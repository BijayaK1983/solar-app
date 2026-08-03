// Bump CACHE_NAME on every deploy that changes solar_business_app.html.
// The activate handler deletes every cache whose name doesn't match, so changing
// this string is what forces existing installs to drop their old copy.
const CACHE_NAME = 'solarops-cache-v3';
const ASSETS = [
  './solar_business_app.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) {
    return; // let the browser handle cross-origin/non-GET requests (e.g. Supabase API calls) normally
  }

  // The app itself is network-first: always try to fetch the current version, and
  // only fall back to the cache when offline. The previous stale-while-revalidate
  // strategy served the cached copy immediately and refreshed in the background,
  // which meant a deploy didn't show up until the *second* reload — the app looked
  // like it hadn't updated at all.
  const isAppShell = req.mode === 'navigate' || new URL(req.url).pathname.endsWith('.html');
  if (isAppShell) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.status === 200) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Icons and the manifest rarely change, so serve them from cache first for speed
  // and refresh them in the background.
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetchPromise = fetch(req).then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
        }
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
