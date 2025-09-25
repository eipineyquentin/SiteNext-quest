
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
import os, json, sqlite3, hashlib, re
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY','devkey')

DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'db')
USERS_DB = os.path.join(DB_DIR, 'users.db')
OFFERS_DB = os.path.join(DB_DIR, 'offers.db')
SERVICES_DB = os.path.join(DB_DIR, 'services.db')

PROHIBITED = re.compile(r'(drogue|prostitution|armes|ksodosod)', re.IGNORECASE)

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

def conn(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def get_user():
    uid = session.get('uid')
    if not uid: return None
    with conn(USERS_DB) as c:
        r = c.execute('SELECT id,name,email,role,cv FROM users WHERE id=?', (uid,)).fetchone()
        return dict(r) if r else None

def get_lang():
    lang = request.cookies.get('lang','fr')
    if lang not in ('fr','de','it','rm'): lang='fr'
    return lang

def get_theme():
    # theme is managed client-side; we keep attribute for SSR defaults
    return request.args.get('theme')

def tdict(lang):
    p = os.path.join(os.path.dirname(__file__), 'i18n', f'{lang}.json')
    with open(p,'r',encoding='utf-8') as f: return json.load(f)

@app.route('/static_lang/<code>.json')
def static_lang(code):
    return app.send_static_file(os.path.join('..','i18n',f'{code}.json'))

@app.context_processor
def inject_globals():
    return dict(year=datetime.now().year, current_user=get_user())

@app.route('/')
def home():
    lang=get_lang(); t=tdict(lang)
    return render_template('index.html', title='Accueil', t=t, lang=lang, theme=get_theme(), active='home')

@app.route('/auth')
def auth():
    lang=get_lang(); t=tdict(lang)
    return render_template('auth.html', title='Auth', t=t, lang=lang, active='auth')

@app.post('/login')
def login():
    email=request.form['email'].strip().lower()
    pw=hash_pw(request.form['password'])
    role=request.form.get('role')
    with conn(USERS_DB) as c:
        r=c.execute('SELECT id,role FROM users WHERE email=? AND password=?', (email,pw)).fetchone()
        if not r: return redirect(url_for('auth'))
        # optional: ensure role matches (soft check)
        session['uid']=r['id']
    return redirect(url_for('home'))

@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.post('/register')
def register():
    name=request.form['name'].strip()
    email=request.form['email'].strip().lower()
    role=request.form['role']
    if role not in ('etudiant','entreprise','particulier'): role='etudiant'
    pw=hash_pw(request.form['password'])
    with conn(USERS_DB) as c:
        ex=c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone()
        if ex: return redirect(url_for('auth'))
        c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,email,pw,role))
        uid=c.execute('SELECT last_insert_rowid() id').fetchone()['id']
    session['uid']=uid
    return redirect(url_for('home'))

@app.route('/offers')
def offers():
    lang=get_lang(); t=tdict(lang)
    with conn(OFFERS_DB) as c:
        rows=c.execute('SELECT * FROM offers ORDER BY id DESC').fetchall()
        offers=[dict(r) for r in rows]
    markers=[{'id':o['id'],'title':o['title'],'city':o['city'],'lat':o['lat'],'lng':o['lng']} for o in offers if o['lat'] and o['lng']]
    return render_template('offers.html', title='Offres', t=t, lang=lang, active='offers', offers=offers, markers=markers)

@app.route('/offer/<int:oid>')
def offer_detail(oid):
    lang=get_lang(); t=tdict(lang)
    with conn(OFFERS_DB) as c:
        o=c.execute('SELECT * FROM offers WHERE id=?',(oid,)).fetchone()
        if not o: return redirect(url_for('offers'))
        reviews=c.execute('SELECT * FROM reviews WHERE offer_id=? ORDER BY id DESC',(oid,)).fetchall()
    user=get_user()
    applied=False
    if user and user['role']=='etudiant':
        with conn(OFFERS_DB) as c:
            ap=c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=?',(oid,user['id'])).fetchone()
            applied=bool(ap)
    return render_template('offer_detail.html', title=o['title'], t=t, lang=lang, active='offers', offer=dict(o), reviews=[dict(r) for r in reviews], applied=applied)

@app.post('/offer/<int:oid>/apply')
def apply_offer(oid):
    user=get_user()
    if not user or user['role']!='etudiant': return redirect(url_for('auth'))
    with conn(OFFERS_DB) as c:
        ex=c.execute('SELECT 1 FROM applications WHERE offer_id=? AND student_id=?',(oid,user['id'])).fetchone()
        if not ex: c.execute('INSERT INTO applications(offer_id,student_id,applied_at) VALUES(?,?,?)',(oid,user['id'],datetime.now().isoformat()))
    return redirect(url_for('offer_detail', oid=oid))

@app.route('/services')
def services():
    lang=get_lang(); t=tdict(lang)
    with conn(SERVICES_DB) as c:
        rows=c.execute('SELECT * FROM services ORDER BY id DESC').fetchall()
        services=[dict(r) for r in rows]
    markers=[{'id':s['id'],'title':s['title'],'city':s['city'],'lat':s['lat'],'lng':s['lng']} for s in services if s['lat'] and s['lng']]
    return render_template('services.html', title='Services', t=t, lang=lang, active='services', services=services, markers=markers)

@app.route('/service/<int:sid>')
def service_detail(sid):
    lang=get_lang(); t=tdict(lang)
    with conn(SERVICES_DB) as c:
        s=c.execute('SELECT * FROM services WHERE id=?',(sid,)).fetchone()
        reviews=c.execute('SELECT * FROM reviews WHERE service_id=? ORDER BY id DESC',(sid,)).fetchall()
    if not s: return redirect(url_for('services'))
    return render_template('service_detail.html', title=s['title'], t=t, lang=lang, active='services', service=dict(s), reviews=[dict(r) for r in reviews])

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
    # simple form
    return f"""
    <html><head><link rel='stylesheet' href='/static/css/style.css'></head><body class='container'>
    <h1>Proposer un service</h1>
    <form method='post'>
      <div class='form-group'><label>Titre</label><input name='title' required></div>
      <div class='form-group'><label>Description</label><textarea name='description' rows='4' required></textarea></div>
      <div class='form-group'><label>Ville</label><input name='city' required></div>
      <div class='form-group'><label>Latitude</label><input name='lat' type='number' step='any'></div>
      <div class='form-group'><label>Longitude</label><input name='lng' type='number' step='any'></div>
      <div class='form-group'><label>Compétences (séparées par des virgules)</label><input name='skills'></div>
      <div class='form-group'><label>Mini‑CV</label><textarea name='cv' rows='3'></textarea></div>
      <button class='btn btn--primary'>Publier</button>
    </form></body></html>
    """

@app.route('/students')
def students():
    lang=get_lang(); t=tdict(lang)
    return render_template('students.html', title='Étudiants', t=t, lang=lang, active='students')

@app.route('/companies')
def companies():
    lang=get_lang(); t=tdict(lang)
    return render_template('companies.html', title='Entreprises', t=t, lang=lang, active='companies')

@app.route('/individuals')
def individuals():
    lang=get_lang(); t=tdict(lang)
    return render_template('individuals.html', title='Particuliers', t=t, lang=lang, active='individuals')

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

@app.post('/profile/delete')
def delete_account():
    user=get_user();
    if not user: return redirect(url_for('auth'))
    with conn(USERS_DB) as c:
        c.execute('DELETE FROM users WHERE id=?',(user['id'],))
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin')
def admin_panel():
    lang=get_lang(); t=tdict(lang)
    user=get_user()
    if not user or user['role']!='admin':
        return render_template('admin.html', title='Admin', t=t, lang=lang, active='admin', users=[], offers=[], services=[])
    with conn(USERS_DB) as cu, conn(OFFERS_DB) as co, conn(SERVICES_DB) as cs:
        users=[dict(r) for r in cu.execute('SELECT id,name,email,role FROM users').fetchall()]
        offers=[dict(r) for r in co.execute('SELECT id,title FROM offers').fetchall()]
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

@app.route('/privacy')
def privacy():
    lang=get_lang(); t=tdict(lang)
    return render_template('privacy.html', title='Confidentialité', t=t, lang=lang)

@app.route('/terms')
def terms():
    lang=get_lang(); t=tdict(lang)
    return render_template('terms.html', title='Conditions', t=t, lang=lang)

@app.route('/contact')
def contact():
    lang=get_lang(); t=tdict(lang)
    return render_template('contact.html', title='Contact', t=t, lang=lang)

@app.route('/bug')
def bug():
    lang=get_lang(); t=tdict(lang)
    return render_template('bug.html', title='Bug', t=t, lang=lang)

def seed():
    # Ensure tables exist and create sample data
    os.makedirs(DB_DIR, exist_ok=True)
    with conn(USERS_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT, role TEXT, cv TEXT)')
        # create default admin
        ex=c.execute('SELECT 1 FROM users WHERE email="admin@nextquest.ch"').fetchone()
        if not ex:
            c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',('Admin','admin@nextquest.ch',hash_pw("admin"),'admin'))
    with conn(OFFERS_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY, title TEXT, description TEXT, city TEXT, lat REAL, lng REAL, skills TEXT, org TEXT, schedule TEXT, salary TEXT, min_age INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY, offer_id INTEGER, student_id INTEGER, applied_at TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, offer_id INTEGER, author_name TEXT, rating INTEGER, comment TEXT)')
        if not c.execute('SELECT 1 FROM offers').fetchone():
            sample=[
                ('Assistant·e en vente','Aide en caisse et réassort. Horaires flexibles.','Lausanne',46.5197,6.6323,'Contact client, Caisse','Exemple Entreprise','Samedi','24 CHF/h',18),
                ('Aide déménagement','Port de cartons, montage meubles.','Renens',46.5367,6.5886,'Manutention','Exemple Particulier','Week-end','25 CHF/h',18),
                ('Serveur·se en café','Service les week-ends.','Morges',46.5113,6.4972,'Service','Exemple Entreprise','Week-end','23 CHF/h',18)
            ]
            for s in sample:
                c.execute('INSERT INTO offers(title,description,city,lat,lng,skills,org,schedule,salary,min_age) VALUES(?,?,?,?,?,?,?,?,?,?)', s)
    with conn(SERVICES_DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, title TEXT, description TEXT, city TEXT, lat REAL, lng REAL, skills TEXT, student_id INTEGER, student_name TEXT, cv TEXT, created_at TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, service_id INTEGER, author_name TEXT, rating INTEGER, comment TEXT)')
        if not c.execute('SELECT 1 FROM services').fetchone():
            c.execute('INSERT INTO services(title,description,city,lat,lng,skills,student_id,student_name,cv,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                      ('Cours de mathématiques','Cours niveau gymnase.','Lausanne',46.5197,6.6323,'Pédagogie,Maths',1,'Admin','—',datetime.now().isoformat()))

if __name__ == '__main__':
    seed()
    app.run(host='0.0.0.0', port=3200, debug=True)
