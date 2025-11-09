// MoldPark Service Worker
// Version 1.0.1 - Network Error Fix

const CACHE_NAME = 'moldpark-cache-v2';
const STATIC_CACHE_URLS = [
    '/',
    '/static/js/custom.js',
    '/static/images/moldpark_logo.jpg',
    '/static/favicon.ico'
];

// Install event - cache static resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching static files');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .then(() => {
                console.log('Service Worker: Static files cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.log('Service Worker: Cache failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activated');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip Chrome extension requests
    if (event.request.url.startsWith('chrome-extension://')) {
        return;
    }
    
    // Skip Chrome DevTools requests
    if (event.request.url.includes('/.well-known/')) {
        return;
    }

    // Skip API and dynamic requests
    if (event.request.url.includes('/api/') || 
        event.request.url.includes('/django-admin/') ||
        event.request.url.includes('?')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if available
                if (response) {
                    return response;
                }

                // For static files, try to cache them
                if (event.request.url.includes('/static/')) {
                    return fetch(event.request).then(fetchResponse => {
                        // Check if valid response
                        if (!fetchResponse || fetchResponse.status !== 200 || fetchResponse.type !== 'basic') {
                            return fetchResponse;
                        }

                        // Clone the response
                        const responseToCache = fetchResponse.clone();

                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return fetchResponse;
                    });
                }

                // For other requests, just fetch from network
                return fetch(event.request);
            })
            .catch(() => {
                // If both cache and network fail, return offline page for HTML requests
                const acceptHeader = event.request.headers.get('accept');
                if (acceptHeader && acceptHeader.includes('text/html')) {
                    return new Response(
                        `<!DOCTYPE html>
                        <html>
                        <head>
                            <title>MoldPark - Çevrimdışı</title>
                            <meta charset="utf-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1">
                            <style>
                                body { 
                                    font-family: Arial, sans-serif; 
                                    text-align: center; 
                                    padding: 50px; 
                                    background: linear-gradient(135deg, #F5B427 0%, #D49A1F 100%);
                                    color: white;
                                    margin: 0;
                                    min-height: 100vh;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    flex-direction: column;
                                }
                                .offline-container {
                                    background: rgba(255, 255, 255, 0.1);
                                    padding: 40px;
                                    border-radius: 20px;
                                    backdrop-filter: blur(10px);
                                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                                }
                                h1 { color: #fff; margin-bottom: 20px; }
                                .retry-btn {
                                    background: #4CAF50;
                                    color: white;
                                    border: none;
                                    padding: 12px 24px;
                                    border-radius: 25px;
                                    cursor: pointer;
                                    font-size: 16px;
                                    margin-top: 20px;
                                    transition: all 0.3s ease;
                                }
                                .retry-btn:hover {
                                    background: #45a049;
                                    transform: translateY(-2px);
                                }
                            </style>
                        </head>
                        <body>
                            <div class="offline-container">
                                <h1>🔌 İnternet Bağlantısı Yok</h1>
                                <p>MoldPark'a erişmek için internet bağlantınızı kontrol edin.</p>
                                <button class="retry-btn" onclick="window.location.reload()">
                                    🔄 Tekrar Dene
                                </button>
                            </div>
                        </body>
                        </html>`,
                        {
                            headers: {
                                'Content-Type': 'text/html',
                            },
                        }
                    );
                }
            })
    );
});

// Background sync for form submissions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('Service Worker: Background sync triggered');
        event.waitUntil(doBackgroundSync());
    }
});

// Push notifications
self.addEventListener('push', event => {
    console.log('Service Worker: Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : 'MoldPark bildirimi',
        icon: '/static/images/moldpark_logo.jpg',
        badge: '/static/favicon.ico',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Görüntüle',
                icon: '/static/favicon.ico'
            },
            {
                action: 'close',
                title: 'Kapat',
                icon: '/static/favicon.ico'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification('MoldPark', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification clicked');
    
    event.notification.close();

    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Helper function for background sync
async function doBackgroundSync() {
    try {
        // Implement background sync logic here
        console.log('Service Worker: Performing background sync');
        return Promise.resolve();
    } catch (error) {
        console.log('Service Worker: Background sync failed', error);
        return Promise.reject(error);
    }
}

// Message handling from main thread
self.addEventListener('message', event => {
    console.log('Service Worker: Message received', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('Service Worker: Script loaded'); 