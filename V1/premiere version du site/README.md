
# Next Quest – Docker (Flask + SQLite)

Lancer en local :

```bash
docker compose up --build
```

Puis ouvrir http://localhost:3200

Comptes :
- Admin seed : **admin@nextquest.ch / admin**

Trois bases SQLite dans `db/` :
- `users.db`, `offers.db`, `services.db`

Fonctions clés :
- Multilingue (FR/DE/IT/RM) avec sélecteur permanent
- Thème clair/sombre/auto
- Rôles : étudiant, entreprise, particulier, admin
- Offres et Services : vue Liste/Carte (Leaflet), détail, postuler (étudiants), mini‑CV
- Admin : nommer admin, supprimer comptes/offres/services
- Modération simple (mots interdits)

> MVP destiné à évoluer en production (emails, paiements, CGU suisses détaillées, etc.).
