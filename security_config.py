"""
Configuration de sécurité pour Next Quest
"""

import os
import secrets
from datetime import timedelta

class SecurityConfig:
    """Configuration de sécurité centralisée"""
    
    # Configuration des sessions
    SESSION_PERMANENT_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False  # True en production avec HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuration des mots de passe
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = False
    
    # Limitation de taux
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_LOGIN_ATTEMPTS = 5
    MAX_LOGIN_WINDOW = 300  # 5 minutes
    
    # Validation des entrées
    MAX_NAME_LENGTH = 50
    MAX_EMAIL_LENGTH = 254
    MAX_DESCRIPTION_LENGTH = 1000
    
    # Contenu interdit
    PROHIBITED_PATTERNS = [
        r'(drogue|prostitution|armes|ksodosod)',
        r'(violence|haine|discrimination)',
        r'(spam|scam|arnaque)',
        r'(pornographie|sexe)',
        r'(terrorisme|extrémisme)'
    ]
    
    # En-têtes de sécurité
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        # Autoriser Leaflet (unpkg) et les tuiles OpenStreetMap pour corriger l'affichage carte
        'Content-Security-Policy': "default-src 'self'; "
                                  "script-src 'self' 'unsafe-inline' https://unpkg.com; "
                                  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
                                  "font-src 'self' https://fonts.gstatic.com; "
                                  "img-src 'self' data: https://unpkg.com https://tile.openstreetmap.org https://*.tile.openstreetmap.org; "
                                  "connect-src 'self'"
    }
    
    @staticmethod
    def generate_secret_key():
        """Génère une clé secrète sécurisée"""
        return secrets.token_hex(32)
    
    @staticmethod
    def validate_password_strength(password):
        """Valide la force du mot de passe"""
        if len(password) < SecurityConfig.PASSWORD_MIN_LENGTH:
            return False, "Le mot de passe doit contenir au moins 8 caractères"
        
        if SecurityConfig.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False, "Le mot de passe doit contenir au moins une majuscule"
        
        if SecurityConfig.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False, "Le mot de passe doit contenir au moins une minuscule"
        
        if SecurityConfig.PASSWORD_REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            return False, "Le mot de passe doit contenir au moins un chiffre"
        
        return True, "Mot de passe valide"
    
    @staticmethod
    def sanitize_text(text):
        """Nettoie le texte des caractères dangereux"""
        if not text:
            return ""
        
        # Supprimer les caractères dangereux
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '|', '`', '$']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text.strip()
    
    @staticmethod
    def validate_email_format(email):
        """Valide le format de l'email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def check_prohibited_content(text):
        """Vérifie si le contenu contient des éléments interdits"""
        import re
        text_lower = text.lower()
        for pattern in SecurityConfig.PROHIBITED_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True, f"Contenu interdit détecté: {pattern}"
        return False, "Contenu valide"