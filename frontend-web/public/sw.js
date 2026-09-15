/* KivuFoot — service worker : coquille hors ligne, polices en cache, API jamais cachée. */
const CACHE = "kivufoot-shell-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/favicon-64.png", "/apple-180.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.origin !== self.location.origin) {
    if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
      e.respondWith(
        caches.open(CACHE).then((c) =>
          c.match(req).then((hit) => {
            const frais = fetch(req)
              .then((r) => {
                if (r && r.ok) c.put(req, r.clone());
                return r;
              })
              .catch(() => hit);
            return hit || frais;
          })
        )
      );
    }
    return; /* API : toujours le réseau, jamais de cache. */
  }

  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((r) => {
          const cp = r.clone();
          caches.open(CACHE).then((c) => c.put("/index.html", cp));
          return r;
        })
        .catch(() => caches.match("/index.html"))
    );
    return;
  }

  e.respondWith(
    caches.match(req).then(
      (hit) =>
        hit ||
        fetch(req).then((r) => {
          if (r && r.ok) {
            const cp = r.clone();
            caches.open(CACHE).then((c) => c.put(req, cp));
          }
          return r;
        })
    )
  );
});
