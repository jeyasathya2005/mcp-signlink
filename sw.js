
const CACHE_NAME = 'signspeak-avatar-v2';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/index.tsx',
  '/types.ts',
  '/App.tsx',
  '/components/SignAvatar.tsx',
  '/components/TranslationLog.tsx',
  '/components/Dashboard.tsx'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching Voice-to-Sign assets...');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});
