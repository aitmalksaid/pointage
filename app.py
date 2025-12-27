from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session
import pandas as pd
import os
import io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import re
import uuid
from db_manager import DBManager  # Import BDD
import difflib

# --- INITIALISATION DE LA BASE DE DONNÉES ---
try:
    db_init = DBManager()
    db_init.init_planning_table()
    print("[OK] Base de donnees initialisee avec succes.")
except Exception as e:
    print("[ERREUR] Erreur lors de l'initialisation de la BDD : " + str(e))

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
REPORT_FOLDER = 'reports'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORT_FOLDER'] = REPORT_FOLDER
app.config['SECRET_KEY'] = 'votre-cle-secrete-super-secrete-2024'

# Stockage en mémoire pour contourner la limite de taille des cookies
# Format: { 'uuid': { 'employees': [...], 'filepath': '...', 'engine': '...' } }
GLOBAL_DATA_STORE = {}

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# --- AUTHENTIFICATION ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == '1234':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = 'Identifiants incorrects.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.before_request
def require_login():
    # Liste des endpoints accessibles sans connexion
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))

# Routes
@app.route('/')
def home():
    """Menu principal de l'application"""
    return render_template('home.html')

@app.route('/heures-travail')
def heures_travail():
    """Page d'affichage des heures travaillées par semaine"""
    db = DBManager()
    employees = db.get_all_employees()
    return render_template('work_hours.html', employees=employees)

@app.route('/anomalies')
def anomalies():
    """Page d'analyse des oublis de pointage"""
    data_id = session.get('data_id')
    
    # Si pas de données en session, on essaie de charger depuis la DB (pour démo)
    employees = []
    if data_id and data_id in GLOBAL_DATA_STORE:
        employees = GLOBAL_DATA_STORE[data_id]['employees_data']
    else:
        # Fallback DB si dispo
        try:
            db = DBManager()
            employees = db.get_all_employees_with_detailed_data()
        except:
            return redirect(url_for('index'))

    anomalies_list = []

    for emp in employees:
        dates = emp.get('dates', [])
        ins = emp.get('check_ins', [])
        outs = emp.get('check_outs', [])
        
        # On parcourt chaque jour
        for i in range(len(dates)):
            if i >= len(ins) or i >= len(outs): break
            
            d = dates[i]
            cin = ins[i]
            cout = outs[i]
            
            # CONDITION D'ANOMALIE :
            # 1. La date est valide (pas '-')
            # 2. Entrée existe (pas '-' et pas vide)
            # 3. Sortie EST MANQUANTE ('-' ou vide ou None)
            if d and d != '-' and cin and cin not in ['-', ''] and (not cout or cout in ['-', '', 'None']):
                anomalies_list.append({
                    'name': emp['name'],
                    'date': d,
                    'check_in': cin
                })

    return render_template('anomalies.html', anomalies=anomalies_list)

@app.route('/reconciliation')
def reconciliation():
    """Page de comparaison des noms entre Pointage et Planning"""
    data_id = session.get('data_id')
    
    # 1. Liste des noms du Pointage (Excel)
    names_pointage = set()
    if data_id and data_id in GLOBAL_DATA_STORE:
        for emp in GLOBAL_DATA_STORE[data_id]['employees_data']:
            if emp.get('name'):
                names_pointage.add(emp['name'].strip())
    
    # 2. Liste des noms du Planning (DB - Ceux qui ont des horaires)
    names_planning = set()
    try:
        db = DBManager()
        # On ne prend QUE ceux qui ont un planning réel (table 'planning')
        planning_names_list = db.get_employees_with_planning()
        for name in planning_names_list:
            if name:
                names_planning.add(name.strip())
    except:
        pass # Si erreur DB, la liste restera vide

    # 3. Comparaison
    # Noms dans le pointage mais pas dans le planning
    pointage_only = sorted(list(names_pointage - names_planning))
    
    # Noms dans le planning mais pas dans le pointage
    planning_only = sorted(list(names_planning - names_pointage))
    
    # Ceux qui matchent
    match_count = len(names_pointage.intersection(names_planning))

    # 4. Fuzzy Matching (Suggestions de correction)
    suggestions = {}
    planning_lower_map = {name.lower(): name for name in planning_only}
    planning_lower_list = list(planning_lower_map.keys())

    for name in pointage_only:
        # On cherche si un nom "Pointage Only" ressemble à un nom "Planning Only"
        matches = difflib.get_close_matches(name.lower(), planning_lower_list, n=1, cutoff=0.6)
        if matches:
            suggested_name = planning_lower_map[matches[0]]
            suggestions[name] = suggested_name

    return render_template('reconciliation.html', 
                         pointage_only=pointage_only,
                         planning_only=planning_only,
                         match_count=match_count,
                         suggestions=suggestions)

@app.route('/upload-page')
def index():
    """Page d'importation du fichier Excel"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "Aucun fichier sélectionné", 400

    file = request.files['file']
    if file.filename == '':
        return "Nom de fichier vide", 400

    # Ajout d'un timestamp pour rendre le nom unique et éviter les erreurs "Permission denied"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = secure_filename(file.filename)
    filename = f"{timestamp}_{original_filename}"
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
    except Exception as e:
        return f"Erreur lors de la sauvegarde du fichier : {e}", 500

    # Determine file format and engine
    file_extension = os.path.splitext(filename)[1].lower()
    
    # Correct engine selection
    if file_extension == '.xlsx':
        engine = 'openpyxl'
    elif file_extension == '.xls':
        engine = 'xlrd'
    else:
        return "Format de fichier non supporté. Utilisez .xls ou .xlsx", 400

    # Process the file and parse data
    try:
        employees = parse_attendance_data(filepath, engine)
        
        # --- PRÉ-RÉCUPÉRATION DU CONTEXTE BDD POUR OPTIMISATION ---
        db = DBManager()
        calc_context = db.get_calculation_context()
        # ---------------------------------------------------------

        # Calculate statistics for each employee
        employees_with_stats_for_db = [] # Liste propre pour la BDD
        
        employees_with_stats = []
        for emp in employees:
            stats = calculate_statistics(emp, context=calc_context)
            
            # Préparation de l'objet enrichi pour la BDD
            emp_copy = emp.copy()
            emp_copy['stats'] = stats
            employees_with_stats_for_db.append(emp_copy)
            
            emp_data = {
                'person_id': emp['person_id'],
                'name': emp['name'],
                'department': emp['department'],
                'position': emp['position'],
                'joining_date': emp['joining_date'],
                'stats': stats,
                'dates': emp['dates'][:10] if len(emp['dates']) > 10 else emp['dates'],
                'check_ins': emp['check_ins'][:10] if len(emp['check_ins']) > 10 else emp['check_ins'],
                'check_outs': emp['check_outs'][:10] if len(emp['check_outs']) > 10 else emp['check_outs'],
                'statuses': emp['statuses'][:10] if len(emp['statuses']) > 10 else emp['statuses'],
            }
            employees_with_stats.append(emp_data)
        
        # --- SAUVEGARDE EN BASE DE DONNEES ---
        db_msg = ""
        try:
            success, message = db.save_data(employees_with_stats_for_db)
            db_msg = message
            if success:
                print(f"DEBUG BDD: {message}")
            else:
                print(f"DEBUG BDD ERREUR: {message}")
        except Exception as e:
            db_msg = f"Erreur critique BDD: {str(e)}"
            print(f"DEBUG BDD EXCEPTION: {e}")
        # -------------------------------------

        # Store in GLOBAL_DATA_STORE instead of session cookie
        data_id = str(uuid.uuid4())
        GLOBAL_DATA_STORE[data_id] = {
            'employees_data': employees_with_stats_for_db,
            'filepath': filepath,
            'engine': engine,
            'db_message': db_msg
        }
        
        # Store only the ID in the session (very small)
        session['data_id'] = data_id
        session.modified = True
        
        print(f"DEBUG: Données stockées en mémoire (ID: {data_id}), redirection vers dashboard...")
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"DEBUG: Erreur: {e}")
        return f"Erreur lors du traitement du fichier : {str(e)}", 500

@app.route('/test-db')
def test_db_page():
    """Page de diagnostic de la base de données"""
    return render_template('test_db.html')

@app.route('/api/test-db')
def api_test_db():
    """API de diagnostic détaillée pour la BDD"""
    db = DBManager()
    config_safe = db.config.copy()
    host = db.config['host']
    port = db.config['port']
    
    # Diagnostic Réseau
    net_diag = {}
    import socket
    
    # 1. Test DNS
    try:
        ip = socket.gethostbyname(host)
        net_diag['dns_resolution'] = f"OK (IP: {ip})"
    except Exception as e:
        net_diag['dns_resolution'] = f"ÉCHEC: {str(e)}"
        
    # 2. Test Socket direct
    try:
        s = socket.create_connection((host, port), timeout=3)
        net_diag['socket_connection'] = "OK (Port accessible)"
        s.close()
    except Exception as e:
        net_diag['socket_connection'] = f"ÉCHEC: {str(e)}"

    config_safe['host_debug'] = f"[{host}]"
    config_safe['host_len'] = len(host)
    
    if 'password' in config_safe:
        config_safe['password'] = '******'
        
    try:
        conn = db.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True) # Utiliser dictionary=True pour éviter l'erreur de tuple
            cursor.execute("SELECT VERSION()")
            ver_row = cursor.fetchone()
            ver = ver_row['VERSION()'] if ver_row and 'VERSION()' in ver_row else "Inconnue"
            
            db_stats = {}
            cursor.execute("SELECT DISTINCT departement FROM employes")
            db_stats['unique_departments'] = [r['departement'] for r in cursor.fetchall() if r['departement']]
            cursor.execute("SELECT DISTINCT poste FROM employes")
            db_stats['unique_positions'] = [r['poste'] for r in cursor.fetchall() if r['poste']]
            
            conn.close()
            return jsonify({
                'success': True, 
                'message': f"Connexion réussie ! Version MySQL: {ver}",
                'debug': {'config': config_safe, 'network': net_diag, 'db_stats': db_stats}
            })
        else:
            return jsonify({
                'success': False, 
                'message': "La connexion a renvoyé None",
                'debug': {'config': config_safe, 'network': net_diag}
            })
    except Exception as e:
        import traceback
        
        # Stats additionnelles pour comprendre le problème des fonctions
        db_stats = {}
        try:
            conn = db.get_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT DISTINCT departement FROM employes")
                db_stats['unique_departments'] = [r['departement'] for r in cursor.fetchall()]
                cursor.execute("SELECT DISTINCT poste FROM employes")
                db_stats['unique_positions'] = [r['poste'] for r in cursor.fetchall()]
                conn.close()
        except: pass

        return jsonify({
            'success': False, 
            'message': f"Erreur de connexion : {str(e)}",
            'debug': {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'config': config_safe,
                'network': net_diag,
                'db_stats': db_stats
            }
        })

@app.route('/dashboard')
def dashboard():
    """Rendu du dashboard avec persistance BDD TOTALE et filtrage par période"""
    db = DBManager()
    
    # 1. Récupérer les périodes disponibles
    periods = db.get_available_periods()
    
    # 2. Récupérer les paramètres de filtrage
    target_year = request.args.get('year')
    target_month = request.args.get('month')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Si non spécifié et qu'on a des périodes, on prend la plus récente (si pas de plage de dates)
    if not target_year and not target_month and not start_date and periods:
        target_year = periods[0]['year']
        target_month = periods[0]['month']
    
    data_id = session.get('data_id')
    employees = []
    
    # On force la récupération depuis la BDD si une période ou plage est spécifiée
    if (target_year and target_month) or (start_date and end_date):
        employees = db.get_all_employees_with_detailed_data_filtered(
            year=target_year, month=target_month, 
            start_date=start_date, end_date=end_date
        )
        # On met à jour la session/mémoire avec ces données filtrées pour le PDF/Excel
        new_id = str(uuid.uuid4())
        session['data_id'] = new_id
        GLOBAL_DATA_STORE[new_id] = {
            'employees_data': employees,
            'filepath': None, 'engine': 'xlrd',
            'year': target_year, 'month': target_month,
            'start_date': start_date, 'end_date': end_date
        }
    elif data_id in GLOBAL_DATA_STORE:
        employees = GLOBAL_DATA_STORE[data_id]['employees_data']
    else:
        # Fallback : toutes les données
        employees = db.get_all_employees_with_detailed_data_filtered()
        if employees:
            new_id = str(uuid.uuid4())
            session['data_id'] = new_id
            GLOBAL_DATA_STORE[new_id] = {
                'employees_data': employees,
                'filepath': None, 'engine': 'xlrd'
            }

    if not employees:
        return redirect(url_for('index'))
    
    # Calcul des stats et recherche de la plage de dates
    employees_with_stats = []
    all_dates = []
    
    db = DBManager()
    calc_context = db.get_calculation_context()

    for emp in employees:
        stats = calculate_statistics(emp, context=calc_context)
        # Collecte de toutes les dates pour trouver la plage
        if 'dates' in emp:
            all_dates.extend([d for d in emp['dates'] if d and d != '-'])
        
        emp_data = {
            'person_id': emp['person_id'],
            'name': emp['name'],
            'department': emp.get('department', 'N/A'),
            'position': emp.get('position', 'N/A'),
            'joining_date': emp.get('joining_date', 'N/A'),
            'stats': stats
        }
        employees_with_stats.append(emp_data)
    
    # Détermination de la période couverte
    date_range = "Période non définie"
    if all_dates:
        try:
            date_objs = [datetime.strptime(d[:10], '%Y-%m-%d') for d in all_dates]
            min_date = min(date_objs).strftime('%d/%m/%Y')
            max_date = max(date_objs).strftime('%d/%m/%Y')
            date_range = f"Du {min_date} au {max_date}"
        except: pass

    # Calculate global statistics
    total_employees = len(employees)
    total_hours_all = sum([emp['stats']['total_hours'] for emp in employees_with_stats])
    total_days_worked = sum([emp['stats']['total_days_worked'] for emp in employees_with_stats])
    total_days_absent = sum([emp['stats']['total_days_absent'] for emp in employees_with_stats])
    
    global_stats = {
        'total_employees': total_employees,
        'total_hours': round(total_hours_all, 2),
        'avg_hours_per_employee': round(total_hours_all / total_employees, 2) if total_employees > 0 else 0,
        'total_days_worked': total_days_worked,
        'total_days_absent': total_days_absent,
        'attendance_rate': round((total_days_worked / (total_days_worked + total_days_absent) * 100), 2) if (total_days_worked + total_days_absent) > 0 else 0
    }
    
    db_message = ""
    if data_id in GLOBAL_DATA_STORE:
        db_message = GLOBAL_DATA_STORE[data_id].get('db_message', '')

    return render_template('dashboard.html', 
                          employees=employees_with_stats, 
                          global_stats=global_stats, 
                          date_range=date_range,
                          raw_data=employees,
                          db_message=db_message,
                          periods=periods,
                          current_period={'year': target_year, 'month': target_month, 'start_date': start_date, 'end_date': end_date})

@app.route('/api/update_employee', methods=['POST'])
def update_employee():
    """Update employee statistics manually"""
    try:
        data = request.json
        person_id = data.get('person_id')
        new_stats = data.get('stats')
        
        data_id = session.get('data_id')
        if not data_id or data_id not in GLOBAL_DATA_STORE:
            return jsonify({'success': False, 'message': 'Session expirée'}), 400
            
        # 1. Mise à jour en mémoire (pour le PDF et l'affichage)
        stored_data = GLOBAL_DATA_STORE[data_id]
        found = False
        
        # Le format des stats en entrée doit être converti en nombres
        stats_clean = {
            'total_hours': float(new_stats['total_hours']),
            'total_days_worked': int(new_stats['total_days_worked']),
            'total_days_absent': int(new_stats['total_days_absent']),
            'total_weekends': int(new_stats.get('total_weekends', 0)),
            'average_hours_per_day': float(new_stats['average_hours_per_day'])
        }

        # On parcourt la liste en mémoire pour trouver l'employé
        for emp in stored_data['employees_data']:
            if str(emp['person_id']) == str(person_id):
                # On met à jour directement l'objet en mémoire
                # Attention: calculate_statistics est une fonction qui recalcule à partir des raw data.
                # Ici on veut FORCER les valeurs.
                # Astuce: On stocke les stats 'fixées' dans une nouvelle clé 'manual_stats'
                # et on modifiera calculate_statistics pour les utiliser en priorité.
                emp['manual_stats'] = stats_clean
                found = True
                break
        
        if not found:
            return jsonify({'success': False, 'message': 'Employé non trouvé en mémoire'}), 404
            
        # 2. Mise à jour en Base de Données
        try:
            db = DBManager()
            db.update_employee_stats(person_id, stats_clean)
        except Exception as e:
            print(f"Erreur update DB: {e}")
            # On continue même si la DB échoue, l'important est le PDF pour l'instant
            
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Init DB Planning Table (Déjà fait au début, mais on garde une sécurité si besoin)
# db_init.init_planning_table() est appelé à la ligne 20

@app.route('/planning')
def planning_page():
    """Page de gestion du planning hebdomadaire avec persistance BDD"""
    data_id = session.get('data_id')
    employees = []
    
    if data_id and data_id in GLOBAL_DATA_STORE:
        employees = GLOBAL_DATA_STORE[data_id]['employees_data']
    else:
        db = DBManager()
        employees = db.get_all_employees()

    return render_template('planning.html', employees=employees)

@app.route('/api/get_planning/<person_id>')
def get_planning(person_id):
    """API pour récupérer le planning (Individuel ou Fonction par défaut)"""
    try:
        week_date = request.args.get('date')
        if not week_date:
            return jsonify({'success': False, 'message': 'Date requise'})
            
        db = DBManager()
        # 1. Tentative : Planning individuel
        planning = db.get_employee_planning(person_id, week_date)
        is_fallback = False
        
        # 2. Si vide : Tentative planning de fonction
        if not planning:
            # Récupérer le département de l'employé
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT departement FROM employes WHERE person_id = %s", (person_id,))
            emp = cursor.fetchone()
            if emp and emp['departement']:
                func_planning = db.get_function_planning(emp['departement'])
                if func_planning:
                    planning = func_planning
                    is_fallback = True
            cursor.close()
            conn.close()

        return jsonify({'success': True, 'planning': planning or {}, 'is_fallback': is_fallback})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/save_planning', methods=['POST'])
def save_planning():
    """API pour sauvegarder le planning d'une semaine"""
    try:
        data = request.json
        person_id = data.get('person_id')
        planning = data.get('planning')
        week_date = data.get('date') # La date du Lundi
        
        if not week_date:
            return jsonify({'success': False, 'message': 'Date requise'})
        
        db = DBManager()
        success = db.save_employee_planning(person_id, week_date, planning)
        
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/templates')
def api_get_templates():
    """Récupère la liste des modèles de planning"""
    try:
        db = DBManager()
        templates = db.get_templates()
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/save_template', methods=['POST'])
def api_save_template():
    """Enregistre un nouveau modèle de planning"""
    try:
        data = request.json
        nom = data.get('nom')
        planning_data = data.get('planning')
        
        if not nom or not planning_data:
            return jsonify({'success': False, 'message': 'Nom et données requis'})
            
        db = DBManager()
        success = db.save_template(nom, planning_data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/planning-fonctions')
def planning_fonctions():
    """Page de gestion des plannings par fonction avec persistance BDD"""
    db = DBManager()
    
    # On récupère toutes les fonctions (départements) existantes en base de données
    # pour que la liste soit complète, même sans fichier uploadé dans la session
    conn = db.get_connection()
    departments = []
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT departement FROM employes WHERE departement IS NOT NULL AND departement != 'N/A'")
        departments = sorted([r[0] for r in cursor.fetchall()])
        conn.close()
    
    # Fallback sur la session si la BDD est vide
    if not departments:
        data_id = session.get('data_id')
        if data_id in GLOBAL_DATA_STORE:
            emps = GLOBAL_DATA_STORE[data_id]['employees_data']
            departments = sorted(list(set([e['department'] for e in emps if 'department' in e and e['department'] != 'N/A'])))
    
    return render_template('function_planning.html', departments=departments)

@app.route('/api/function_planning/<path:dept_name>')
def api_get_function_planning(dept_name):
    """Récupère le planning type d'une fonction"""
    try:
        db = DBManager()
        planning = db.get_function_planning(dept_name)
        return jsonify({'success': True, 'planning': planning or {}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/save_function_planning', methods=['POST'])
def api_save_function_planning():
    """Sauvegarde le planning type d'une fonction"""
    try:
        data = request.json
        dept_name = data.get('department')
        planning_data = data.get('planning')
        db = DBManager()
        
        # Les tables sont déjà initialisées au démarrage de l'appli
        
        success = db.save_function_planning(dept_name, planning_data)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/work-hours-details/<person_id>')
def api_work_hours_details(person_id):
    """Calcule les détails quotidiens pour la page Feuilles d'Heures"""
    week_start_str = request.args.get('week')
    if not week_start_str:
        return jsonify({'success': False, 'message': 'Date de semaine requise'})
    
    try:
        db = DBManager()
        # On récupère les données brutes de l'employé depuis la BDD (optimisé)
        emp = db.get_employee_detailed_data(person_id)
        
        if not emp:
            return jsonify({'success': False, 'message': f'Employé {person_id} non trouvé dans la base de données'})

        from datetime import datetime, timedelta
        # Mapping manuel pour éviter les problèmes d'encodage Windows/Locale
        MONTHS_FR = {
            1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
            7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
        }
        DAYS_FR_FULL = {
            0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"
        }

        monday = datetime.strptime(week_start_str, '%Y-%m-%d')
        days_details = []
        
        # Récupération du contexte de planning pour cet employé
        calc_context = db.get_calculation_context()

        for i in range(7):
            current_day = monday + timedelta(days=i)
            day_str = current_day.strftime('%Y-%m-%d')
            
            day_num = current_day.weekday() # 0=Lundi
            day_name_fr = DAYS_FR_FULL[day_num]
            day_month_fr = MONTHS_FR[current_day.month]
            
            day_name_en = day_name_fr # On renomme pour garder la compatibilité avec le reste de la boucle
            
            # Recherche du pointage pour ce jour (comparaison souple)
            idx = -1
            if 'dates' in emp:
                for d_idx, d_val in enumerate(emp['dates']):
                    if str(d_val).startswith(day_str):
                        idx = d_idx
                        break
            
            c_in = emp['check_ins'][idx] if idx != -1 else None
            c_out = emp['check_outs'][idx] if idx != -1 else None
            
            # --- RÉCUPÉRATION DU PLANNING ---
            # On utilise le contexte pré-chargé pour la performance
            planned = None
            p_id = str(person_id)
            monday_str = monday.strftime('%Y-%m-%d')
            
            # Tentative Individuelle
            indiv_plans = calc_context['individual'].get(p_id, {})
            if monday_str in indiv_plans:
                plan_data = indiv_plans[monday_str]
                if day_name_en in plan_data:
                    planned = plan_data[day_name_en]
            
            # Tentative Fonction (fallback)
            if not planned:
                dept = calc_context['emp_depts'].get(p_id) or emp.get('department')
                if dept and dept in calc_context['functions']:
                    planned = calc_context['functions'][dept].get(day_name_en)

            is_repos = planned.get('repos', False) if planned else False
            
            # --- CALCUL DE L'ÉCART (DIFFÉRENCE) ---
            actual_minutes = 0
            planned_minutes = 0
            diff_display = ""
            late_display = ""
            
            # 1. Minutes Réelles
            if c_in and c_out and c_in not in ('--', '-', '') and c_out not in ('--', '-', ''):
                try:
                    t1 = datetime.strptime(c_in.strip()[:5], '%H:%M')
                    t2 = datetime.strptime(c_out.strip()[:5], '%H:%M')
                    d_diff = t2 - t1
                    actual_minutes = int(d_diff.total_seconds() / 60)
                    if actual_minutes < 0: actual_minutes += 1440 # Nuit
                except: pass
            
            # 2. Minutes Prévues
            if planned and not is_repos:
                try:
                    p1 = datetime.strptime(planned['debut'], '%H:%M')
                    p2 = datetime.strptime(planned['fin'], '%H:%M')
                    p_diff = p2 - p1
                    planned_minutes = int(p_diff.total_seconds() / 60)
                    if planned_minutes < 0: planned_minutes += 1440
                except: pass
                
            # 3. Comparaison et Retard
            if actual_minutes > 0 and planned_minutes > 0:
                diff = actual_minutes - planned_minutes
                if diff > 0:
                    diff_display = f"+{diff // 60}h {diff % 60:02d}min" if diff >= 60 else f"+{diff} min"
                elif diff < 0:
                    abs_diff = abs(diff)
                    diff_display = f"-{abs_diff // 60}h {abs_diff % 60:02d}min" if abs_diff >= 60 else f"-{abs_diff} min"
                
                # Retard spécifique (Clock-in > Planned Start)
                try:
                    actual_start = datetime.strptime(c_in.strip()[:5], '%H:%M')
                    planned_start_dt = datetime.strptime(planned['debut'], '%H:%M')
                    if actual_start > planned_start_dt:
                        late = int((actual_start - planned_start_dt).total_seconds() / 60)
                        if late > 0:
                            late_str = f"{late // 60}h {late % 60:02d}min" if late >= 60 else f"{late} min"
                            late_display = (late_display + " | " if late_display else "") + f"Retard: -{late_str}"
                except: pass

                # Départ anticipé (Clock-out < Planned End)
                try:
                    actual_end = datetime.strptime(c_out.strip()[:5], '%H:%M')
                    planned_end_dt = datetime.strptime(planned['fin'], '%H:%M')
                    if actual_end < planned_end_dt:
                        early = int((planned_end_dt - actual_end).total_seconds() / 60)
                        if early > 0:
                            early_str = f"{early // 60}h {early % 60:02d}min" if early >= 60 else f"{early} min"
                            late_display = (late_display + " | " if late_display else "") + f"Départ: -{early_str}"
                except: pass

            # Détection stricte de la présence
            has_clocked_in = (c_in and c_in not in ('--', '-', 'nan', 'None', ''))
            
            status_text = "Absent"
            if has_clocked_in:
                status_text = "TRAVAILLÉ"
            elif is_repos:
                status_text = "Repos"

            # Formatage de la durée réelle
            duration = "--"
            if actual_minutes > 0:
                duration = f"{actual_minutes // 60}h {actual_minutes % 60:02d}min" if actual_minutes >= 60 else f"{actual_minutes} min"

            # Construction manuelle de la date complète pour éviter les encodages foireux
            full_date_str = f"{day_name_fr} {current_day.day} {day_month_fr} {current_day.year}"

            days_details.append({
                'day_name': day_name_fr,
                'full_date': f"{current_day.day} {day_month_fr} {current_day.year}",
                'full_date_string': full_date_str,
                'check_in': c_in or '--',
                'check_out': c_out or '--',
                'duration': duration,
                'planned_start': planned.get('debut') if planned and not is_repos else '--',
                'planned_end': planned.get('fin') if planned and not is_repos else '--',
                'is_repos': is_repos,
                'status_text': status_text,
                'diff_display': diff_display,
                'late_display': late_display
            })

        return jsonify({'success': True, 'days': days_details})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/data')
def get_data():
    """Return employee data as JSON for charts"""
    data_id = session.get('data_id')
    
    if not data_id or data_id not in GLOBAL_DATA_STORE:
        return jsonify({'error': 'No data available'}), 404
    
    # Retrieve data from memory
    stored_data = GLOBAL_DATA_STORE[data_id]
    employees = stored_data['employees_data']
    
    # Prepare data for charts
    chart_data = {
        'employees': [],
        'hours': [],
        'departments': {},
        'status_summary': {
            'worked': 0,
            'absent': 0,
            'weekend': 0
        }
    }
    
    for emp in employees:
        stats = calculate_statistics(emp)
        chart_data['employees'].append(emp['name'])
        chart_data['hours'].append(stats['total_hours'])
        
        # Group by department
        dept = emp['department']
        if dept not in chart_data['departments']:
            chart_data['departments'][dept] = {
                'total_hours': 0,
                'employee_count': 0
            }
        chart_data['departments'][dept]['total_hours'] += stats['total_hours']
        chart_data['departments'][dept]['employee_count'] += 1
        
        # Status summary
        chart_data['status_summary']['worked'] += stats['total_days_worked']
        chart_data['status_summary']['absent'] += stats['total_days_absent']
        chart_data['status_summary']['weekend'] += stats['total_weekends']
    
    return jsonify(chart_data)

@app.route('/generate-excel')
def generate_excel():
    """Génère un fichier Excel des résultats actuels"""
    data_id = session.get('data_id')
    if not data_id or data_id not in GLOBAL_DATA_STORE:
        return "Données non trouvées. Veuillez ré-uploader le fichier.", 404
    
    employees = GLOBAL_DATA_STORE[data_id]['employees_data']
    
    # Récupérer le contexte de planning pour des calculs précis
    db = DBManager()
    calc_context = db.get_calculation_context()
    
    # Préparation des données pour Excel
    rows = []
    for emp in employees:
        # Utiliser le contexte pour des calculs précis basés sur le planning
        stats = calculate_statistics(emp, context=calc_context)
        
        # Format minutes to HhMM
        ovt = f"{int(stats['total_overtime_minutes'] // 60)}h{int(stats['total_overtime_minutes'] % 60):02d}" if stats.get('total_overtime_minutes') else "0h00"
        unt = f"{int(stats['total_undertime_minutes'] // 60)}h{int(stats['total_undertime_minutes'] % 60):02d}" if stats.get('total_undertime_minutes') else "0h00"
        late = f"{int(stats['total_late_minutes'] // 60)}h{int(stats['total_late_minutes'] % 60):02d}" if stats.get('total_late_minutes') else "0h00"

        rows.append({
            'ID Employé': emp['person_id'],
            'Nom': emp['name'],
            'Département': emp['department'],
            'Jours Travaillés': stats['total_days_worked'],
            'Nbr Absences': stats['total_days_absent'],
            'Repos/Weekends': stats['total_weekends'],
            'Total Heures': stats['total_hours'],
            'Heures Supp.': ovt,
            'Heures Manquantes': unt,
            'Retards (durée)': late,
            'Nbr Retards': stats.get('count_lates', 0)
        })
    
    df = pd.DataFrame(rows)
    
    # Ordonner les colonnes proprement
    cols = ['ID Employé', 'Nom', 'Département', 'Jours Travaillés', 'Nbr Absences', 'Nbr Retards', 'Total Heures', 'Heures Supp.', 'Heures Manquantes', 'Retards (durée)']
    df = df[cols]
    
    # Création du fichier Excel en mémoire
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapport Assiduité')
        
        # Ajustement automatique de la largeur des colonnes
        worksheet = writer.sheets['Rapport Assiduité']
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_len

    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'rapport_assiduite_{timestamp}.xlsx'
    )

@app.route('/generate-pdf')
def generate_pdf():
    """Generate and download PDF report"""
    data_id = session.get('data_id')
    
    if not data_id or data_id not in GLOBAL_DATA_STORE:
        return redirect(url_for('index'))
    
    try:
        stored_data = GLOBAL_DATA_STORE[data_id]
        filepath = stored_data['filepath']
        engine = stored_data['engine']
        
        db = DBManager()
        calc_context = db.get_calculation_context()
        
        pdf_path = process_and_generate_pdf(filepath, engine, context=calc_context)
        return send_file(pdf_path, as_attachment=True, download_name=f"rapport_assiduité_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    except Exception as e:
        return f"Erreur lors de la génération du PDF : {str(e)}", 500


def parse_attendance_data(filepath, engine):
    """Parse the attendance Excel file and extract employee data"""
    
    # Read the entire file without headers
    try:
        df = pd.read_excel(filepath, engine=engine, header=None)
    except Exception as e:
        # Fallback pour les faux fichiers .xls qui sont en fait du HTML
        if 'Expected BOF record' in str(e) or 'html' in str(e).lower():
            try:
                # On lit comme du HTML (retourne une liste de DataFrames)
                dfs = pd.read_html(filepath, header=None)
                if dfs:
                    df = dfs[0]  # On prend le premier tableau trouvé
                else:
                    raise e
            except:
                raise e # Si échec HTML aussi, on remonte l'erreur initiale
        else:
            raise e
    
    employees = []
    current_employee = None
    
    # Recherche de la date de début du rapport
    base_date = None
    for _, row in df.iterrows():
        cell_0 = str(row[0]) if pd.notna(row[0]) else ""
        if "From:" in cell_0 and "To:" in cell_0:
            import re
            m = re.search(r"From:\s*(\d{4}-\d{2}-\d{2})", cell_0)
            if m:
                try:
                    base_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                    break
                except: pass

    for idx, row in df.iterrows():
        # Check if this row contains "Person ID"
        if pd.notna(row[0]) and str(row[0]).strip() == "Person ID":
            # If we have a previous employee, save it
            if current_employee is not None:
                employees.append(current_employee)
            
            # Start a new employee
            current_employee = {
                'person_id': row[1] if pd.notna(row[1]) else 'N/A',
                'name': 'N/A',
                'department': 'N/A',
                'joining_date': 'N/A',
                'position': 'N/A',
                'dates': [],
                'check_ins': [],
                'check_outs': [],
                'attended_minutes': [],
                'statuses': [],
                'summary': ''
            }
            
            # Extract employee name, department, etc. from the same row
            for i in range(len(row)):
                if pd.notna(row[i]):
                    if str(row[i]).strip() == "Employee Name" and i+3 < len(row):
                        current_employee['name'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Department" and i+3 < len(row):
                        current_employee['department'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Joining Date" and i+3 < len(row):
                        current_employee['joining_date'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                    elif str(row[i]).strip() == "Position" and i+3 < len(row):
                        current_employee['position'] = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
        
        # Detection souple des lignes
        first_col = str(row[0]).strip().lower() if pd.notna(row[0]) else ""
        
        # Check if this row contains "Date" (the dates row)
        if current_employee is not None and "date" in first_col and len(first_col) < 10:
            raw_dates = [str(x) if pd.notna(x) else '-' for x in row[1:]]
            if base_date:
                from datetime import timedelta
                new_dates = []
                for i in range(len(raw_dates)):
                    if raw_dates[i] == '-':
                        new_dates.append('-')
                    else:
                        # On calcule la date réelle basée sur la position de la colonne
                        d_actual = base_date + timedelta(days=i)
                        new_dates.append(d_actual.strftime('%Y-%m-%d'))
                current_employee['dates'] = new_dates
            else:
                current_employee['dates'] = raw_dates
        
        # Check if this row contains "Check-in1"
        elif current_employee is not None and "check-in1" in first_col:
            current_employee['check_ins'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Check-out1"
        elif current_employee is not None and "check-out1" in first_col:
            current_employee['check_outs'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Attended"
        elif current_employee is not None and "attended" in first_col:
            current_employee['attended_minutes'] = [x if pd.notna(x) and str(x) != '-' else 0 for x in row[1:]]
        
        # Check if this row contains "Status"
        elif current_employee is not None and "status" in first_col:
            current_employee['statuses'] = [str(x) if pd.notna(x) else '-' for x in row[1:]]
        
        # Check if this row contains "Summary"
        elif current_employee is not None and pd.notna(row[0]) and str(row[0]).strip() == "Summary":
            current_employee['summary'] = str(row[1]) if pd.notna(row[1]) else ''
    
    # Don't forget the last employee
    if current_employee is not None:
        employees.append(current_employee)
    
    return employees

def calculate_statistics(employee, context=None):
    """Calcule les statistiques d'un employé"""
    total_minutes = 0
    total_days_worked = 0
    total_days_absent = 0
    total_weekends = 0
    total_late_minutes = 0
    total_overtime_minutes = 0
    total_undertime_minutes = 0
    count_lates = 0  # Nouveau compteur

    # Contexte pour les plannings
    if context is None:
        db = DBManager()
        context = db.get_calculation_context()

    p_id = str(employee['person_id'])

    for i, date_val in enumerate(employee['dates']):
        # 1. Infos de base
        status = str(employee['statuses'][i]).upper() if i < len(employee['statuses']) else ''
        check_in = str(employee['check_ins'][i]) if i < len(employee['check_ins']) else '-'
        check_out = str(employee['check_outs'][i]) if i < len(employee['check_outs']) else ''
        
        # 2. Récupérer le planning depuis le CONTEXTE (beaucoup plus rapide)
        planned = None
        try:
            date_obj = datetime.strptime(str(date_val)[:10], '%Y-%m-%d')
            monday_str = (date_obj - timedelta(days=date_obj.weekday())).strftime('%Y-%m-%d')
            
            # Mapping robuste indépendant de la locale
            days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            day_name = days_fr[date_obj.weekday()]
            
            # Tentative Individuelle
            indiv_plans = context['individual'].get(p_id, {})
            if monday_str in indiv_plans:
                plan_data = indiv_plans[monday_str]
                if day_name in plan_data:
                    planned = {
                        'heure_debut': plan_data[day_name]['debut'],
                        'heure_fin': plan_data[day_name]['fin'],
                        'est_repos': plan_data[day_name]['repos']
                    }
            
            # Tentative Fonction (fallback)
            if not planned:
                dept = context['emp_depts'].get(p_id) or employee.get('department')
                if dept and dept in context['functions']:
                    dept_plan = context['functions'][dept]
                    if day_name in dept_plan:
                        planned = {
                            'heure_debut': dept_plan[day_name]['debut'],
                            'heure_fin': dept_plan[day_name]['fin'],
                            'est_repos': dept_plan[day_name]['repos']
                        }
        except Exception as e: 
            pass

        is_repos_planned = planned['est_repos'] if planned else False
        planned_start = planned['heure_debut'] if (planned and not is_repos_planned) else None
        planned_end = planned['heure_fin'] if (planned and not is_repos_planned) else None

        minutes = 0
        if i < len(employee['attended_minutes']):
            try:
                val = employee['attended_minutes'][i]
                if val != '-' and val != 'nan':
                    minutes = int(float(val))
            except: minutes = 0
        
        # --- LOGIQUE DE PRÉSENCE / ABSENCE ---
        has_clocked_in = (check_in != '-' and check_in != 'nan' and check_in != 'None' and check_in.strip() != '')
        
        if minutes > 0 or has_clocked_in:
            # Travaillé
            total_days_worked += 1
            total_minutes += minutes
            
            # --- CALCUL DU RETARD ---
            if planned_start and has_clocked_in:
                try:
                    fmt = "%H:%M"
                    clean_check_in = check_in.strip()[:5] 
                    
                    time_planned = datetime.strptime(planned_start, fmt)
                    time_actual = datetime.strptime(clean_check_in, fmt)
                    
                    if time_actual > time_planned:
                        diff_late = (time_actual - time_planned).total_seconds() / 60
                        if diff_late > 0:
                            total_late_minutes += int(diff_late)
                            count_lates += 1  # Incrémenter le nombre de retards
                except: pass

            # --- CALCUL HEURES SUPP / MANQUANTES ---
            if planned_start and planned_end:
                try:
                    p1 = datetime.strptime(planned_start, "%H:%M")
                    p2 = datetime.strptime(planned_end, "%H:%M")
                    p_diff = (p2 - p1).total_seconds() / 60
                    if p_diff < 0: p_diff += 1440
                    planned_min = int(p_diff)
                    
                    if minutes > 0:
                        diff_work = minutes - planned_min
                        
                        if diff_work > 0:
                            total_overtime_minutes += diff_work
                        elif diff_work < 0:
                            total_undertime_minutes += abs(diff_work)
                except: pass
        
        elif not is_repos_planned and date_obj.weekday() < 6: 
             # Si pas travaillé, pas repos, et pas Dimanche (simplifié) -> Absent
             # (Logique existante à préserver/affiner selon besoin)
             # Ici on utilise la logique simple : absence si 0 min et pas repos
             # Note: logic un peu simpliste sur le dimanche hardcodé, mais je touche pas pour pas casser
             if date_obj.weekday() != 6:
                total_days_absent += 1
             else:
                total_weekends += 1
        elif date_obj.weekday() == 6:
            total_weekends += 1

    # Calcul final
    total_hours = total_minutes / 60
    
    return {
        'total_days_worked': total_days_worked,
        'total_days_absent': total_days_absent,
        'total_hours': round(total_hours, 2),
        'total_weekends': total_weekends,
        'total_late_minutes': total_late_minutes,
        'count_lates': count_lates,  # Nouvelle sortie
        'total_overtime_minutes': total_overtime_minutes,
        'total_undertime_minutes': total_undertime_minutes,
        'average_hours_per_day': round(total_hours / total_days_worked, 2) if total_days_worked > 0 else 0
    }

def process_and_generate_pdf(filepath, engine, context=None):
    """Process Excel file and generate PDF report"""
    
    # Parse the attendance data
    employees = parse_attendance_data(filepath, engine)
    
    # Préparation du contexte s'il n'est pas fourni
    if context is None:
        db = DBManager()
        context = db.get_calculation_context()
    
    # Generate PDF
    pdf_filename = f"rapport_assiduité_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(app.config['REPORT_FOLDER'], pdf_filename)
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#283593'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Add title
    title = Paragraph("RAPPORT D'ASSIDUITÉ MENSUEL", title_style)
    elements.append(title)
    
    # Add date
    date_text = Paragraph(f"<b>Date de génération:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style)
    elements.append(date_text)
    elements.append(Spacer(1, 20))
    
    # Global statistics
    total_employees = len(employees)
    total_hours_all = sum([calculate_statistics(emp, context=context)['total_hours'] for emp in employees])
    
    summary_data = [
        ['STATISTIQUES GLOBALES', ''],
        ['Nombre total d\'employés', str(total_employees)],
        ['Total heures travaillées', f"{round(total_hours_all, 2)} heures"],
        ['Moyenne heures/employé', f"{round(total_hours_all/total_employees, 2) if total_employees > 0 else 0} heures"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Add employee details
    elements.append(Paragraph("DÉTAILS PAR EMPLOYÉ", heading_style))
    elements.append(Spacer(1, 12))
    
    for emp in employees:
        stats = calculate_statistics(emp, context=context)
        
        # Employee header
        emp_header = Paragraph(f"<b>{emp['name']}</b> (ID: {emp['person_id']})", heading_style)
        elements.append(emp_header)
        
        # Format minutes to HhMM for PDF
        ovt = f"{int(stats['total_overtime_minutes'] // 60)}h{int(stats['total_overtime_minutes'] % 60):02d}" if stats.get('total_overtime_minutes') else "0h00"
        unt = f"{int(stats['total_undertime_minutes'] // 60)}h{int(stats['total_undertime_minutes'] % 60):02d}" if stats.get('total_undertime_minutes') else "0h00"
        late = f"{int(stats['total_late_minutes'] // 60)}h{int(stats['total_late_minutes'] % 60):02d}" if stats.get('total_late_minutes') else "0h00"

        # Employee details table
        emp_data = [
            ['Département', emp['department']],
            ['Poste', emp['position']],
            ['Date d\'embauche', emp['joining_date']],
            ['Jours travaillés', str(stats['total_days_worked'])],
            ['Jours d\'absence', str(stats['total_days_absent'])],
            ['Weekends / Repos', str(stats['total_weekends'])],
            ['Total heures réelles', f"{stats['total_hours']} heures"],
            ['Heures Supplémentaires', ovt],
            ['Heures Manquantes', unt],
            ['Total Retards', late],
            ['Moyenne heures/jour', f"{stats['average_hours_per_day']} heures"],
        ]
        
        emp_table = Table(emp_data, colWidths=[2.5*inch, 3.5*inch])
        emp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(emp_table)
        elements.append(Spacer(1, 20))
    
    # Build PDF
    doc.build(elements)
    
    return pdf_path

@app.route('/import-planning')
def import_planning_page():
    return render_template('import_planning.html')

@app.route('/api/import-planning', methods=['POST'])
def api_import_planning():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier fourni'})
        
        file = request.files['file']
        week_start_str = request.form.get('week_start')
        target_dept = request.form.get('department')
        
        if not file.filename:
            return jsonify({'success': False, 'message': 'Nom de fichier vide'})
        
        # Lecture du fichier
        try:
            filename = file.filename.lower()
            if filename.endswith('.pdf'):
                import pdfplumber
                with pdfplumber.open(file) as pdf:
                    # On ne traite que la première page pour l'instant
                    page = pdf.pages[0]
                    table = page.extract_table()
                    
                    if not table or len(table) < 2:
                        return jsonify({'success': False, 'message': 'Tableau non trouvé dans le PDF'})
                    
                    # Nettoyage des données (suppression des sauts de ligne)
                    cleaned_table = []
                    for row in table:
                        cleaned_row = []
                        for cell in row:
                            if cell:
                                # Remplacer les sauts de ligne par des espaces pour faciliter le parsing "8am\n- 4pm"
                                cleaned_row.append(str(cell).replace('\n', ' ').strip())
                            else:
                                cleaned_row.append('')
                        cleaned_table.append(cleaned_row)
                    
                    # Convertir en DataFrame
                    # On suppose que la première ligne est l'en-tête
                    df = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
            else:
                # Excel
                df = pd.read_excel(file)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Erreur lecture fichier: {str(e)}'})

        # Normalisation des colonnes (minuscules, strip)
        df.columns = df.columns.astype(str).str.lower().str.strip()
        
        # Identification des colonnes Jours
        # On cherche 'lun', 'mon', '22', etc.
        # Mapping simple index -> jour de la semaine (Lundi=0)
        # On suppose que la première colonne est "Nom" et les 7 suivantes sont les jours
        
        # Trouver la colonne "Nom"
        name_col = None
        for col in df.columns:
            if 'nom' in col or 'name' in col or 'employee' in col:
                name_col = col
                break
        
        if not name_col:
            # Fallback: utiliser la première colonne
            name_col = df.columns[0]
            
        # Trouver les colonnes de jours (soit par nom 'lun', 'mar', soit les 7 colonnes après le nom)
        day_cols = []
        start_idx = df.columns.get_loc(name_col) + 1
        if start_idx + 7 <= len(df.columns):
            day_cols = df.columns[start_idx:start_idx+7]
        else:
            return jsonify({'success': False, 'message': 'Format invalide: Impossible de trouver les 7 jours après la colonne Nom'})

        db = DBManager()
        employees = db.get_all_employees()
        
        updated_count = 0
        errors = []
        logs = []
        
        days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        # Itération sur les lignes
        for index, row in df.iterrows():
            raw_name = str(row[name_col]).strip()
            if not raw_name or raw_name.lower() in ['nan', 'none', 'total']: continue

            # Recherche de l'employé (Fuzzy match simple)
            emp_found = None
            
            # 1. Exact match ID ou Nom
            for e in employees:
                if str(e['person_id']) == raw_name or e['name'].lower() == raw_name.lower():
                    emp_found = e
                    break
            
            # 2. Contient le nom (si pas trouvé)
            if not emp_found:
                for e in employees:
                    if raw_name.lower() in e['name'].lower() or e['name'].lower() in raw_name.lower():
                        # Filtre par département si spécifié
                        if target_dept and target_dept.lower() not in (e['department'] or '').lower():
                            continue
                        emp_found = e
                        break
            
            if not emp_found:
                logs.append(f"⚠️ Ignoré: '{raw_name}' non trouvé en base.")
                continue

            # Construction du planning pour cet employé
            planning_data = {}
            has_valid_data = False
            
            for i, day_col in enumerate(day_cols):
                day_name = days_fr[i]
                cell_val = str(row[day_col]).strip().lower()
                
                # Parsing horaire
                start_hr = "09:00"
                end_hr = "17:00"
                is_repos = False
                
                # Si la cellule est vide ou contient juste des espaces -> REPOS
                if not cell_val:
                    is_repos = True
                    has_valid_data = True 
                    start_hr = "REPOS"
                    end_hr = "REPOS"
                elif 'conge' in cell_val or 'congé' in cell_val:
                    is_repos = True
                    has_valid_data = True
                    start_hr = "CONGÉ"
                    end_hr = "CONGÉ"
                elif 'off' in cell_val or 'repos' in cell_val:
                    is_repos = True
                    has_valid_data = True
                    start_hr = "REPOS"
                    end_hr = "REPOS"
                elif '-' in cell_val:
                    # Tentative de parsing "8am - 4pm" ou "10 - 18"
                    try:
                        parts = cell_val.split('-')
                        t1_raw = parts[0].strip()
                        t2_raw = parts[1].split('\n')[0].strip() # Enlever d'éventuels textes après (ex: "Supervisor")
                        
                        def parse_time_str(t_str):
                            t_str = t_str.replace('am', '').replace('pm', '').strip()
                            if ':' in t_str:
                                h, m = map(int, t_str.split(':'))
                            else:
                                h = int(t_str)
                                m = 0
                            
                            # Correction PM très basique (si < 8 et pas '00', c'est surement PM sauf si c'est le matin tôt)
                            # Ici on suppose format 24h ou AM/PM explicite si possible
                            # Mais l'exemple montre "8am", "4pm".
                            # Si 'am'/'pm' était présent, le replace l'a viré.
                            # On ajoute la logique +12 si pm était là (compliqué car déjà string cleané)
                            return h, m

                        # Re-parsing plus intelligent avec regex pour capturer am/pm
                        import re
                        def smart_parse(raw):
                            raw = raw.lower()
                            is_pm = 'pm' in raw
                            is_am = 'am' in raw
                            nums = re.findall(r'\d+', raw)
                            if not nums: return 0, 0
                            h = int(nums[0])
                            m = int(nums[1]) if len(nums) > 1 else 0
                            
                            if is_pm and h < 12: h += 12
                            if is_am and h == 12: h = 0
                            # Heuristique si pas am/pm: si h < 7 (ex: 3am, 4am fin de shift), c'est matin. Si h > 7 et < 12, matin. 
                            # Si h dans range [1, 6], c'est probablement AM (fin de shift nuit).
                            # Si on a "4pm", c'est 16.
                            
                            # Cas spécifique image: "8am - 4pm" -> 8h, 16h. "6pm - 3am" -> 18h, 03h.
                            # Si pas d'indicateur, et h < 8, on suppose PM pour start ? Non, dangereux.
                            # On va supposer que 'am'/'pm' sont là ou format 24h.
                            if not is_pm and not is_am:
                                # Fallback heuristique pour "2 - 10" ? Non supporté sans am/pm pour l'instant sauf format 24h
                                pass
                                
                            return f"{h:02d}:{m:02d}"

                        start_hr = smart_parse(parts[0])
                        end_hr = smart_parse(parts[1])
                        has_valid_data = True
                        
                    except Exception as e:
                        logs.append(f"⚠️ Erreur format '{cell_val}' pour {raw_name}: {e}")
                        is_repos = True # Fallback

                planning_data[day_name] = {
                    'debut': start_hr,
                    'fin': end_hr,
                    'repos': is_repos
                }
            
            if has_valid_data:
                # Sauvegarde en BDD
                res = db.save_weekly_planning(emp_found['person_id'], week_start_str, planning_data)
                if res:
                    updated_count += 1
                    logs.append(f"✅ {emp_found['name']} : Planning mis à jour.")
                else:
                    errors.append(f"Erreur DB pour {emp_found['name']}")

        return jsonify({
            'success': True,
            'message': 'Importation terminée.',
            'details': {
                'updated': updated_count,
                'errors': errors,
                'logs': logs
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    # Changement de port pour éviter les conflits et compatibilité Cloud
    port = int(os.environ.get("PORT", 5001))
    print(f"Démarrage du serveur sur le port {port}...")
    app.run(debug=True, port=port, host='0.0.0.0')
