// SPDX-License-Identifier: AGPL-3.0-or-later · Copyright (C) 2026 Samed KIZILHAN — Praevidio AI
// Uygulama kabuğunu önbellekler (hızlı açılış + "ana ekrana ekle"). API istekleri HİÇ önbelleklenmez.
const CACHE = "praevidio-shell-v4";
const SHELL = ["./", "index.html", "styles.css", "app.js", "manifest.webmanifest",
               "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || !url.pathname.startsWith("/app/")) return;   // API → doğrudan ağ
  e.respondWith(fetch(e.request).then((r) => {                                   // önce ağ, çevrimdışıysa önbellek
    const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r;
  }).catch(() => caches.match(e.request)));
});
