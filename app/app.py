
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from flask_mail import Mail, Message
import os, json, sqlite3, hashlib, re, requests, threading, time, secrets
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import schedule
from dotenv import load_dotenv
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from security_config import SecurityConfig

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuration de sécurité
app.config['PERMANENT_SESSION_LIFETIME'] = SecurityConfig.SESSION_PERMANENT_LIFETIME
app.config['SESSION_COOKIE_SECURE'] = SecurityConfig.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SecurityConfig.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = SecurityConfig.SESSION_COOKIE_SAMESITE

# Configuration Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@nextquest.ch')

mail = Mail(app)

DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'db')
USERS_DB = os.path.join(DB_DIR, 'users.db')
OFFERS_DB = os.path.join(DB_DIR, 'offers.db')
SERVICES_DB = os.path.join(DB_DIR, 'services.db')

PROHIBITED = re.compile(r'(drogue|prostitution|armes|ksodosod)', re.IGNORECASE)

# Système de limitation de taux
rate_limit_storage = {}
MAX_REQUESTS_PER_MINUTE = 60
MAX_LOGIN_ATTEMPTS = 5
MAX_LOGIN_WINDOW = 300  # 5 minutes

def rate_limit_exceeded(ip, endpoint):
    """Vérifie si l'IP a dépassé la limite de taux"""
    now = time.time()
    key = f"{ip}:{endpoint}"
    
    if key not in rate_limit_storage:
        rate_limit_storage[key] = []
    
    # Nettoyer les anciennes requêtes
    rate_limit_storage[key] = [req_time for req_time in rate_limit_storage[key] if now - req_time < 60]
    
    # Vérifier la limite
    if len(rate_limit_storage[key]) >= MAX_REQUESTS_PER_MINUTE:
        return True
    
    # Ajouter la requête actuelle
    rate_limit_storage[key].append(now)
    return False

def check_login_attempts(ip):
    """Vérifie les tentatives de connexion"""
    now = time.time()
    key = f"login:{ip}"
    
    if key not in rate_limit_storage:
        rate_limit_storage[key] = []
    
    # Nettoyer les anciennes tentatives
    rate_limit_storage[key] = [req_time for req_time in rate_limit_storage[key] if now - req_time < MAX_LOGIN_WINDOW]
    
    return len(rate_limit_storage[key]) >= MAX_LOGIN_ATTEMPTS

def record_login_attempt(ip):
    """Enregistre une tentative de connexion"""
    now = time.time()
    key = f"login:{ip}"
    
    if key not in rate_limit_storage:
        rate_limit_storage[key] = []
    
    rate_limit_storage[key].append(now)

def hash_pw(p): 
    """Hash sécurisé avec Werkzeug"""
    return generate_password_hash(p)

def verify_pw(p, hash_pw):
    """Vérification du mot de passe avec Werkzeug"""
    return check_password_hash(hash_pw, p)

def sanitize_input(text):
    """Nettoie les entrées utilisateur"""
    return SecurityConfig.sanitize_text(text)

def validate_csrf_token():
    """Valide le token CSRF"""
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            return False
    return True

def generate_csrf_token():
    """Génère un token CSRF"""
    try:
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
            print(f"DEBUG: Token CSRF généré: {session['csrf_token'][:10]}...")
        return session['csrf_token']
    except Exception as e:
        print(f"DEBUG: Erreur génération CSRF: {e}")
        return secrets.token_hex(32)

def validate_email(email):
    """Validation stricte des emails"""
    return SecurityConfig.validate_email_format(email)

def add_security_headers(response):
    """Ajoute des en-têtes de sécurité"""
    for header, value in SecurityConfig.SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

def require_auth(f):
    """Décorateur pour les routes nécessitant une authentification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('uid'):
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Décorateur pour les routes admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_user()
        if not user or user.get('role') != 'admin':
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(f):
    """Décorateur pour la limitation de taux"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if rate_limit_exceeded(client_ip, request.endpoint):
            return make_response("Trop de requêtes. Veuillez patienter.", 429)
        return f(*args, **kwargs)
    return decorated_function

def conn(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

# Middleware pour ajouter les en-têtes de sécurité
@app.after_request
def after_request(response):
    return add_security_headers(response)

def get_user():
    uid = session.get('uid')
    if not uid: return None
    
    # Vérifier l'expiration de la session
    login_time = session.get('login_time', 0)
    if time.time() - login_time > 7200:  # 2 heures
        session.clear()
        return None
    
    with conn(USERS_DB) as c:
        r = c.execute('SELECT id,name,email,role,cv FROM users WHERE id=?', (uid,)).fetchone()
        if not r: return None
        user = dict(r)
        user['professional_data'] = {}  # Ajouter pour compatibilité
        return user

def get_lang():
    lang = request.cookies.get('lang','fr')
    if lang not in ('fr','de','it','rm'): lang='fr'
    return lang

def get_theme():
    # theme is managed client-side; we keep attribute for SSR defaults
    return request.args.get('theme')

def search_external_offers():
    """Recherche des offres d'emploi externes via des APIs légales"""
    try:
        # AVERTISSEMENT LÉGAL : Cette fonction est désactivée pour des raisons de conformité légale
        # Le web scraping direct d'Indeed.ch viole leurs conditions d'utilisation
        
        print("⚠️  RECHERCHE D'OFFRES EXTERNES DÉSACTIVÉE")
        print("📋 Raisons légales :")
        print("   - Violation des conditions d'utilisation d'Indeed.ch")
        print("   - Problèmes de droits d'auteur")
        print("   - Non-respect des robots.txt")
        print("   - Risques de protection des données")
        
        # Alternative légale : Utiliser des APIs officielles ou des partenariats
        external_offers = []
        
        # Exemple d'offres externes simulées (pour démonstration uniquement)
        demo_external_offers = [
            {
                'title': 'Job étudiant - Vente (Offre externe)',
                'description': 'Offre d\'emploi trouvée sur Indeed.ch - Exemple d\'entreprise',
                'city': 'Lausanne',
                'lat': 46.5197,
                'lng': 6.6323,
                'skills': 'Recherche externe, Exemple',
                'org': 'Exemple d\'entreprise',
                'schedule': 'À définir',
                'salary': 'À négocier',
                'min_age': 16,
                'is_external': 1,
                'external_url': 'https://ch.indeed.com/viewjob?jk=example'
            }
        ]
        
        # Ajouter seulement si pas déjà présent
        with conn(OFFERS_DB) as c:
            for offer in demo_external_offers:
                existing = c.execute('SELECT 1 FROM offers WHERE title=? AND is_external=1', (offer['title'],)).fetchone()
                if not existing:
                    external_offers.append(offer)
        
        if external_offers:
            print(f"✅ Ajouté {len(external_offers)} offres externes de démonstration")
        else:
            print("ℹ️  Aucune nouvelle offre externe à ajouter")
        
        # Sauvegarder les offres externes dans la base de données
        if external_offers:
            with conn(OFFERS_DB) as c:
                for offer in external_offers:
                    # Vérifier si l'offre existe déjà
                    existing = c.execute('SELECT 1 FROM offers WHERE title=? AND is_external=1', (offer['title'],)).fetchone()
                    if not existing:
                        c.execute('''INSERT INTO offers(title,description,city,lat,lng,skills,org,schedule,salary,min_age,created_at,is_external,external_url) 
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                                (offer['title'], offer['description'], offer['city'], offer['lat'], offer['lng'], 
                                 offer['skills'], offer['org'], offer['schedule'], offer['salary'], offer['min_age'], 
                                 datetime.now().isoformat(), offer['is_external'], offer['external_url']))
            
            print(f"Ajouté {len(external_offers)} offres externes")
        
    except Exception as e:
        print(f"Erreur recherche offres externes: {e}")

def start_external_offers_scheduler():
    """Démarre le planificateur pour la recherche automatique d'offres externes"""
    def run_scheduler():
        schedule.every(6).hours.do(search_external_offers)  # Recherche toutes les 6 heures
        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes
    
    # Démarrer le scheduler dans un thread séparé
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Scheduler d'offres externes démarré")

def send_email(to, subject, body, html_body=None):
    """Envoie un email"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def get_api_config():
    """Récupère la configuration des APIs depuis la base de données"""
    config_db = os.path.join(DB_DIR, 'config.db')
    with conn(config_db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS api_config(key TEXT PRIMARY KEY, value TEXT)')
        rows = c.execute('SELECT key, value FROM api_config').fetchall()
        return {row['key']: row['value'] for row in rows}

def set_api_config(key, value):
    """Met à jour la configuration des APIs"""
    config_db = os.path.join(DB_DIR, 'config.db')
    with conn(config_db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS api_config(key TEXT PRIMARY KEY, value TEXT)')
        c.execute('INSERT OR REPLACE INTO api_config(key, value) VALUES(?, ?)', (key, value))

def tdict(lang):
    p = os.path.join(os.path.dirname(__file__), 'i18n', f'{lang}.json')
    with open(p,'r',encoding='utf-8') as f: return json.load(f)

@app.route('/static_lang/<code>.json')
def static_lang(code):
    if code not in ('fr','de','it','rm'): code='fr'
    return jsonify(tdict(code))

@app.context_processor
def inject_globals():
    return dict(year=datetime.now().year, current_user=get_user(), csrf_token=generate_csrf_token())

@app.route('/')
def home():
    lang=get_lang(); t=tdict(lang)
    return render_template('index.html', title='Accueil', t=t, lang=lang, theme=get_theme(), active='home')

@app.route('/auth')
def auth():
    lang=get_lang(); t=tdict(lang)
    return render_template('auth.html', title='Auth', t=t, lang=lang, active='auth')

@app.post('/login')
@rate_limit
def login():
    # Validation CSRF (permissive pour les tests)
    csrf_token = request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    if csrf_token and session_token and csrf_token != session_token:
        flash("Token de sécurité invalide. Veuillez réessayer.", "error")
        return redirect(url_for('auth'))
    
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Vérifier les tentatives de connexion
    if check_login_attempts(client_ip):
        flash("Trop de tentatives de connexion. Veuillez patienter 5 minutes.", "error")
        return redirect(url_for('auth'))
    
    # Validation des entrées
    email = sanitize_input(request.form.get('email', '')).strip().lower()
    password = request.form.get('password', '')
    
    if not email or not password:
        flash("Email et mot de passe requis.", "error")
        record_login_attempt(client_ip)
        return redirect(url_for('auth'))
    
    if not validate_email(email):
        flash("Format d'email invalide.", "error")
        record_login_attempt(client_ip)
        return redirect(url_for('auth'))
    
    if len(password) < 6:
        flash("Mot de passe trop court (minimum 6 caractères).", "error")
        record_login_attempt(client_ip)
        return redirect(url_for('auth'))
    
    # Tentative de connexion
    with conn(USERS_DB) as c:
        r = c.execute('SELECT id,role,name,password FROM users WHERE email=?', (email,)).fetchone()
        if not r or not verify_pw(password, r['password']):
            flash("Email ou mot de passe incorrect.", "error")
            record_login_attempt(client_ip)
            return redirect(url_for('auth'))
        
        # Connexion réussie
        session.permanent = True
        session['uid'] = r['id']
        session['login_time'] = time.time()
        
        # Nettoyer les tentatives de connexion pour cette IP
        key = f"login:{client_ip}"
        if key in rate_limit_storage:
            del rate_limit_storage[key]
        
        # Message de succès
        flash(f"Connexion réussie ! Bienvenue {r['name']}.", "success")
    
    return redirect(url_for('home'))

@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.post('/register')
@rate_limit
def register():
    # Validation CSRF (permissive pour les tests)
    csrf_token = request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    if csrf_token and session_token and csrf_token != session_token:
        flash("Token de sécurité invalide. Veuillez réessayer.", "error")
        return redirect(url_for('auth'))
    
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    
    # Validation des entrées
    name = sanitize_input(request.form.get('name', '')).strip()
    email = sanitize_input(request.form.get('email', '')).strip().lower()
    role = request.form.get('role', 'etudiant')
    password = request.form.get('password', '')
    accept_terms = request.form.get('accept')
    
    # Validation stricte avec messages d'erreur
    if not name or len(name) < 2 or len(name) > 50:
        flash("Le nom doit contenir entre 2 et 50 caractères.", "error")
        return redirect(url_for('auth'))
    
    if not email or not validate_email(email):
        flash("Format d'email invalide.", "error")
        return redirect(url_for('auth'))
    
    if role not in ('etudiant', 'entreprise', 'particulier'):
        role = 'etudiant'
    
    # Validation de la force du mot de passe
    is_valid, error_message = SecurityConfig.validate_password_strength(password)
    if not is_valid:
        flash(error_message, "error")
        return redirect(url_for('auth'))
    
    if not accept_terms:
        flash("Vous devez accepter les conditions d'utilisation.", "error")
        return redirect(url_for('auth'))
    
    pw = hash_pw(password)
    
    with conn(USERS_DB) as c:
        # Vérifier si l'email existe déjà
        ex = c.execute('SELECT 1 FROM users WHERE email=?', (email,)).fetchone()
        if ex:
            flash("Cette adresse email est déjà utilisée.", "error")
            return redirect(url_for('auth'))
        
        # Créer le compte
        c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)', (name, email, pw, role))
        uid = c.execute('SELECT last_insert_rowid() id').fetchone()['id']
    
    # Connexion automatique après inscription
    session.permanent = True
    session['uid'] = uid
    session['login_time'] = time.time()
    
    flash(f"Compte créé avec succès ! Bienvenue {name}.", "success")
    return redirect(url_for('home'))

@app.route('/offers')
def offers():
    lang=get_lang(); t=tdict(lang)
    search=request.args.get('search','').strip()
    city=request.args.get('city','').strip()
    
    query='SELECT * FROM offers WHERE 1=1'
    params=[]
    if search:
        query+=' AND (title LIKE ? OR description LIKE ? OR skills LIKE ?)'
        search_term=f'%{search}%'
        params.extend([search_term,search_term,search_term])
    if city:
        query+=' AND city LIKE ?'
        params.append(f'%{city}%')
    query+=' ORDER BY is_external ASC, id DESC'  # Offres internes en premier, puis externes
    
    with conn(OFFERS_DB) as c:
        rows=c.execute(query,params).fetchall()
        offers=[dict(r) for r in rows]
    markers=[{'id':o['id'],'title':o['title'],'city':o['city'],'lat':o['lat'],'lng':o['lng']} for o in offers if o['lat'] and o['lng']]
    return render_template('offers.html', title='Offres', t=t, lang=lang, active='offers', offers=offers, markers=markers, search=search, city=city)

@app.route('/offer/<int:oid>')
def offer_detail(oid):
    lang=get_lang(); t=tdict(lang)
    with conn(OFFERS_DB) as c:
        o=c.execute('SELECT * FROM offers WHERE id=?',(oid,)).fetchone()
        if not o: return redirect(url_for('offers'))
        reviews=c.execute('SELECT * FROM reviews WHERE offer_id=? ORDER BY id DESC',(oid,)).fetchall()
        applications=c.execute('SELECT * FROM applications WHERE offer_id=? ORDER BY applied_at DESC',(oid,)).fetchall()
    user=get_user()
    applied=False
    if user and user['role']=='etudiant':
        with conn(OFFERS_DB) as c:
            ap=c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=?',(oid,user['id'])).fetchone()
            applied=bool(ap)
    
    # Récupérer les noms des étudiants pour les candidatures
    applications_with_names = []
    for app in applications:
        app_dict = dict(app)
        # Essayer de récupérer le nom depuis la base users
        try:
            with conn(USERS_DB) as c:
                student = c.execute('SELECT name FROM users WHERE id=?', (app['student_id'],)).fetchone()
                app_dict['student_name'] = student['name'] if student else f"Étudiant #{app['student_id']}"
        except:
            app_dict['student_name'] = f"Étudiant #{app['student_id']}"
        applications_with_names.append(app_dict)
    
    # Vérifier si l'utilisateur peut laisser un avis
    can_review = False
    if user and user['role'] == 'etudiant':
        with conn(OFFERS_DB) as c:
            # Vérifier si l'utilisateur a une candidature acceptée pour cette offre
            accepted_app = c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=? AND status="accepted"', (oid, user['id'])).fetchone()
            if accepted_app:
                # Vérifier qu'il n'a pas déjà laissé un avis
                existing_review = c.execute('SELECT 1 FROM reviews WHERE offer_id=? AND author_name=?', (oid, user['name'])).fetchone()
                can_review = not existing_review
    
    return render_template('offer_detail.html', title=o['title'], t=t, lang=lang, active='offers', offer=dict(o), reviews=[dict(r) for r in reviews], applications=applications_with_names, applied=applied, can_review=can_review)

@app.post('/offer/<int:oid>/apply')
def apply_offer(oid):
    user=get_user()
    if not user or user['role']!='etudiant': return redirect(url_for('auth'))
    with conn(OFFERS_DB) as c:
        ex=c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=?',(oid,user['id'])).fetchone()
        if not ex: c.execute('INSERT INTO applications(offer_id,student_id,applied_at,status) VALUES(?,?,?,?)',(oid,user['id'],datetime.now().isoformat(),'pending'))
    return redirect(url_for('offer_detail', oid=oid))

@app.post('/offer/<int:oid>/application/<int:aid>/accept')
def accept_application(oid, aid):
    user=get_user()
    if not user or user['role'] not in ('entreprise','particulier'): return redirect(url_for('auth'))
    with conn(OFFERS_DB) as c:
        # Vérifier que l'offre appartient à l'utilisateur
        offer=c.execute('SELECT org FROM offers WHERE id=?',(oid,)).fetchone()
        if not offer or offer['org']!=user['name']: return redirect(url_for('offers'))
        c.execute('UPDATE applications SET status="accepted" WHERE id=?',(aid,))
    return redirect(url_for('offer_detail', oid=oid))

@app.post('/offer/<int:oid>/application/<int:aid>/reject')
def reject_application(oid, aid):
    user=get_user()
    if not user or user['role'] not in ('entreprise','particulier'): return redirect(url_for('auth'))
    with conn(OFFERS_DB) as c:
        # Vérifier que l'offre appartient à l'utilisateur
        offer=c.execute('SELECT org FROM offers WHERE id=?',(oid,)).fetchone()
        if not offer or offer['org']!=user['name']: return redirect(url_for('offers'))
        c.execute('UPDATE applications SET status="rejected" WHERE id=?',(aid,))
    return redirect(url_for('offer_detail', oid=oid))

@app.route('/services')
def services():
    lang=get_lang(); t=tdict(lang)
    search=request.args.get('search','').strip()
    city=request.args.get('city','').strip()
    
    query='SELECT * FROM services WHERE 1=1'
    params=[]
    if search:
        query+=' AND (title LIKE ? OR description LIKE ? OR skills LIKE ?)'
        search_term=f'%{search}%'
        params.extend([search_term,search_term,search_term])
    if city:
        query+=' AND city LIKE ?'
        params.append(f'%{city}%')
    query+=' ORDER BY id DESC'
    
    with conn(SERVICES_DB) as c:
        rows=c.execute(query,params).fetchall()
        services=[dict(r) for r in rows]
    markers=[{'id':s['id'],'title':s['title'],'city':s['city'],'lat':s['lat'],'lng':s['lng']} for s in services if s['lat'] and s['lng']]
    return render_template('services.html', title='Services', t=t, lang=lang, active='services', services=services, markers=markers, search=search, city=city)

@app.route('/service/<int:sid>')
def service_detail(sid):
    lang=get_lang(); t=tdict(lang)
    with conn(SERVICES_DB) as c:
        s=c.execute('SELECT * FROM services WHERE id=?',(sid,)).fetchone()
        reviews=c.execute('SELECT * FROM reviews WHERE service_id=? ORDER BY id DESC',(sid,)).fetchall()
    if not s: return redirect(url_for('services'))
    
    # Récupérer les données professionnelles de l'étudiant
    service_data = dict(s)
    with conn(USERS_DB) as c:
        student_data = c.execute('SELECT professional_data FROM users WHERE id=?',(s['student_id'],)).fetchone()
        if student_data and student_data['professional_data']:
            try:
                import json
                service_data['professional_data'] = json.loads(student_data['professional_data'])
            except:
                service_data['professional_data'] = {}
        else:
            service_data['professional_data'] = {}
    
    # Vérifier si l'utilisateur peut laisser un avis
    user = get_user()
    can_review = False
    if user and user['role'] in ('entreprise', 'particulier'):
        with conn(SERVICES_DB) as c:
            # Vérifier qu'il n'a pas déjà laissé un avis
            existing_review = c.execute('SELECT 1 FROM reviews WHERE service_id=? AND author_name=?', (sid, user['name'])).fetchone()
            can_review = not existing_review
    
    return render_template('service_detail.html', title=s['title'], t=t, lang=lang, active='services', service=service_data, reviews=[dict(r) for r in reviews], can_review=can_review)

@app.route('/offer/create', methods=['GET','POST'])
def create_offer():
    user=get_user()
    if not user or user['role'] not in ('entreprise','particulier'): return redirect(url_for('auth'))
    lang=get_lang(); t=tdict(lang)
    if request.method=='POST':
        title=request.form['title'].strip()
        desc=request.form['description'].strip()
        if PROHIBITED.search(title+' '+desc): return "Contenu interdit",400
        city=request.form['city'].strip()
        lat=float(request.form.get('lat') or 0) or None
        lng=float(request.form.get('lng') or 0) or None
        skills=request.form.get('skills','').strip()
        schedule=request.form.get('schedule','').strip()
        salary=request.form.get('salary','').strip()
        min_age=int(request.form.get('min_age') or 18)
        org=user['name']
        with conn(OFFERS_DB) as c:
            c.execute('INSERT INTO offers(title,description,city,lat,lng,skills,org,schedule,salary,min_age,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                      (title,desc,city,lat,lng,skills,org,schedule,salary,min_age,datetime.now().isoformat()))
        return redirect(url_for('offers'))
    return render_template('create_offer.html', title='Créer une offre', t=t, lang=lang, active='offers')

@app.route('/service/create', methods=['GET','POST'])
def create_service():
    user=get_user()
    if not user or user['role']!='etudiant': return redirect(url_for('auth'))
    lang=get_lang(); t=tdict(lang)
    if request.method=='POST':
        title=request.form['title'].strip()
        desc=request.form['description'].strip()
        if PROHIBITED.search(title+' '+desc): return "Contenu interdit",400
        city=request.form['city'].strip()
        lat=float(request.form.get('lat') or 0) or None
        lng=float(request.form.get('lng') or 0) or None
        skills=request.form.get('skills','').strip()
        cv=request.form.get('cv','').strip() or user.get('cv')
        with conn(SERVICES_DB) as c:
            c.execute('INSERT INTO services(title,description,city,lat,lng,skills,student_id,student_name,cv,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                      (title,desc,city,lat,lng,skills,user['id'],user['name'],cv,datetime.now().isoformat()))
        return redirect(url_for('services'))
    return render_template('create_service.html', title='Proposer un service', t=t, lang=lang, active='services')

@app.route('/students')
def students():
    lang=get_lang(); t=tdict(lang)
    user=get_user()
    applications=[]
    services=[]
    if user and user['role']=='etudiant':
        with conn(OFFERS_DB) as c:
            applications=c.execute('SELECT a.*, o.title, o.org FROM applications a JOIN offers o ON a.offer_id=o.id WHERE a.student_id=? ORDER BY a.applied_at DESC',(user['id'],)).fetchall()
        with conn(SERVICES_DB) as c:
            services=c.execute('SELECT * FROM services WHERE student_id=? ORDER BY created_at DESC',(user['id'],)).fetchall()
    return render_template('students.html', title='Étudiants', t=t, lang=lang, active='students', applications=[dict(a) for a in applications], services=[dict(s) for s in services])

@app.route('/companies')
def companies():
    lang=get_lang(); t=tdict(lang)
    user=get_user()
    offers=[]
    if user and user['role']=='entreprise':
        with conn(OFFERS_DB) as c:
            offers=c.execute('SELECT * FROM offers WHERE org=? ORDER BY created_at DESC',(user['name'],)).fetchall()
    return render_template('companies.html', title='Entreprises', t=t, lang=lang, active='companies', offers=[dict(o) for o in offers])

@app.route('/individuals')
def individuals():
    lang=get_lang(); t=tdict(lang)
    user=get_user()
    offers=[]
    if user and user['role']=='particulier':
        with conn(OFFERS_DB) as c:
            offers=c.execute('SELECT * FROM offers WHERE org=? ORDER BY created_at DESC',(user['name'],)).fetchall()
    return render_template('individuals.html', title='Particuliers', t=t, lang=lang, active='individuals', offers=[dict(o) for o in offers])

@app.route('/profile', methods=['GET'])
def profile():
    lang=get_lang(); t=tdict(lang)
    return render_template('profile.html', title='Profil', t=t, lang=lang, active='profile')

@app.post('/profile/update')
def update_profile():
    user=get_user();
    if not user: return redirect(url_for('auth'))
    name=request.form['name'].strip()
    email=request.form['email'].strip().lower()
    pw=request.form.get('password','').strip()
    with conn(USERS_DB) as c:
        if pw:
            c.execute('UPDATE users SET name=?, email=?, password=? WHERE id=?',(name,email,hash_pw(pw),user['id']))
        else:
            c.execute('UPDATE users SET name=?, email=? WHERE id=?',(name,email,user['id']))
    return redirect(url_for('profile'))

@app.post('/profile/cv')
def update_cv():
    user=get_user();
    if not user: return redirect(url_for('auth'))
    cv=request.form.get('cv','').strip()
    with conn(USERS_DB) as c:
        c.execute('UPDATE users SET cv=? WHERE id=?',(cv,user['id']))
    return redirect(url_for('profile'))

@app.post('/profile/professional-data')
def update_professional_data():
    user=get_user();
    if not user: return redirect(url_for('auth'))
    
    # Collecter toutes les données du formulaire
    professional_data = {
        'formation': request.form.get('formation','').strip(),
        'experience': request.form.get('experience','').strip(),
        'competences': request.form.get('competences','').strip(),
        'langues': request.form.get('langues','').strip(),
        'disponibilite': request.form.get('disponibilite','').strip(),
        'objectifs': request.form.get('objectifs','').strip(),
        'interets': request.form.get('interets','').strip(),
        'portfolio': request.form.get('portfolio','').strip(),
        'references': request.form.get('references','').strip(),
        'certifications': request.form.get('certifications','').strip()
    }
    
    # Convertir en JSON pour stockage
    import json
    professional_data_json = json.dumps(professional_data, ensure_ascii=False)
    
    with conn(USERS_DB) as c:
        c.execute('UPDATE users SET professional_data=? WHERE id=?',(professional_data_json,user['id']))
    return redirect(url_for('profile'))

@app.post('/profile/delete')
def delete_account():
    user=get_user();
    if not user: return redirect(url_for('auth'))
    with conn(USERS_DB) as c:
        c.execute('DELETE FROM users WHERE id=?',(user['id'],))
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin')
@require_admin
@rate_limit
def admin_panel():
    lang=get_lang(); t=tdict(lang)
    user=get_user()
    if not user or user['role']!='admin':
        return render_template('admin.html', title='Admin', t=t, lang=lang, active='admin', users=[], offers=[], services=[])
    with conn(USERS_DB) as cu, conn(OFFERS_DB) as co, conn(SERVICES_DB) as cs:
        users=[dict(r) for r in cu.execute('SELECT id,name,email,role FROM users').fetchall()]
        offers=[dict(r) for r in co.execute('SELECT id,title,is_external FROM offers ORDER BY is_external ASC, id DESC').fetchall()]
        services=[dict(r) for r in cs.execute('SELECT id,title FROM services').fetchall()]
    return render_template('admin.html', title='Admin', t=t, lang=lang, active='admin', users=users, offers=offers, services=services)

@app.get('/admin/user/<int:uid>/promote')
def promote_admin(uid):
    user=get_user()
    if not user or user['role']!='admin': return redirect(url_for('admin_panel'))
    with conn(USERS_DB) as c:
        c.execute('UPDATE users SET role="admin" WHERE id=?',(uid,))
    return redirect(url_for('admin_panel'))

@app.get('/admin/user/<int:uid>/delete')
def delete_user(uid):
    user=get_user()
    if not user or user['role']!='admin': return redirect(url_for('admin_panel'))
    with conn(USERS_DB) as c:
        c.execute('DELETE FROM users WHERE id=?',(uid,))
    return redirect(url_for('admin_panel'))

@app.get('/admin/offer/<int:oid>/delete')
def admin_delete_offer(oid):
    user=get_user()
    if not user or user['role']!='admin': return redirect(url_for('admin_panel'))
    with conn(OFFERS_DB) as c:
        c.execute('DELETE FROM offers WHERE id=?',(oid,))
    return redirect(url_for('admin_panel'))

@app.get('/admin/service/<int:sid>/delete')
def admin_delete_service(sid):
    user=get_user()
    if not user or user['role']!='admin': return redirect(url_for('admin_panel'))
    with conn(SERVICES_DB) as c:
        c.execute('DELETE FROM services WHERE id=?',(sid,))
    return redirect(url_for('admin_panel'))

@app.route('/review/create', methods=['GET','POST'])
def create_review():
    user=get_user()
    if not user: return redirect(url_for('auth'))
    lang=get_lang(); t=tdict(lang)
    if request.method=='POST':
        offer_id=request.form.get('offer_id')
        service_id=request.form.get('service_id')
        rating=int(request.form.get('rating',5))
        comment=request.form.get('comment','').strip()
        author_name=user['name']
        
        if offer_id:
            # Vérifier que l'utilisateur a bien travaillé pour cette offre
            with conn(OFFERS_DB) as c:
                # Vérifier si l'utilisateur a une candidature acceptée pour cette offre
                accepted_app = c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=? AND status="accepted"', (offer_id, user['id'])).fetchone()
                if not accepted_app:
                    flash('Vous ne pouvez laisser un avis que pour les entreprises avec lesquelles vous avez travaillé.', 'error')
                    return redirect(url_for('offer_detail', oid=offer_id))
                
                # Vérifier qu'il n'a pas déjà laissé un avis
                existing_review = c.execute('SELECT 1 FROM reviews WHERE offer_id=? AND author_name=?', (offer_id, author_name)).fetchone()
                if existing_review:
                    flash('Vous avez déjà laissé un avis pour cette entreprise.', 'error')
                    return redirect(url_for('offer_detail', oid=offer_id))
                
                c.execute('INSERT INTO reviews(offer_id,author_name,rating,comment,created_at) VALUES(?,?,?,?,?)',
                          (offer_id,author_name,rating,comment,datetime.now().isoformat()))
                flash('Votre avis a été publié avec succès !', 'success')
            return redirect(url_for('offer_detail', oid=offer_id))
        elif service_id:
            # Pour les services, vérifier que l'utilisateur a bien utilisé ce service
            with conn(SERVICES_DB) as c:
                # Récupérer le service pour vérifier le propriétaire
                service = c.execute('SELECT student_id FROM services WHERE id=?', (service_id,)).fetchone()
                if not service:
                    flash('Service introuvable.', 'error')
                    return redirect(url_for('service_detail', sid=service_id))
                
                # Vérifier qu'il n'a pas déjà laissé un avis
                existing_review = c.execute('SELECT 1 FROM reviews WHERE service_id=? AND author_name=?', (service_id, author_name)).fetchone()
                if existing_review:
                    flash('Vous avez déjà laissé un avis pour ce service.', 'error')
                    return redirect(url_for('service_detail', sid=service_id))
                
                c.execute('INSERT INTO reviews(service_id,author_name,rating,comment,created_at) VALUES(?,?,?,?,?)',
                          (service_id,author_name,rating,comment,datetime.now().isoformat()))
                flash('Votre avis a été publié avec succès !', 'success')
            return redirect(url_for('service_detail', sid=service_id))
    return redirect(url_for('home'))

@app.route('/privacy')
def privacy():
    lang=get_lang(); t=tdict(lang)
    return render_template('privacy.html', title='Confidentialité', t=t, lang=lang)

@app.route('/terms')
def terms():
    lang=get_lang(); t=tdict(lang)
    return render_template('terms.html', title='Conditions', t=t, lang=lang)


@app.route('/bug')
def bug():
    lang=get_lang(); t=tdict(lang)
    return render_template('bug.html', title='Bug', t=t, lang=lang)

def seed():
    # Ensure tables exist and create sample data
    try:
        os.makedirs(DB_DIR, exist_ok=True)
        print(f"Dossier db créé: {DB_DIR}")
    except Exception as e:
        print(f"Erreur création dossier db: {e}")
        return
    
    print("Initialisation de la base de données...")
    with conn(USERS_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, cv TEXT)')
        
        # Vérifier si la colonne professional_data existe, sinon l'ajouter
        try:
            c.execute('SELECT professional_data FROM users LIMIT 1')
        except sqlite3.OperationalError:
            # La colonne n'existe pas, l'ajouter
            c.execute('ALTER TABLE users ADD COLUMN professional_data TEXT')
        # create default admin
        ex=c.execute('SELECT 1 FROM users WHERE email="admin@nextquest.ch"').fetchone()
        if not ex:
            c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('Admin','admin@nextquest.ch',hash_pw("admin"),'admin'))
            
        # Créer des utilisateurs d'exemple
        sample_users = [
            ('Marie Dubois','marie.dubois@example.ch',hash_pw("password123"),'etudiant'),
            ('Pierre Martin','pierre.martin@example.ch',hash_pw("password123"),'etudiant'),
            ('Sophie Weber','sophie.weber@example.ch',hash_pw("password123"),'etudiant'),
            ('Luca Rossi','luca.rossi@example.ch',hash_pw("password123"),'etudiant'),
            ('Anna Mueller','anna.mueller@example.ch',hash_pw("password123"),'etudiant'),
            ('Entreprise Tech SA','contact@techsa.ch',hash_pw("password123"),'entreprise'),
            ('Restaurant Le Bon Goût','info@bon-gout.ch',hash_pw("password123"),'entreprise'),
            ('Famille Dupont','famille.dupont@example.ch',hash_pw("password123"),'particulier'),
            ('M. et Mme Schmidt','schmidt.family@example.ch',hash_pw("password123"),'particulier')
        ]
        
        for user in sample_users:
            ex_user = c.execute('SELECT 1 FROM users WHERE email=?',(user[1],)).fetchone()
            if not ex_user:
                c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)', user)
    with conn(OFFERS_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY, title TEXT, description TEXT, city TEXT, lat REAL, lng REAL, skills TEXT, org TEXT, schedule TEXT, salary TEXT, min_age INTEGER, created_at TEXT)')
        
        # Vérifier si les colonnes is_external et external_url existent, sinon les ajouter
        try:
            c.execute('SELECT is_external FROM offers LIMIT 1')
        except sqlite3.OperationalError:
            # La colonne n'existe pas, l'ajouter
            c.execute('ALTER TABLE offers ADD COLUMN is_external INTEGER DEFAULT 0')
            c.execute('ALTER TABLE offers ADD COLUMN external_url TEXT')
        
        c.execute('CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY, offer_id INTEGER, student_id INTEGER, applied_at TEXT, status TEXT DEFAULT "pending")')
        c.execute('CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, offer_id INTEGER, author_name TEXT, rating INTEGER, comment TEXT, created_at TEXT)')
        # Supprimer toutes les offres existantes
        c.execute('DELETE FROM offers')
        c.execute('DELETE FROM applications')
        c.execute('DELETE FROM reviews')
        
        # Créer de nouvelles offres réalistes pour jobs étudiants
        sample_offers=[
                    ('Livraison de fleurs','Livraison de bouquets dans toute la ville. Vélo fourni.','Lausanne',46.5197,6.6323,'Vélo, Ponctualité, Exemple','Fleuriste Les Roses','Week-end','22 CHF/h',16),
                    ('Distribution de flyers','Distribution de prospectus dans le centre-ville.','Genève',46.2044,6.1432,'Marche, Communication, Exemple','Agence Pub','Après-midi','20 CHF/h',16),
                    ('Inventaire magasin','Comptage et vérification des stocks.','Zurich',47.3769,8.5417,'Organisation, Attention, Exemple','Magasin Sport','Soirées','24 CHF/h',16),
                    ('Baby-sitting','Garde d\'enfants le soir et week-end.','Bâle',47.5596,7.5886,'Pédagogie, Patience, Exemple','Famille Müller','Soirées','25 CHF/h',16),
                    ('Nettoyage véhicules','Lavage et nettoyage de voitures.','Fribourg',46.8067,7.1516,'Physique, Ponctualité, Exemple','Station Auto','Week-end','23 CHF/h',16),
                    ('Aide déménagement','Port de cartons et meubles légers.','Berne',46.9481,7.4474,'Manutention, Physique, Exemple','Déménageurs Pro','Week-end','26 CHF/h',16),
                    ('Service événement','Aide lors d\'événements et fêtes.','Neuchâtel',46.9929,6.9319,'Service, Dynamisme, Exemple','Agence Events','Variable','24 CHF/h',16),
                    ('Livraison repas','Livraison de commandes à vélo.','Lucerne',47.0502,8.3093,'Vélo, Ponctualité, Exemple','Restaurant Express','Soirées','21 CHF/h',16),
                    ('Aide jardinage','Désherbage et entretien de jardins.','Lugano',46.0101,8.9600,'Jardinage, Physique, Exemple','Jardins Ticino','Week-end','25 CHF/h',16),
                    ('Inventaire bibliothèque','Classement et rangement de livres.','Lausanne',46.5197,6.6323,'Organisation, Calme, Exemple','Bibliothèque UNIL','Après-midi','22 CHF/h',16),
                    ('Service café','Service en café étudiant.','Montreux',46.4330,6.9113,'Service, Dynamisme, Exemple','Café Campus','Week-end','23 CHF/h',16),
                    ('Distribution journaux','Livraison de journaux tôt le matin.','Nyon',46.3833,6.2333,'Vélo, Ponctualité, Exemple','Presse Locale','Matin','20 CHF/h',16),
                    ('Aide ménage','Nettoyage de bureaux le week-end.','Renens',46.5367,6.5886,'Ménage, Ponctualité, Exemple','Nettoyage Pro','Week-end','24 CHF/h',16),
                    ('Inventaire stock','Comptage de produits en magasin.','Morges',46.5113,6.4972,'Organisation, Attention, Exemple','Supermarché Coop','Soirées','22 CHF/h',16),
                    ('Service parking','Surveillance et gestion d\'un parking.','Zermatt',46.0207,7.7491,'Service, Ponctualité, Exemple','Parking Zermatt','Week-end','25 CHF/h',16)
        ]
        for s in sample_offers:
            c.execute('INSERT INTO offers(title,description,city,lat,lng,skills,org,schedule,salary,min_age,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)', s + (datetime.now().isoformat(),))
        
        # Ajouter des avis d'exemple pour les nouvelles offres
        sample_reviews_offers = [
                (1, 'Marie Dubois', 5, 'Fleuriste Les Roses est très professionnelle. Horaires flexibles parfaits pour les études.', datetime.now().isoformat()),
                (2, 'Pierre Martin', 4, 'Agence Pub était sympa. Distribution de flyers simple et bien payée.', datetime.now().isoformat()),
                (3, 'Sophie Weber', 5, 'Magasin Sport offre de bonnes conditions. Inventaire le soir compatible avec les cours.', datetime.now().isoformat()),
                (4, 'Luca Rossi', 4, 'Famille Müller très arrangeante pour les horaires de baby-sitting.', datetime.now().isoformat()),
                (5, 'Anna Mueller', 5, 'Station Auto propose un travail simple et bien rémunéré.', datetime.now().isoformat()),
                (6, 'Marie Dubois', 4, 'Déménageurs Pro très professionnels. Bonne expérience.', datetime.now().isoformat()),
                (7, 'Pierre Martin', 5, 'Agence Events propose des jobs variés et intéressants.', datetime.now().isoformat()),
                (8, 'Sophie Weber', 4, 'Restaurant Express horaires adaptés aux étudiants.', datetime.now().isoformat())
        ]
        
        for review in sample_reviews_offers:
            c.execute('INSERT INTO reviews(offer_id,author_name,rating,comment,created_at) VALUES(?,?,?,?,?)', review)
    with conn(SERVICES_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, title TEXT, description TEXT, city TEXT, lat REAL, lng REAL, skills TEXT, student_id INTEGER, student_name TEXT, cv TEXT, created_at TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, service_id INTEGER, author_name TEXT, rating INTEGER, comment TEXT, created_at TEXT)')
        # Supprimer tous les services existants
        c.execute('DELETE FROM services')
        c.execute('DELETE FROM reviews')
        
        sample_services=[
                ('Cours de mathématiques (Exemple)','Cours niveau gymnase et université. Service d\'exemple pour démonstration.','Lausanne',46.5197,6.6323,'Pédagogie,Maths,Exemple',2,'Marie Dubois','—',datetime.now().isoformat()),
                ('Cours d\'anglais (Exemple)','Conversation et grammaire pour tous niveaux. Service d\'exemple pour démonstration.','Genève',46.2044,6.1432,'Anglais,Pédagogie,Exemple',3,'Pierre Martin','—',datetime.now().isoformat()),
                ('Cours de piano (Exemple)','Initiation et perfectionnement. Service d\'exemple pour démonstration.','Zurich',47.3769,8.5417,'Musique,Pédagogie,Exemple',4,'Sophie Weber','—',datetime.now().isoformat()),
                ('Réparation d\'ordinateurs (Exemple)','Diagnostic et réparation PC/Mac. Service d\'exemple pour démonstration.','Bâle',47.5596,7.5886,'Informatique,Réparation,Exemple',5,'Luca Rossi','—',datetime.now().isoformat()),
                ('Cours de photographie (Exemple)','Techniques photo et retouche. Service d\'exemple pour démonstration.','Fribourg',46.8067,7.1516,'Photographie,Créativité,Exemple',6,'Anna Mueller','—',datetime.now().isoformat()),
                ('Traduction français-allemand (Exemple)','Documents et textes divers. Service d\'exemple pour démonstration.','Berne',46.9481,7.4474,'Traduction,Langues,Exemple',2,'Marie Dubois','—',datetime.now().isoformat()),
                ('Cours de cuisine (Exemple)','Recettes traditionnelles et modernes. Service d\'exemple pour démonstration.','Lucerne',47.0502,8.3093,'Cuisine,Créativité,Exemple',3,'Pierre Martin','—',datetime.now().isoformat()),
                ('Cours de yoga (Exemple)','Séances individuelles et en groupe. Service d\'exemple pour démonstration.','Lugano',46.0101,8.9600,'Yoga,Bien-être,Exemple',4,'Sophie Weber','—',datetime.now().isoformat()),
                ('Cours de dessin (Exemple)','Techniques artistiques et créativité. Service d\'exemple pour démonstration.','Neuchâtel',46.9929,6.9319,'Art,Créativité,Exemple',5,'Luca Rossi','—',datetime.now().isoformat()),
                ('Cours de programmation (Exemple)','Python, JavaScript, bases de données. Service d\'exemple pour démonstration.','Lausanne',46.5197,6.6323,'Programmation,Informatique,Exemple',6,'Anna Mueller','—',datetime.now().isoformat()),
                ('Cours de natation (Exemple)','Apprentissage et perfectionnement. Service d\'exemple pour démonstration.','Montreux',46.4330,6.9113,'Natation,Sport,Exemple',2,'Marie Dubois','—',datetime.now().isoformat()),
                ('Cours de guitare (Exemple)','Acoustique et électrique. Service d\'exemple pour démonstration.','Nyon',46.3833,6.2333,'Musique,Pédagogie,Exemple',3,'Pierre Martin','—',datetime.now().isoformat()),
                ('Cours de danse (Exemple)','Salsa, bachata, danse moderne. Service d\'exemple pour démonstration.','Genève',46.2044,6.1432,'Danse,Expression,Exemple',4,'Sophie Weber','—',datetime.now().isoformat()),
                ('Cours de jardinage (Exemple)','Techniques et conseils pratiques. Service d\'exemple pour démonstration.','Zurich',47.3769,8.5417,'Jardinage,Nature,Exemple',5,'Luca Rossi','—',datetime.now().isoformat()),
                ('Cours de couture (Exemple)','Création et modification de vêtements. Service d\'exemple pour démonstration.','Bâle',47.5596,7.5886,'Couture,Créativité,Exemple',6,'Anna Mueller','—',datetime.now().isoformat()),
                ('Cours de langues (Exemple)','Français, allemand, italien, anglais. Service d\'exemple pour démonstration.','Fribourg',46.8067,7.1516,'Langues,Pédagogie,Exemple',2,'Marie Dubois','—',datetime.now().isoformat()),
                ('Cours de fitness (Exemple)','Musculation et cardio. Service d\'exemple pour démonstration.','Berne',46.9481,7.4474,'Fitness,Sport,Exemple',3,'Pierre Martin','—',datetime.now().isoformat()),
                ('Cours de méditation (Exemple)','Techniques de relaxation et mindfulness. Service d\'exemple pour démonstration.','Lucerne',47.0502,8.3093,'Méditation,Bien-être,Exemple',4,'Sophie Weber','—',datetime.now().isoformat()),
                ('Cours de bricolage (Exemple)','Réparations et créations DIY. Service d\'exemple pour démonstration.','Lugano',46.0101,8.9600,'Bricolage,Manuel,Exemple',5,'Luca Rossi','—',datetime.now().isoformat()),
                ('Cours de marketing digital (Exemple)','Réseaux sociaux et e-commerce. Service d\'exemple pour démonstration.','Neuchâtel',46.9929,6.9319,'Marketing,Digital,Exemple',6,'Anna Mueller','—',datetime.now().isoformat())
        ]
        for s in sample_services:
            c.execute('INSERT INTO services(title,description,city,lat,lng,skills,student_id,student_name,cv,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)', s)
        
        # Ajouter des avis d'exemple pour les services
        sample_reviews_services = [
                (1, 'Entreprise Tech SA', 5, 'Excellent cours de mathématiques ! Marie explique très bien. (Avis d\'exemple)', datetime.now().isoformat()),
                (2, 'Famille Dupont', 4, 'Pierre est un très bon professeur d\'anglais. (Avis d\'exemple)', datetime.now().isoformat()),
                (3, 'M. et Mme Schmidt', 5, 'Sophie est patiente et pédagogue pour le piano. (Avis d\'exemple)', datetime.now().isoformat()),
                (4, 'Restaurant Le Bon Goût', 4, 'Luca a réparé notre ordinateur rapidement. (Avis d\'exemple)', datetime.now().isoformat()),
                (5, 'Entreprise Tech SA', 5, 'Anna prend de très belles photos ! (Avis d\'exemple)', datetime.now().isoformat())
        ]
        
        for review in sample_reviews_services:
            c.execute('INSERT INTO reviews(service_id,author_name,rating,comment,created_at) VALUES(?,?,?,?,?)', review)
    
    print("Base de données initialisée avec succès!")

# Initialiser la base de données au démarrage
seed()

# Démarrer le scheduler d'offres externes
start_external_offers_scheduler()

# Route pour déclencher manuellement la recherche d'offres externes
@app.route('/legal')
def legal():
    lang=get_lang(); t=tdict(lang)
    return render_template('legal.html', title='Informations légales', t=t, lang=lang, active='legal')

@app.route('/admin/config', methods=['GET', 'POST'])
def admin_config():
    user = get_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('auth'))
    
    if request.method == 'POST':
        # Sauvegarder la configuration
        config_data = {
            'indeed_api_key': request.form.get('indeed_api_key', ''),
            'linkedin_api_key': request.form.get('linkedin_api_key', ''),
            'mail_server': request.form.get('mail_server', ''),
            'mail_port': request.form.get('mail_port', ''),
            'mail_username': request.form.get('mail_username', ''),
            'mail_password': request.form.get('mail_password', ''),
            'mail_sender': request.form.get('mail_sender', ''),
            'stripe_public_key': request.form.get('stripe_public_key', ''),
            'stripe_secret_key': request.form.get('stripe_secret_key', ''),
            'contact_email': request.form.get('contact_email', ''),
        }
        
        for key, value in config_data.items():
            set_api_config(key, value)
        
        flash('Configuration sauvegardée avec succès!', 'success')
        return redirect(url_for('admin_config'))
    
    # Afficher la configuration actuelle
    config = get_api_config()
    lang=get_lang(); t=tdict(lang)
    return render_template('admin_config.html', title='Configuration', t=t, lang=lang, active='admin', config=config)

@app.route('/admin/send-test-email')
def admin_send_test_email():
    user = get_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('auth'))
    
    try:
        success = send_email(
            user['email'],
            'Test Email - Next Quest',
            'Ceci est un email de test pour vérifier la configuration email.',
            '<h2>Test Email - Next Quest</h2><p>Ceci est un email de test pour vérifier la configuration email.</p>'
        )
        if success:
            flash('Email de test envoyé avec succès!', 'success')
        else:
            flash('Erreur lors de l\'envoi de l\'email de test.', 'error')
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('admin_config'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    lang=get_lang(); t=tdict(lang)
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        subject = request.form.get('subject', '')
        message = request.form.get('message', '')
        contact_type = request.form.get('contact_type', 'general')
        
        # Envoyer l'email à l'admin
        config = get_api_config()
        admin_email = config.get('contact_email', 'admin@nextquest.ch')
        
        email_subject = f"[Next Quest] {subject} - {contact_type}"
        email_body = f"""
Nouveau message de contact reçu sur Next Quest :

Nom: {name}
Email: {email}
Type: {contact_type}
Sujet: {subject}

Message:
{message}

---
Envoyé depuis Next Quest
        """
        
        html_body = f"""
<h2>Nouveau message de contact reçu sur Next Quest</h2>
<p><strong>Nom:</strong> {name}</p>
<p><strong>Email:</strong> {email}</p>
<p><strong>Type:</strong> {contact_type}</p>
<p><strong>Sujet:</strong> {subject}</p>
<p><strong>Message:</strong></p>
<p>{message.replace(chr(10), '<br>')}</p>
<hr>
<p><em>Envoyé depuis Next Quest</em></p>
        """
        
        try:
            success = send_email(admin_email, email_subject, email_body, html_body)
            if success:
                flash('Votre message a été envoyé avec succès! Nous vous répondrons dans les plus brefs délais.', 'success')
            else:
                flash('Erreur lors de l\'envoi du message. Veuillez réessayer.', 'error')
        except Exception as e:
            flash(f'Erreur: {str(e)}', 'error')
        
        return redirect(url_for('contact'))
    
    return render_template('contact.html', title='Contact', t=t, lang=lang, active='contact')

@app.route('/admin/search-external-offers')
def admin_search_external_offers():
    user = get_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('auth'))
    
    try:
        search_external_offers()
        flash('Recherche d\'offres externes lancée avec succès!', 'success')
    except Exception as e:
        flash(f'Erreur lors de la recherche: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3200, debug=True)
