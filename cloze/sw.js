// Cloze: works offline once opened. Bump the version when the app or decks change.
const C = "cloze-v1";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon.svg", "data/pol.json", "data/cym.json", "data/deu.json", "data/nob.json"];
self.addEventListener("install", e => e.waitUntil(caches.open(C).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).then(r => {
    if (r.ok && new URL(e.request.url).origin === location.origin) { const copy = r.clone(); caches.open(C).then(c => c.put(e.request, copy)); }
    return r;
  })));
});
