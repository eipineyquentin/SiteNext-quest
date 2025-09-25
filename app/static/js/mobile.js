// Mobile functionality for Next Quest
document.addEventListener('DOMContentLoaded', function() {
    
    // Menu mobile toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const nav = document.querySelector('.nav');
    
    if (mobileMenuBtn && nav) {
        mobileMenuBtn.addEventListener('click', function() {
            nav.classList.toggle('mobile-open');
            
            // Changer l'icône du bouton
            const icon = mobileMenuBtn.querySelector('span');
            if (nav.classList.contains('mobile-open')) {
                icon.textContent = '✕';
            } else {
                icon.textContent = '☰';
            }
        });
        
        // Fermer le menu en cliquant à l'extérieur
        document.addEventListener('click', function(e) {
            if (!nav.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                nav.classList.remove('mobile-open');
                const icon = mobileMenuBtn.querySelector('span');
                icon.textContent = '☰';
            }
        });
    }
    
    // Améliorer l'expérience tactile
    const buttons = document.querySelectorAll('.btn, .nav__link, button');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
        });
        
        button.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Optimiser les formulaires pour mobile
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        // Éviter le zoom automatique sur iOS
        if (input.type !== 'range' && input.type !== 'checkbox' && input.type !== 'radio') {
            input.style.fontSize = '16px';
        }
        
        // Améliorer l'expérience de saisie
        input.addEventListener('focus', function() {
            this.style.borderColor = 'var(--accent)';
        });
        
        input.addEventListener('blur', function() {
            this.style.borderColor = 'var(--border)';
        });
    });
    
    // Gestion du viewport pour éviter le zoom horizontal
    function setViewport() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        }
    }
    
    setViewport();
    
    // Détection de l'orientation
    function handleOrientationChange() {
        if (window.innerWidth <= 768) {
            document.body.classList.add('mobile-landscape');
        } else {
            document.body.classList.remove('mobile-landscape');
        }
    }
    
    window.addEventListener('orientationchange', function() {
        setTimeout(handleOrientationChange, 100);
    });
    
    window.addEventListener('resize', handleOrientationChange);
    handleOrientationChange();
    
    // Améliorer les cartes d'offres sur mobile
    const offers = document.querySelectorAll('.offer');
    offers.forEach(offer => {
        offer.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.98)';
            this.style.transition = 'transform 0.1s ease';
        });
        
        offer.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Optimiser les cartes
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('touchstart', function() {
            this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        });
        
        card.addEventListener('touchend', function() {
            this.style.boxShadow = '';
        });
    });
    
    // Gestion des gestes de swipe pour la navigation
    let startX = 0;
    let startY = 0;
    
    document.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
    });
    
    document.addEventListener('touchend', function(e) {
        if (!startX || !startY) return;
        
        const endX = e.changedTouches[0].clientX;
        const endY = e.changedTouches[0].clientY;
        
        const diffX = startX - endX;
        const diffY = startY - endY;
        
        // Détecter un swipe horizontal significatif
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            if (diffX > 0) {
                // Swipe gauche - pourrait être utilisé pour navigation
                console.log('Swipe gauche détecté');
            } else {
                // Swipe droite - pourrait être utilisé pour navigation
                console.log('Swipe droite détecté');
            }
        }
        
        startX = 0;
        startY = 0;
    });
    
    // Améliorer l'accessibilité tactile
    const focusableElements = document.querySelectorAll('a, button, input, select, textarea, [tabindex]');
    focusableElements.forEach(element => {
        element.addEventListener('focus', function() {
            this.style.outline = '2px solid var(--accent)';
            this.style.outlineOffset = '2px';
        });
        
        element.addEventListener('blur', function() {
            this.style.outline = '';
            this.style.outlineOffset = '';
        });
    });
    
    // Détection de la connexion réseau
    function updateConnectionStatus() {
        const isOnline = navigator.onLine;
        const statusElement = document.getElementById('connection-status');
        
        if (statusElement) {
            if (isOnline) {
                statusElement.textContent = '🟢 En ligne';
                statusElement.style.color = 'green';
            } else {
                statusElement.textContent = '🔴 Hors ligne';
                statusElement.style.color = 'red';
            }
        }
    }
    
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
    updateConnectionStatus();
    
    // Optimiser les performances sur mobile
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            // Enregistrer un service worker pour le cache
            navigator.serviceWorker.register('/sw.js').catch(function(err) {
                console.log('ServiceWorker registration failed: ', err);
            });
        });
    }
    
    // Précharger les images importantes
    const importantImages = document.querySelectorAll('img[data-preload]');
    importantImages.forEach(img => {
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'image';
        link.href = img.src;
        document.head.appendChild(link);
    });
    
    console.log('Mobile optimizations loaded successfully');
});
