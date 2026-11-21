/* CurrencyTel PWA hotfix: 2026-11-21 / shell v5 */
const APP_CACHE = 'currencytel-shell-v5-20261121-news-cache-hotfix';
// Keep the existing data cache so offline prices/news are not deleted on upgrade.
const DATA_CACHE = 'currencytel-data-v3.4.2';
const SHELL = [
  './', './index.html', './assets/css/main.css',
  './assets/js/app.js', './assets/js/data.js', './assets/js/news.js',
  './assets/js/format.js', './assets/js/chart.js', './assets/js/history.js',
  './assets/icons/icon.svg', './manifest.webmanifest'
];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(APP_CACHE);
    // Bypass the browser's HTTP cache when preparing a new application version.
    await cache.addAll(SHELL.map(path => new Request(path, { cache: 'reload' })));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(name =>
      name.startsWith('currencytel-shell-') && name !== APP_CACHE
    ).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});
async function networkFirst(event, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(event.request, { cache: 'no-store' });
    if (response.ok) {
      event.waitUntil(cache.put(event.request, response.clone()));
      return response;
    }
    // If the server temporarily responds with an error, use previously saved data.
    return await cache.match(event.request) || response;
  } catch (_error) {
    return await cache.match(event.request) || Response.error();
  }
}
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // JSON should never be served cache-first; otherwise rates/news go stale.
  if (/\/data\/[^/]+\.json$/.test(url.pathname)) {
    event.respondWith(networkFirst(event, DATA_CACHE));
    return;
  }
  // HTML, JS and CSS must be checked online on each app launch.
  if (request.mode === 'navigate' || /\.(?:html|css|js)$/.test(url.pathname) ||
      url.pathname.endsWith('/manifest.webmanifest')) {
    event.respondWith((async () => {
      const response = await networkFirst(event, APP_CACHE);
      if (request.mode !== 'navigate' || response.ok) return response;
      const cache = await caches.open(APP_CACHE);
      return await cache.match('./index.html') || response;
    })());
    return;
  }
  event.respondWith((async () => {
    const cache = await caches.open(APP_CACHE);
    const saved = await cache.match(request);
    if (saved) return saved;
    const response = await fetch(request);
    if (response.ok) event.waitUntil(cache.put(request, response.clone()));
    return response;
  })());
});
