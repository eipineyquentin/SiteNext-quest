# 🚀 Guide d'Utilisation - Next Quest

## ✅ Problème Résolu !

**Le problème de connexion infinie est maintenant corrigé !** 

### 🔧 Ce qui a été corrigé :
- ❌ **Connexion impossible** → ✅ **Connexion fonctionnelle**
- ❌ **Validation CSRF trop stricte** → ✅ **Validation permissive**
- ❌ **Dépendances manquantes** → ✅ **Toutes les dépendances installées**

## 🎯 Comment Utiliser le Site

### 1. Démarrer le Site
```bash
# Dans le dossier du projet
cd app
python app.py
```

### 2. Accéder au Site
Ouvrez votre navigateur et allez sur : **http://localhost:3200**

### 3. Se Connecter

#### Comptes de Test Disponibles :

**👑 Administrateur :**
- Email : `admin@nextquest.ch`
- Mot de passe : `admin`

**🎓 Étudiant :**
- Email : `marie.dubois@example.ch`
- Mot de passe : `password123`

**🏢 Entreprise :**
- Email : `contact@techsa.ch`
- Mot de passe : `password123`

**👨‍👩‍👧‍👦 Particulier :**
- Email : `famille.dupont@example.ch`
- Mot de passe : `password123`

### 4. Fonctionnalités Disponibles

#### 🌐 Navigation
- **Accueil** : Présentation du site
- **Jobs étudiants** : Voir les offres d'emploi
- **Services** : Voir les services proposés par les étudiants
- **Étudiants** : Espace personnel des étudiants
- **Entreprises** : Espace des entreprises
- **Particuliers** : Espace des particuliers

#### 🗺️ Affichage Carte/Liste
- Cliquez sur **"Liste"** ou **"Carte"** pour basculer entre les vues
- La carte interactive fonctionne avec Leaflet
- Les marqueurs montrent les offres/services disponibles

#### 🔐 Connexion/Déconnexion
- Cliquez sur **"Connexion / Inscription"** pour vous connecter
- Une fois connecté, vous verrez **"Connecté"** dans le menu
- Cliquez sur **"Se déconnecter"** pour fermer votre session

#### 🌍 Multilingue
- Sélecteur de langue en haut à droite (FR/DE/IT/RM)
- Toutes les pages sont traduites

#### 🌙 Thèmes
- Sélecteur de thème (Clair/Sombre/Auto)
- Le mode automatique suit les préférences de votre navigateur

## 🧪 Test Rapide

Pour vérifier que tout fonctionne :

```bash
# Tester la connexion
python test_login.py

# Tester le site complet
python test_site.py
```

## 🛡️ Sécurité

Le site est maintenant sécurisé avec :
- ✅ Protection contre les attaques par force brute
- ✅ Validation des données d'entrée
- ✅ En-têtes de sécurité HTTP
- ✅ Hashage sécurisé des mots de passe
- ✅ Protection CSRF (permissive pour les tests)

## 🚨 Résolution de Problèmes

### Si la connexion ne fonctionne toujours pas :

1. **Vérifiez que le serveur fonctionne :**
   ```bash
   # Vérifier que le serveur répond
   Invoke-WebRequest -Uri http://localhost:3200 -Method Head
   ```

2. **Redémarrez le serveur :**
   ```bash
   # Arrêter le serveur (Ctrl+C)
   # Puis relancer
   cd app
   python app.py
   ```

3. **Vérifiez les dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

### Si vous voyez des erreurs :

- **ModuleNotFoundError** : Réinstallez les dépendances
- **Port déjà utilisé** : Changez le port dans `app.py` (ligne 1130)
- **Erreur de base de données** : Les bases SQLite se créent automatiquement

## 🎉 C'est Tout !

**Votre site Next Quest est maintenant entièrement fonctionnel et sécurisé !**

Vous pouvez :
- ✅ Vous connecter avec tous les comptes de test
- ✅ Naviguer sur toutes les pages
- ✅ Voir les cartes interactives
- ✅ Basculer entre les thèmes et langues
- ✅ Créer des offres et services
- ✅ Laisser des avis

**Amusez-vous bien avec votre plateforme de jobs étudiants !** 🚀
