#!/usr/bin/env python3
"""Builds Tongues' sentence decks (cloze/data/<lang>.json) from Tatoeba exports.

  python3 build_decks.py TATOEBA_DIR [lang ...]

TATOEBA_DIR holds the unpacked per-language exports from downloads.tatoeba.org/exports/per_language/:
<lang>_sentences.tsv, <lang>-eng_links.tsv and eng_sentences.tsv.

Each item is [sentence, english, offset of the gap word, gap word, its frequency rank, tatoeba id].
Sentences are picked to spread over lengths (mostly 5–10 words, some short ones for the start, some long
ones for the top levels), made only of reasonably common words, and ordered easy → hard. The previous
deck's ids go into "old" so the app can carry progress across to the new deck.
"""
import json, math, re, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

META = {
    "pol": ("Polish", "pl-PL"), "deu": ("German", "de-DE"),
    "nob": ("Norwegian", "nb-NO"), "cym": ("Welsh", "cy-GB"),
}
COUNT = 6000
WORDS = 4000
# share of the deck per sentence length (words): a few short ones to start, most in the middle, some long
BANDS = [((3, 4), .12), ((5, 6), .28), ((7, 8), .28), ((9, 11), .22), ((12, 16), .10)]
WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")
NAMES = {"tom", "mary", "john", "alice", "jack", "ken", "bob", "tony", "mike", "jim", "lucy", "emily", "bill"}


def toks(s):
    return WORD_RE.findall(unicodedata.normalize("NFC", s).lower().replace("’", "'"))


def load(tsv, lang=None):
    out = {}
    with open(tsv, encoding="utf8") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and (lang is None or p[1] == lang):
                out[int(p[0])] = p[2]
    return out


def build(src: Path, code: str, eng: dict, old: dict | None):
    sents = load(src / f"{code}_sentences.tsv", code)
    en_of = {}
    with open(src / f"{code}-eng_links.tsv", encoding="utf8") as f:
        for line in f:
            a, b = map(int, line.split("\t")[:2])
            if a in sents and b in eng and a not in en_of:
                en_of[a] = eng[b]
    cand, seen = [], set()
    for sid in sorted(en_of):           # oldest ids first: the most checked sentences win duplicates
        s = sents[sid].strip()
        key = s.lower()
        if key in seen or len(s) > 95 or re.search(r"\d|[\"“”„«»()\[\]]", s):
            continue
        seen.add(key)
        t = toks(s)
        if len(t) < 3:
            continue
        cand.append((sid, s, en_of[sid], t))
    freq = Counter(w for _, _, _, t in cand for w in t)
    words = [w for w, _ in freq.most_common() if w not in NAMES and len(w) > 1][:WORDS]
    rank = {w: i for i, w in enumerate(words)}

    items = []
    for sid, s, en, t in cand:
        # every word common enough (names allowed), and at most one name
        if sum(w in NAMES for w in t) > 1 or any(w not in rank and w not in NAMES and len(w) > 1 for w in t):
            continue
        # the gap: the least common real word (not a name), at least 2 letters
        best = None
        for m in WORD_RE.finditer(unicodedata.normalize("NFC", s)):
            w = m.group().lower().replace("’", "'")
            if w in rank and (best is None or rank[w] > rank[best[1]]):
                best = (m, w)
        if not best:
            continue
        rs = [math.log(2 + rank.get(w, 50)) for w in t]
        diff = max(rs) + .5 * sum(rs) / len(rs) + .12 * len(t)
        items.append((diff, len(t), [s, en, best[0].start(), best[0].group(), rank[best[1]], sid], t))

    n_names = 0
    chosen = []
    total = min(COUNT, len(items))
    for (lo, hi), share in BANDS:
        pool = sorted((x for x in items if lo <= x[1] <= hi), key=lambda x: x[0])
        want = round(total * share)
        got = 0
        for x in pool:
            if got >= want:
                break
            if any(w in NAMES for w in x[3]):
                if n_names >= total * .12:     # keep Tom & Mary to about one sentence in eight
                    continue
                n_names += 1
            chosen.append(x); got += 1
    if len(chosen) < total:                 # small decks (Welsh): take whatever is left
        have = {id(x) for x in chosen}
        chosen += [x for x in sorted(items, key=lambda x: x[0]) if id(x) not in have][: total - len(chosen)]
    chosen.sort(key=lambda x: (x[0], x[2][5]))
    out = {"lang": code, "name": META[code][0], "voice": META[code][1], "count": len(chosen), "v": 2,
           "credit": "Sentences from Tatoeba (tatoeba.org), CC-BY 2.0 FR",
           "words": words, "items": [x[2] for x in chosen]}
    if old:
        out["old"] = [it[5] for it in old["items"]]
    return out


def main():
    src = Path(sys.argv[1])
    codes = sys.argv[2:] or list(META)
    eng = load(src / "eng_sentences.tsv", "eng")
    data = Path(__file__).resolve().parent.parent / "data"
    for code in codes:
        f = data / f"{code}.json"
        old = json.loads(f.read_text()) if f.exists() else None
        if old and old.get("v") == 2:
            old = {"items": [[None] * 5 + [i] for i in old.get("old", [])]} if old.get("old") else None
        d = build(src, code, eng, old)
        f.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
        L = sorted(len(toks(it[0])) for it in d["items"])
        print(f"{code}: {d['count']} sentences, words/sentence median {L[len(L)//2]}, "
              f"10–90% {L[len(L)//10]}–{L[len(L)*9//10]}, {f.stat().st_size//1024} KB")


if __name__ == "__main__":
    main()
