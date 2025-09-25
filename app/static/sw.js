// Service Worker pour Next Quest
const CACHE_NAME = 'nextquest-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/theme.js',
  '/static/js/lang.js',
  '/static/js/mobile.js',
  '/static/js/main.js',
  '/static/img/logo.png',
  '/offers',
  '/services'
];

// Installation du service worker
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('Cache ouvert');
        return cache.addAll(urlsToCache);
      })
  );
});

// Activation du service worker
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('Suppression de l\'ancien cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Interception des requêtes
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Retourner la réponse du cache si elle existe
        if (response) {
          return response;
        }
        
        // Sinon, faire la requête réseau
        return fetch(event.request).then(function(response) {
          // Vérifier si la réponse est valide
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          // Cloner la réponse pour le cache
          const responseToCache = response.clone();
          
          caches.open(CACHE_NAME)
            .then(function(cache) {
              cache.put(event.request, responseToCache);
            });
          
          return response;
        });
      })
  );
});

// Gestion des notifications push (pour usage futur)
self.addEventListener('push', function(event) {
  const options = {
    body: event.data ? event.data.text() : 'Nouvelle notification Next Quest',
    icon: '/static/img/logo.png',
    badge: '/static/img/logo.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Voir les offres',
        icon: '/static/img/logo.png'
      },
      {
        action: 'close',
        title: 'Fermer',
        icon: '/static/img/logo.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Next Quest', options)
  );
});

// Gestion des clics sur les notifications
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/offers')
    );
  } else if (event.action === 'close') {
    // Fermer la notification
    return;
  } else {
    // Action par défaut
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

console.log('Service Worker Next Quest chargé');
