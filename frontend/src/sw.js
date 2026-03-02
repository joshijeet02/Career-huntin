// Custom Service Worker — cache-bust: v6
// Handles: precaching, offline, push notifications, notification clicks

import { clientsClaim } from 'workbox-core'
import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

self.skipWaiting()
clientsClaim()

// Precache all static assets (manifest injected by VitePWA at build time)
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// SPA navigation fallback — serve index.html for all navigation requests
registerRoute(new NavigationRoute(createHandlerBoundToURL('index.html')))

// ── Push Notifications ────────────────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'Coach', body: 'Your coach has a message for you.', url: '/' }
  if (event.data) {
    try { data = { ...data, ...event.data.json() } } catch (_) {}
  }

  const options = {
    body: data.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    data: { url: data.url || '/' },
    vibrate: [200, 100, 200],
    requireInteraction: false,
    tag: 'coach-nudge',         // replaces previous unread notification
    renotify: true,
  }

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  )
})

// ── Notification Click ────────────────────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = event.notification.data?.url || '/'

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // If app is already open, focus it
      for (const client of clientList) {
        if ('focus' in client) {
          client.focus()
          return
        }
      }
      // Otherwise open a new window
      if (clients.openWindow) return clients.openWindow(targetUrl)
    })
  )
})
