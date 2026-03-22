/// <reference lib="webworker" />

const CACHE_NAME = 'izana-v1';

const STATIC_ASSETS = ['/', '/chat', '/journey', '/profile'];

/* ── Install ──────────────────────────────────────────────────── */

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)),
  );
  // Activate immediately without waiting for existing clients to close
  self.skipWaiting();
});

/* ── Activate ─────────────────────────────────────────────────── */

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      ),
    ),
  );
  // Take control of all open clients immediately
  self.clients.claim();
});

/* ── Fetch Strategy ───────────────────────────────────────────── */

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip chrome-extension and other non-http(s) schemes
  if (!url.protocol.startsWith('http')) return;

  // API calls: Network-first, no cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({ error: 'offline', message: 'You are offline' }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      }),
    );
    return;
  }

  // Static assets & pages: Network-first with cache fallback
  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache successful responses
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
        }
        return response;
      })
      .catch(() => {
        // Serve from cache when offline
        return caches.match(request).then((cached) => {
          if (cached) return cached;

          // For navigation requests, serve the cached root page
          if (request.mode === 'navigate') {
            return caches.match('/');
          }

          return new Response('Offline', { status: 503 });
        });
      }),
  );
});
