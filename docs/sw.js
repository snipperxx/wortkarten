// 离线缓存：页面和词库先联网（拿最新版），没网用缓存；发音包看过就存下来；同步请求不经过缓存
const V = "wortkarten-v4";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "words.json", "audio/index.json", "changelog.json"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  // 和送报 App 同一个域名、共用缓存区：只清自己的旧版本缓存
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith("wortkarten-") && k !== V).map((k) => caches.delete(k)))));
  self.clients.claim();
});
const networkFirst = (req, key) => fetch(req, { cache: "no-cache" })
  .then((r) => { if (r.ok) { const c = r.clone(); caches.open(V).then((x) => x.put(key || req, c)); } return r; })
  .catch(() => caches.match(key || req).then((r) => r || caches.match("index.html")));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.hostname === "api.github.com" || u.hostname.endsWith("githubusercontent.com")) return;
  if (u.origin === location.origin) {
    if (u.pathname.endsWith("/") || u.pathname.endsWith("index.html")) return e.respondWith(networkFirst(e.request, "index.html"));
    if (u.pathname.endsWith("words.json") || u.pathname.endsWith("changelog.json") || u.pathname.endsWith("audio/index.json")) return e.respondWith(networkFirst(e.request));
    if (/\/audio\/b\d+\.json$/.test(u.pathname)) {
      return e.respondWith(caches.open("wk-audio").then((c) => c.match(e.request).then((hit) => hit ||
        fetch(e.request).then((r) => { if (r.ok) c.put(e.request, r.clone()); return r; }))));
    }
    return e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
  if (u.hostname.endsWith("googleapis.com") || u.hostname.endsWith("gstatic.com")) {
    e.respondWith(caches.open("wk-fonts").then((c) => c.match(e.request).then((hit) => hit ||
      fetch(e.request).then((r) => { if (r.ok || r.type === "opaque") c.put(e.request, r.clone()); return r; }))));
  }
});
