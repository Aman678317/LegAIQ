/**
 * Jurisiva AI Service Worker
 * Provides offline-first caching for the legal intelligence platform
 * Uses Workbox for advanced caching strategies
 */

// Load Workbox from CDN for unbundled public service worker file
try {
  importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js');
} catch (e) {
  console.warn('[Jurisiva SW] Workbox CDN load skipped/failed.');
}

// Cache names
const CACHE_NAMES = {
  static: 'jurisiva-static-v1',
  api: 'jurisiva-api-v1',
  documents: 'jurisiva-documents-v1',
  images: 'jurisiva-images-v1',
  offline: 'jurisiva-offline-v1',
};

// Maximum entries and age for caches
const MAX_ENTRIES = 100;
const MAX_AGE_SECONDS = 60 * 60 * 24 * 30; // 30 days

if (typeof workbox !== 'undefined' && workbox) {
  workbox.setConfig({ debug: false });

  const { precacheAndRoute, cleanupOutdatedCaches } = workbox.precaching || {};
  const { registerRoute, NavigationRoute } = workbox.routing || {};
  const { StaleWhileRevalidate, NetworkFirst, CacheFirst, NetworkOnly } = workbox.strategies || {};
  const { ExpirationPlugin } = workbox.expiration || {};
  const { CacheableResponsePlugin } = workbox.cacheableResponse || {};
  const { BackgroundSyncPlugin } = workbox.backgroundSync || {};

  if (precacheAndRoute) {
    precacheAndRoute(self.__WB_MANIFEST || []);
  }
  if (cleanupOutdatedCaches) {
    cleanupOutdatedCaches();
  }

  if (registerRoute && CacheFirst) {
    registerRoute(
      ({ request }) => request.destination === 'script' || request.destination === 'style' || request.destination === 'font',
      new CacheFirst({
        cacheName: CACHE_NAMES.static,
        plugins: [
          new CacheableResponsePlugin({ statuses: [0, 200] }),
          new ExpirationPlugin({ maxEntries: MAX_ENTRIES, maxAgeSeconds: MAX_AGE_SECONDS }),
        ],
      })
    );

    registerRoute(
      ({ request }) => request.destination === 'image',
      new CacheFirst({
        cacheName: CACHE_NAMES.images,
        plugins: [
          new CacheableResponsePlugin({ statuses: [0, 200] }),
          new ExpirationPlugin({ maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 60 }),
        ],
      })
    );

    if (StaleWhileRevalidate) {
      registerRoute(
        ({ url }) => url.pathname.startsWith('/api/') && url.searchParams.get('_nocache') !== 'true',
        new StaleWhileRevalidate({
          cacheName: CACHE_NAMES.api,
          plugins: [
            new CacheableResponsePlugin({ statuses: [0, 200] }),
            new ExpirationPlugin({ maxEntries: MAX_ENTRIES, maxAgeSeconds: 60 * 60 * 24 * 7 }),
          ],
        }),
        'GET'
      );
    }

    if (BackgroundSyncPlugin && NetworkOnly) {
      const bgSyncPlugin = new BackgroundSyncPlugin('jurisiva-mutations', {
        maxRetentionTime: 24 * 60,
      });

      ['POST', 'PUT', 'DELETE', 'PATCH'].forEach((method) => {
        registerRoute(
          ({ url, request }) => url.pathname.startsWith('/api/') && request.method === method,
          new NetworkOnly({ plugins: [bgSyncPlugin] }),
          method
        );
      });
    }

    registerRoute(
      ({ url }) => url.pathname.includes('/documents/') || url.pathname.includes('/storage/'),
      new CacheFirst({
        cacheName: CACHE_NAMES.documents,
        plugins: [
          new CacheableResponsePlugin({ statuses: [0, 200] }),
          new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 30 }),
        ],
      })
    );

    if (NavigationRoute && NetworkFirst) {
      const navigationRoute = new NavigationRoute(
        new NetworkFirst({
          cacheName: CACHE_NAMES.offline,
          plugins: [
            new CacheableResponsePlugin({ statuses: [0, 200] }),
            new ExpirationPlugin({ maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 7 }),
          ],
          networkTimeoutSeconds: 3,
        }),
        {
          allowlist: [/^\/dashboard/, /^\/cases/, /^\/chat/, /^\/settings/, /^\/admin/],
          denylist: [/^\/api/, /^\/_next/, /^\/static/],
        }
      );
      registerRoute(navigationRoute);
    }
  }
}

/**
 * Offline fallback page
 */
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    self.registration.unregister().then(() => {
      return clients.claim();
    })
  );
});

/**
 * Handle messages from clients
 */
self.addEventListener('message', (event) => {
  const { type, payload } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'GET_CACHE_STATUS':
      event.ports[0].postMessage({
        type: 'CACHE_STATUS',
        payload: {
          caches: Object.keys(CACHE_NAMES).map((key) => ({
            name: CACHE_NAMES[key],
            type: key,
          })),
        },
      });
      break;

    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ type: 'CACHE_CLEARED' });
      });
      break;

    case 'PREFETCH_CASE':
      if (payload?.caseId) {
        prefetchCaseData(payload.caseId);
      }
      break;

    default:
      break;
  }
});

/**
 * Clear all caches
 */
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  await Promise.all(
    cacheNames
      .filter((name) => name.startsWith('jurisiva-'))
      .map((name) => caches.delete(name))
  );
}

/**
 * Prefetch case data for offline access
 */
async function prefetchCaseData(caseId) {
  try {
    const cache = await caches.open(CACHE_NAMES.api);
    const urls = [
      `/api/v1/cases/${caseId}`,
      `/api/v1/cases/${caseId}/documents`,
      `/api/v1/cases/${caseId}/entities`,
      `/api/v1/cases/${caseId}/timeline`,
      `/api/v1/cases/${caseId}/ownership`,
      `/api/v1/cases/${caseId}/risks`,
    ];
    await Promise.all(
      urls.map((url) =>
        fetch(url, { credentials: 'include' })
          .then((response) => {
            if (response.ok) return cache.put(url, response);
          })
          .catch(() => {}) // Ignore failures
      )
    );

    // Notify clients
    self.clients.matchAll().then((clients) => {
      clients.forEach((client) => {
        client.postMessage({
          type: 'PREFETCH_COMPLETE',
          payload: { caseId },
        });
      });
    });
  } catch (error) {
    console.error('Prefetch failed:', error);
  }
}

/**
 * Periodic sync for background updates (when supported)
 */
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'jurisiva-periodic-sync') {
    event.waitUntil(performPeriodicSync());
  }
});

async function performPeriodicSync() {
  try {
    // Sync any pending mutations
    const queue = await self.registration.sync.getTags();
    // Notify clients of sync
    self.clients.matchAll().then((clients) => {
      clients.forEach((client) => {
        client.postMessage({
          type: 'PERIODIC_SYNC_COMPLETE',
          payload: { timestamp: Date.now() },
        });
      });
    });
  } catch (error) {
    console.error('Periodic sync failed:', error);
  }
}

/**
 * Handle fetch errors for offline UX
 */
self.addEventListener('fetch', (event) => {
  // Pass-through fetch
});

// Notify clients when service worker is ready
self.addEventListener('controllerchange', () => {
  self.clients.matchAll().then((clients) => {
    clients.forEach((client) => {
      client.postMessage({ type: 'SW_UPDATED' });
    });
  });
});

console.log('[Jurisiva SW] Service Worker loaded');