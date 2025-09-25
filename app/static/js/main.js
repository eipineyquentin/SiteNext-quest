
function toggleView(idShow, idHide) {
    const showElement = document.getElementById(idShow);
    const hideElement = document.getElementById(idHide);
    
    if (showElement && hideElement) {
        showElement.hidden = false;
        hideElement.hidden = true;
        
        // Si on affiche la carte, l'initialiser si ce n'est pas déjà fait
        if (idShow === 'mapView' && window.map) {
            setTimeout(() => {
                window.map.invalidateSize();
            }, 100);
        }
    }
}

// Fonction pour initialiser la carte avec gestion d'erreur
function initMap(containerId, markers, centerLat = 46.5197, centerLng = 6.6323, zoom = 10) {
    try {
        const mapContainer = document.getElementById(containerId);
        if (!mapContainer) {
            console.error('Conteneur de carte non trouvé:', containerId);
            return null;
        }
        
        // Créer la carte
        const map = L.map(containerId).setView([centerLat, centerLng], zoom);
        
        // Ajouter la couche de tuiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // Ajouter les marqueurs
        if (markers && Array.isArray(markers)) {
            markers.forEach(marker => {
                if (marker.lat && marker.lng) {
                    const m = L.marker([marker.lat, marker.lng]).addTo(map);
                    
                    // Créer le contenu du popup
                    let popupContent = `<strong>${marker.title || 'Titre non disponible'}</strong><br>`;
                    popupContent += `${marker.city || 'Ville non disponible'}<br>`;
                    
                    // Déterminer le type de lien selon le contexte
                    if (marker.id) {
                        const isService = window.location.pathname.includes('/services');
                        const linkPath = isService ? `/service/${marker.id}` : `/offer/${marker.id}`;
                        const linkText = isService ? 'Voir le service' : 'Voir l\'offre';
                        popupContent += `<a href="${linkPath}">${linkText}</a>`;
                    }
                    
                    m.bindPopup(popupContent);
                }
            });
        }
        
        return map;
    } catch (error) {
        console.error('Erreur lors de l\'initialisation de la carte:', error);
        return null;
    }
}

// Initialiser la carte quand le DOM est chargé
document.addEventListener('DOMContentLoaded', function() {
    // Attendre un peu pour s'assurer que tous les éléments sont chargés
    setTimeout(() => {
        const mapContainer = document.getElementById('map');
        if (mapContainer && typeof points !== 'undefined') {
            window.map = initMap('map', points);
        }
    }, 100);
});
