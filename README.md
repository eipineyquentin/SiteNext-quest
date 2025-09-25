
# Next Quest – Plateforme de Jobs Étudiants Sécurisée

## 🚀 Démarrage Rapide

```bash
docker compose up --build
```

Puis ouvrir http://localhost:3200

## 🔐 Comptes de Test
- **Admin** : `admin@nextquest.ch` / `admin`
- **Étudiant** : `marie.dubois@example.ch` / `password123`
- **Entreprise** : `contact@techsa.ch` / `password123`

## 🛡️ Améliorations de Sécurité (Corrections Apportées)

### ✅ Problèmes Résolus
1. **Connexion Impossible** → Authentification renforcée avec Werkzeug
2. **Carte/Liste Bug** → JavaScript corrigé avec gestion d'erreurs
3. **Sécurité Vulnérable** → Protection CSRF + validation stricte

### 🔒 Sécurité Renforcée
- **Hashage sécurisé** des mots de passe (Werkzeug)
- **Protection CSRF** sur tous les formulaires
- **Validation stricte** des données d'entrée
- **Limitation du taux** de requêtes (anti-brute force)
- **En-têtes de sécurité** HTTP complets
- **Filtrage automatique** du contenu interdit

## 📊 Architecture

### Bases de Données SQLite (`db/`)
- `users.db` - Utilisateurs et authentification
- `offers.db` - Offres d'emploi et candidatures
- `services.db` - Services étudiants et avis

### Fonctionnalités Clés
- **Multilingue** : FR/DE/IT/RM avec sélecteur permanent
- **Thèmes** : Clair/Sombre/Auto (préférences navigateur)
- **Rôles** : Étudiant, Entreprise, Particulier, Admin
- **Cartes interactives** : Leaflet avec marqueurs et popups
- **Système d'avis** : Évaluation mutuelle entre utilisateurs
- **Modération** : Filtrage automatique du contenu illégal

## 🔧 Configuration

### Variables d'Environnement (`env.example`)
```bash
SECRET_KEY=your_secret_key_here
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
```

### Sécurité (`security_config.py`)
- Configuration centralisée de la sécurité
- Validation des mots de passe
- Patterns de contenu interdit
- En-têtes de sécurité HTTP

## 🧪 Tests

1. **Connexion** : Tester avec les comptes fournis
2. **Carte** : Vérifier l'affichage des marqueurs
3. **Liste** : Tester le basculement liste/carte
4. **Création** : Tester l'ajout d'offres/services
5. **Sécurité** : Vérifier les en-têtes HTTP

## 📁 Structure

```
app/
├── app.py              # Application Flask principale
├── templates/          # Templates HTML avec CSRF
├── static/            # CSS, JS corrigé, images
├── i18n/              # Traductions multilingues
└── db/                # Bases SQLite
security_config.py      # Configuration sécurité
docker-compose.yml     # Déploiement Docker
```

## 🚀 Production

> Site sécurisé et prêt pour la production avec :
> - Authentification robuste
> - Protection CSRF complète
> - Validation stricte des données
> - Interface responsive et moderne
