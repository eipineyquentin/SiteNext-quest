# 🚀 Next Quest - Guide de mise en production

## 📋 Préparation pour la mise en ligne

### 1. Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```bash
# Clé secrète Flask (OBLIGATOIRE)
SECRET_KEY=votre-cle-secrete-tres-longue-et-securisee

# Configuration Email (pour l'envoi automatique)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=votre-email@gmail.com
MAIL_PASSWORD=votre-mot-de-passe-application
MAIL_DEFAULT_SENDER=noreply@nextquest.ch

# APIs externes (optionnel)
INDEED_API_KEY=votre-cle-api-indeed
LINKEDIN_API_KEY=votre-cle-api-linkedin

# Paiements Stripe (optionnel)
STRIPE_PUBLIC_KEY=pk_live_votre-cle-publique-stripe
STRIPE_SECRET_KEY=sk_live_votre-cle-secrete-stripe

# Email de contact
CONTACT_EMAIL=contact@nextquest.ch
```

### 2. Configuration Email (Gmail)

1. **Activez l'authentification à 2 facteurs** sur votre compte Gmail
2. **Générez un mot de passe d'application** :
   - Allez dans Paramètres Google > Sécurité
   - Activez l'authentification à 2 facteurs
   - Générez un mot de passe d'application
   - Utilisez ce mot de passe dans `MAIL_PASSWORD`

### 3. Configuration des APIs

#### Indeed API
- Visitez : https://ads.indeed.com/jobroll/xmlfeed
- Créez un compte développeur
- Obtenez votre clé API
- Ajoutez-la dans `INDEED_API_KEY`

#### LinkedIn API
- Visitez : https://developer.linkedin.com/
- Créez une application LinkedIn
- Obtenez votre clé API
- Ajoutez-la dans `LINKEDIN_API_KEY`

#### Stripe (Paiements)
- Visitez : https://dashboard.stripe.com/
- Créez un compte Stripe
- Obtenez vos clés de production
- Ajoutez-les dans `STRIPE_PUBLIC_KEY` et `STRIPE_SECRET_KEY`

### 4. Déploiement Docker

```bash
# Construire et démarrer le conteneur
docker-compose up --build -d

# Vérifier que le conteneur fonctionne
docker ps

# Voir les logs
docker logs siteinternet-web-1
```

### 5. Configuration Admin

1. **Connectez-vous** avec le compte admin par défaut :
   - Email : `admin@nextquest.ch`
   - Mot de passe : `admin`

2. **Allez dans l'administration** : http://votre-domaine.com/admin

3. **Configurez le système** :
   - Cliquez sur "⚙️ Configuration"
   - Remplissez tous les champs nécessaires
   - Testez l'envoi d'emails
   - Sauvegardez la configuration

### 6. Sécurité

#### Changer le mot de passe admin
```bash
# Connectez-vous et changez le mot de passe admin
# Ou modifiez directement dans la base de données
```

#### Configuration HTTPS
- Utilisez un reverse proxy (Nginx, Apache)
- Configurez SSL/TLS avec Let's Encrypt
- Redirigez HTTP vers HTTPS

### 7. Monitoring et maintenance

#### Logs
```bash
# Voir les logs en temps réel
docker logs -f siteinternet-web-1

# Sauvegarder les logs
docker logs siteinternet-web-1 > logs.txt
```

#### Sauvegarde des données
```bash
# Sauvegarder les bases de données
cp -r db/ backup/db-$(date +%Y%m%d)/
```

#### Mise à jour
```bash
# Arrêter le conteneur
docker-compose down

# Mettre à jour le code
git pull

# Reconstruire et redémarrer
docker-compose up --build -d
```

### 8. Fonctionnalités disponibles

#### ✅ Fonctionnalités implémentées
- [x] **Authentification** : Connexion/inscription avec 4 types de comptes
- [x] **Jobs étudiants** : Publication et candidature aux offres
- [x] **Services étudiants** : Proposition de services par les étudiants
- [x] **Système d'avis** : Notation et commentaires
- [x] **Multilingue** : Français, allemand, italien, romanche
- [x] **Thèmes** : Mode clair/sombre/automatique
- [x] **Administration** : Gestion des utilisateurs, offres, services
- [x] **Configuration** : APIs, emails, paiements
- [x] **Envoi d'emails** : Notifications automatiques
- [x] **Responsive** : Compatible mobile et desktop

#### 🔧 Configuration requise
- [x] **Variables d'environnement** : Fichier `.env`
- [x] **Configuration email** : SMTP pour notifications
- [x] **APIs externes** : Indeed, LinkedIn (optionnel)
- [x] **Paiements** : Stripe (optionnel)

### 9. Support et contact

- **Email** : contact@nextquest.ch
- **Support technique** : support@nextquest.ch
- **Partenariats** : partnerships@nextquest.ch

### 10. Informations légales

- **Conformité** : Respect des réglementations suisses
- **Protection des données** : Conformité LPD
- **Conditions d'utilisation** : Disponibles sur `/terms`
- **Politique de confidentialité** : Disponible sur `/privacy`

---

## 🎯 Prêt pour la mise en production !

Votre site Next Quest est maintenant configuré et prêt pour la mise en ligne. Toutes les fonctionnalités sont opérationnelles et le système est conforme aux réglementations légales.

**Bonne chance avec votre plateforme de jobs étudiants !** 🚀
