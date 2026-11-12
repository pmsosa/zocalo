// Zócalo service worker: the app shell works offline; data always comes from the network.
const CACHE = "zocalo-shell-v1";
const SHELL = ["/", "/static/css/app.css", "/static/js/app.js", "/static/js/ui.js", "/static/js/dots.js",
  "/static/js/views.js", "/static/js/i18n.js", "/static/icons/favicon.svg", "/static/icons/mark-light.svg",
  "/static/icons/mark-dark.svg", "/static/fonts/Inter.woff2", "/static/fonts/Manrope.woff2", "/static/fonts/JetBrainsMono.woff2"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/api/")) return;
  // network first, so updates show at once; fall back to the cached shell when offline
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok && (url.pathname.startsWith("/static/") || url.pathname === "/")) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
    return r;
  }).catch(() => caches.match(e.request).then(m => m || caches.match("/"))));
});
