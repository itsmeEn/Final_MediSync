/*
 * This file (which will be your service worker)
 * is picked up by the build system ONLY if
 * quasar.config file > pwa > workboxMode is set to "InjectManifest"
 */

declare const self: ServiceWorkerGlobalScope &
  typeof globalThis & { skipWaiting: () => void };

import { clientsClaim } from 'workbox-core';
import {
  precacheAndRoute,
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
} from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';

void self.skipWaiting();
clientsClaim();

// Use with precache injection
precacheAndRoute(self.__WB_MANIFEST);

cleanupOutdatedCaches();

// Non-SSR fallbacks to index.html
// Production SSR fallbacks to offline.html (except for dev)
if (process.env.MODE !== 'ssr' || process.env.PROD) {
  registerRoute(
    new NavigationRoute(
      createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML),
      { denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/] }
    )
  );
}

self.addEventListener('push', (event: PushEvent) => {
  let payload: {
    title?: string
    body?: string
    url?: string
    tag?: string
    data?: Record<string, unknown>
  } = {}

  try {
    payload = event.data?.json() as typeof payload
  } catch {
    try {
      payload = { body: event.data?.text() || '' }
    } catch {
      payload = {}
    }
  }

  const title = payload.title || 'MediSync'
  const body = payload.body || ''
  const url = payload.url || '/'

  const options: NotificationOptions = {
    body,
    data: { ...(payload.data || {}), url },
  }
  if (payload.tag) {
    options.tag = payload.tag
  }

  event.waitUntil(
    self.registration.showNotification(title, options)
  )
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const url = (event.notification.data && (event.notification.data as { url?: string }).url) || '/'

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      const existing = allClients.find((c) => 'focus' in c)
      if (existing) {
        await existing.focus()
        existing.postMessage({ type: 'navigate', url })
        return
      }
      await self.clients.openWindow(url)
    })()
  )
})
