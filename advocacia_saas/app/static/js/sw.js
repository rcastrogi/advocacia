// Service Worker para Notificações Push
const CACHE_NAME = 'petitio-portal-v1';

self.addEventListener('install', (event) => {
    console.log('Service Worker installing.');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('Service Worker activating.');
    event.waitUntil(clients.claim());
});

// Handle push notifications
self.addEventListener('push', (event) => {
    console.log('Push message received:', event);

    let data = {};
    if (event.data) {
        data = event.data.json();
    }

    const options = {
        body: data.body || 'Você tem uma nova notificação',
        icon: '/static/img/petitio-logo.svg',
        badge: '/static/img/petitio-logo.svg',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: data.id || 1,
            url: data.url || '/portal'
        },
        actions: [
            {
                action: 'view',
                title: 'Ver',
                icon: '/static/img/view-icon.png'
            },
            {
                action: 'dismiss',
                title: 'Fechar'
            }
        ],
        requireInteraction: true,
        silent: false
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Petitio', options)
    );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    console.log('Notification click received:', event);

    event.notification.close();

    if (event.action === 'dismiss') {
        return;
    }

    const urlToOpen = event.notification.data.url || '/portal';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // Check if there is already a window/tab open with the target URL
                for (let client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // If not, open a new window/tab
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Handle background sync for offline functionality
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);

    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    try {
        // Implement background sync logic here
        console.log('Performing background sync...');
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}