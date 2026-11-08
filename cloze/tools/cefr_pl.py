"""CEFR level estimate for a Polish sentence, on an absolute scale (not relative to the deck).

level = the higher of
  - vocabulary: how common the rarest word's lemma is in everyday Polish (OpenSubtitles frequency,
    counted per lemma so "wiedziałeś" counts as the common verb "wiedzieć"), and
  - grammar: the hardest structure in it (conditionals, participles, passive, impersonal -no/-to,
    formal connectives), and
  - length: long multi-clause sentences are at least B1/B2.

Levels: 0 A1, 1 A2, 2 B1, 3 B2, 4 C1.
Lemma-rank bands follow the usual rough CEFR vocabulary sizes (A1 ~700 words, A2 ~1500, B1 ~3000,
B2 ~6000, C1 beyond).
"""
import re
import simplemma

LEVELS = ["A1", "A2", "B1", "B2", "C1"]
LEX_CUTS = [700, 1500, 3000, 6000]          # lemma rank → level

# formal or literary connectives
C1_WORDS = {"aczkolwiek", "bowiem", "wszakże", "tudzież", "jakkolwiek", "albowiem", "iż", "jakoby",
            "acz", "ażeby", "wszelako", "atoli", "przeto", "toteż"}
B2_WORDS = {"mimo", "chociaż", "choć", "skoro", "dopóki", "jednak", "jednakże", "natomiast", "zatem",
            "wprawdzie", "owszem", "ponadto", "otóż", "tymczasem", "zarówno", "aby", "lecz", "zaś",
            "niemniej", "wobec", "względem", "pomimo", "gdyby", "gdybym", "gdybyś", "gdybyśmy",
            "gdybyście"}
B1_WORDS = {"który", "która", "które", "którego", "której", "którym", "których", "którymi", "którzy",
            "ponieważ", "żeby", "żebym", "żebyś", "żebyśmy", "jeśli", "zanim", "dopiero", "kiedykolwiek",
            "by", "bym", "byś", "byśmy", "byście", "jeżeli", "czyli"}
# words that look like participles but aren't
NOT_PART = {"miesiąc", "miesiąca", "miesiące", "tysiąc", "tysiąca", "tysiące", "gorący", "gorąca",
            "gorące", "gorącego", "gorącej", "gorącym", "pierwszy", "zajęcia", "pieniądze", "pieniądz",
            "pieniądza", "pieniądzu", "rano", "kino", "wino", "okno", "ono", "zimno", "dziecko", "sąsiąd"}

PART_ACT = re.compile(r"\w{3,}ąc(?:y|a|e|ego|ej|ym|ych|ymi|ą)$")     # robiący – B2
ADV_PRES = re.compile(r"\w{3,}ąc$")                                   # robiąc – B2
ADV_PERF = re.compile(r"\w{2,}(?:wszy|łszy)$")                        # zrobiwszy, przyszedłszy – C1
PASS_PART = re.compile(r"\w{3,}(?:any|ana|ane|ani|ony|ona|one|eni|ęty|ęta|ęte|ęci|yty|yta|yte|ity|ita|ite)$")
IMPERS = re.compile(r"\w{3,}(?:ano|ono|ęto|yto|ito|uto)$")            # zrobiono – C1
COND = re.compile(r"\w+(?:łby|łaby|łoby|liby|łyby|łbym|łabym|łbyś|łabyś|libyśmy|łybyśmy|libyście)$")


class Scorer:
    def __init__(self, freq_lines, corpus_tokens=()):
        """freq_lines: 'word count' lines, commonest first (FrequencyWords pl_50k.txt).
        corpus_tokens: words of a second, textbook-like corpus (all Tatoeba Polish). Film subtitles
        undercount everyday nouns (dictionary, hat, train), so a word counts at its better rank of the two."""
        lemma_count = {}
        self.form_rank = {}
        for i, line in enumerate(freq_lines):
            p = line.split()
            if len(p) != 2:
                continue
            w, c = p[0].lower(), int(p[1])
            self.form_rank.setdefault(w, i)
            lem = self.lemma(w)
            lemma_count[lem] = lemma_count.get(lem, 0) + c
        self.lemma_rank = {l: i for i, (l, _) in enumerate(sorted(lemma_count.items(), key=lambda x: -x[1]))}
        tc = {}
        for w in corpus_tokens:
            lem = self.lemma(w)
            tc[lem] = tc.get(lem, 0) + 1
        for i, (lem, c) in enumerate(sorted(tc.items(), key=lambda x: -x[1])):
            if c >= 5 and (lem not in self.lemma_rank or i < self.lemma_rank[lem]):
                self.lemma_rank[lem] = i

    _cache = {}

    def lemma(self, w):
        r = self._cache.get(w)
        if r is None:
            r = self._cache[w] = simplemma.lemmatize(w, lang="pl").lower()
        return r

    def rank(self, w):
        """lemma rank of a word form, or None if unknown"""
        r = self.lemma_rank.get(self.lemma(w))
        if r is None and w in self.form_rank:
            r = self.lemma_rank.get(w)
        return r

    def lex_level(self, r):
        return sum(r > c for c in LEX_CUTS)

    def grammar_level(self, t):
        lv = 0
        for i, w in enumerate(t):
            if w in NOT_PART:
                continue
            if w in C1_WORDS or ADV_PERF.match(w) or (IMPERS.match(w) and self.lemma(w).endswith("ć")):
                return 4
            if w in B2_WORDS or ADV_PRES.match(w) or (PART_ACT.match(w) and self.lemma(w).endswith("ć")):
                lv = max(lv, 3)
            elif w.startswith("zosta") and any(PASS_PART.match(x) for x in t[i + 1:i + 3]):
                lv = max(lv, 3)                                     # passive: został zbudowany
            elif w in B1_WORDS or COND.match(w):
                lv = max(lv, 2)
        return lv

    def level(self, t, names=(), proper=()):
        """t: lower-case tokens; proper: words capitalised mid-sentence (places, names), not scored.
        Returns (level, rarest lemma rank) or None if a word is unknown."""
        ranks = []
        for w in t:
            if w in names or w in proper or len(w) < 2:
                continue
            r = self.rank(w)
            if r is None:
                return None
            ranks.append(r)
        top = max(ranks, default=0)
        n = len(t)
        # one unusual word in a short, plain sentence is a lookup, not a level: vocabulary alone lifts
        # a sentence of up to 5 words to B1 at most, up to 9 words to B2
        lex = min(self.lex_level(top), 2 if n <= 5 else 3 if n <= 9 else 4)
        gram = self.grammar_level(t)
        lv = max(lex, gram)
        if lex >= 3 and gram >= 3:
            lv = 4                                  # B2 vocabulary and B2 grammar together
        clauses = sum(w in B1_WORDS or w in B2_WORDS or w in ("że", "gdy", "kiedy", "bo", "ale") for w in t)
        if n >= 18 or clauses >= 3:
            lv = max(lv, 3)
        elif n >= 12 or clauses >= 2:
            lv = max(lv, 2)
        return lv, top


def proper_nouns(sentences, tokens):
    """lower-cased words written with a capital mid-sentence more often than not (names, places)"""
    cap, low = {}, {}
    for s in sentences:
        for m in re.finditer(r"(?<=\S )\w+", s):
            w = m.group()
            d = cap if w[0].isupper() else low
            d[w.lower()] = d.get(w.lower(), 0) + 1
    return {w for w, c in cap.items() if c > low.get(w, 0)}
