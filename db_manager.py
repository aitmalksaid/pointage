import mysql.connector
from datetime import datetime, timedelta
import json
import os

class DBManager:
    def __init__(self):
        self.config = {
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASSWORD', ''),
            'host': os.environ.get('DB_HOST', 'localhost'),
            'database': os.environ.get('DB_NAME', 'kabana_attendance'),
            'port': int(os.environ.get('DB_PORT', 3306)),
            'raise_on_warnings': False
        }
        
        # Activer SSL si on est sur Aiven (détection via DB_HOST)
        if 'aivencloud' in self.config['host']:
             self.config['ssl_disabled'] = False
             self.config['ssl_verify_cert'] = False
             self.config['ssl_verify_identity'] = False

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except mysql.connector.Error as err:
            print("[ERREUR] Erreur de connexion BDD: " + str(err))
            return None

    def init_planning_table(self):
        """Initialisation robuste des tables avec migration automatique"""
        conn = self.get_connection()
        if not conn: return
        cursor = conn.cursor()
        
        # 1. EMPLOYEES
        cursor.execute("""CREATE TABLE IF NOT EXISTS employes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            person_id VARCHAR(50) NOT NULL UNIQUE,
            nom VARCHAR(100),
            departement VARCHAR(100),
            poste VARCHAR(100),
            date_embauche VARCHAR(50)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

        # 2. PLANNINGS (Migration si nécessaire)
        try:
            cursor.execute("SHOW COLUMNS FROM plannings LIKE 'data_json'")
            if not cursor.fetchone():
                # On renomme l'ancienne table si elle existe pour ne pas perdre les données
                cursor.execute("RENAME TABLE plannings TO plannings_old")
                print("[ATTENTION] Ancienne table plannings renommee en plannings_old")
        except: pass

        cursor.execute("""CREATE TABLE IF NOT EXISTS plannings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employe_id_str VARCHAR(50) NOT NULL,
            semaine_lundi DATE NOT NULL,
            data_json JSON NOT NULL,
            UNIQUE KEY unique_weekly_plan (employe_id_str, semaine_lundi)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

        # 3. FUNCTION PLANNINGS
        cursor.execute("""CREATE TABLE IF NOT EXISTS function_plannings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            department_name VARCHAR(100) NOT NULL UNIQUE,
            data JSON NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

        # 3b. PLANNING TEMPLATES
        cursor.execute("""CREATE TABLE IF NOT EXISTS planning_templates (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nom VARCHAR(100) NOT NULL UNIQUE,
            data JSON NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

        # 3c. RAPPORTS MENSUELS (Stats calculées)
        cursor.execute("""CREATE TABLE IF NOT EXISTS rapports_mensuels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            person_id VARCHAR(50) NOT NULL UNIQUE,
            total_heures DECIMAL(10, 2),
            jours_travailles INT,
            jours_absences INT,
            weekends INT,
            moyenne_heures_jour DECIMAL(10, 2),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")

        # 4. POINTAGES
        cursor.execute("""CREATE TABLE IF NOT EXISTS pointages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employe_id INT NOT NULL,
            date_pointage DATE NOT NULL,
            check_in VARCHAR(10),
            check_out VARCHAR(10),
            minutes INT DEFAULT 0,
            statut VARCHAR(50),
            FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE CASCADE,
            UNIQUE KEY unique_pointage (employe_id, date_pointage)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""")
        
        # --- MISE À JOUR SÉCURISÉE DES COLONNES (ALTER) ---
        try:
            cursor.execute("SHOW COLUMNS FROM pointages LIKE 'minutes'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE pointages ADD COLUMN minutes INT DEFAULT 0")
                cursor.execute("ALTER TABLE pointages ADD COLUMN statut VARCHAR(50)")
                print("[OK] Colonnes minutes et statut ajoutees.")
        except: pass

        conn.commit()
        cursor.close()
        conn.close()

    def save_data(self, employees_data):
        """Sauvegarde persistante des employés et de TOUS leurs pointages détaillés"""
        conn = self.get_connection()
        if not conn:
            return False, "Impossible de se connecter à la base de données"

        cursor = conn.cursor()
        total_points = 0
        try:
            for emp in employees_data:
                # 1. Sauvegarder/Mettre à jour l'employé
                cursor.execute("SELECT id FROM employes WHERE person_id = %s", (str(emp['person_id']),))
                result = cursor.fetchone()
                
                if result:
                    emp_db_id = result[0]
                    cursor.execute("""
                        UPDATE employes SET nom=%s, departement=%s, poste=%s 
                        WHERE id=%s
                    """, (emp['name'], emp['department'], emp['position'], emp_db_id))
                else:
                    cursor.execute("""
                        INSERT INTO employes (person_id, nom, departement, poste, date_embauche)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (str(emp['person_id']), emp['name'], emp['department'], emp['position'], emp.get('joining_date', 'N/A')))
                    emp_db_id = cursor.lastrowid

                # 2. Préparation des pointages pour insertion en lot (executemany)
                if 'dates' in emp and 'check_ins' in emp:
                    pointages_to_insert = []
                    for i in range(len(emp['dates'])):
                        date_val_raw = emp['dates'][i]
                        if not date_val_raw or date_val_raw in ('-', 'nan', 'None'):
                            continue
                            
                        try:
                            processed_date = None
                            date_str = str(date_val_raw).strip()
                            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S'):
                                try:
                                    processed_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                                    break
                                except: continue
                            if not processed_date: processed_date = date_str.split(' ')[0]
                            date_val = processed_date
                        except: continue

                        c_in = emp['check_ins'][i] if i < len(emp['check_ins']) else None
                        c_out = emp['check_outs'][i] if i < len(emp['check_outs']) else None
                        mins = emp['attended_minutes'][i] if 'attended_minutes' in emp and i < len(emp['attended_minutes']) else 0
                        stat = emp['statuses'][i] if 'statuses' in emp and i < len(emp['statuses']) else None
                        
                        pointages_to_insert.append((emp_db_id, date_val, c_in, c_out, int(float(mins or 0)), stat))

                    if pointages_to_insert:
                        cursor.executemany("""
                            INSERT INTO pointages (employe_id, date_pointage, check_in, check_out, minutes, statut)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE 
                                check_in = VALUES(check_in), 
                                check_out = VALUES(check_out),
                                minutes = VALUES(minutes),
                                statut = VALUES(statut)
                        """, pointages_to_insert)
                        total_points += len(pointages_to_insert)

            conn.commit()
            print("[OK] Sauvegarde reussie : " + str(len(employees_data)) + " employes, " + str(total_points) + " pointages.")
            return True, f"Succès : {total_points} pointages enregistrés."
        except mysql.connector.Error as err:
            conn.rollback()
            print("[ERREUR] Erreur SQL lors de la sauvegarde : " + str(err))
            return False, f"Erreur SQL: {err}"
        finally:
            cursor.close()
            conn.close()

    def update_employee_stats(self, person_id, stats):
        """Met à jour ou insère les statistiques d'un employé"""
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO rapports_mensuels (person_id, total_heures, jours_travailles, jours_absences, weekends, moyenne_heures_jour)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    total_heures = VALUES(total_heures),
                    jours_travailles = VALUES(jours_travailles),
                    jours_absences = VALUES(jours_absences),
                    weekends = VALUES(weekends),
                    moyenne_heures_jour = VALUES(moyenne_heures_jour)
            """, (str(person_id), stats['total_hours'], stats['total_days_worked'], 
                  stats['total_days_absent'], stats.get('total_weekends', 0), stats['average_hours_per_day']))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur update_employee_stats: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_calculation_context(self):
        """Récupère tout le nécessaire pour les calculs de stats en une seule fois"""
        conn = self.get_connection()
        if not conn: return {'functions': {}, 'individual': {}, 'emp_depts': {}}
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Plannings par fonction
            cursor.execute("SELECT department_name, data FROM function_plannings")
            functions = {row['department_name']: json.loads(row['data']) for row in cursor.fetchall()}
            
            # 2. Plannings individuels
            cursor.execute("SELECT employe_id_str, semaine_lundi, data_json FROM plannings")
            individual = {}
            for row in cursor.fetchall():
                eid = row['employe_id_str']
                if eid not in individual: individual[eid] = {}
                individual[eid][str(row['semaine_lundi'])] = json.loads(row['data_json'])
            
            # 3. Départements des employés (pour fallback sur planning fonction)
            cursor.execute("SELECT person_id, departement FROM employes")
            emp_depts = {str(row['person_id']): row['departement'] for row in cursor.fetchall()}
            
            return {
                'functions': functions,
                'individual': individual,
                'emp_depts': emp_depts
            }
        finally:
            cursor.close()
            conn.close()


    def get_employee_detailed_data(self, person_id):
        """Récupère toutes les informations d'un seul employé"""
        conn = self.get_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, person_id, nom as name, departement as department, poste as position, date_embauche as joining_date FROM employes WHERE person_id = %s", (str(person_id),))
            emp = cursor.fetchone()
            if not emp: return None
            
            cursor.execute("""
                SELECT date_pointage, check_in, check_out, minutes, statut
                FROM pointages WHERE employe_id = %s ORDER BY date_pointage
            """, (emp['id'],))
            pointages = cursor.fetchall()
            
            emp['dates'] = [str(p['date_pointage']) for p in pointages]
            emp['check_ins'] = [p['check_in'] for p in pointages]
            emp['check_outs'] = [p['check_out'] for p in pointages]
            emp['attended_minutes'] = [p['minutes'] for p in pointages]
            emp['statuses'] = [p['statut'] for p in pointages]
            
            return emp
        finally:
            cursor.close()
            conn.close()

    def get_all_employees(self):
        """Récupère la liste simple de tous les employés"""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT person_id, nom as name, departement as department, poste as position FROM employes")
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_all_employees_with_detailed_data_filtered(self, year=None, month=None):
        """Récupère tous les employés avec leurs pointages filtrés par période"""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Récupérer tous les employés
            cursor.execute("SELECT id, person_id, nom as name, departement as department, poste as position, date_embauche as joining_date FROM employes")
            employees = cursor.fetchall()
            
            # 2. Pour chaque employé, récupérer ses pointages filtrés
            for emp in employees:
                if year and month:
                    query = """
                        SELECT date_pointage, check_in, check_out, minutes, statut
                        FROM pointages 
                        WHERE employe_id = %s AND YEAR(date_pointage) = %s AND MONTH(date_pointage) = %s 
                        ORDER BY date_pointage
                    """
                    cursor.execute(query, (emp['id'], int(year), int(month)))
                else:
                    cursor.execute("""
                        SELECT date_pointage, check_in, check_out, minutes, statut
                        FROM pointages WHERE employe_id = %s ORDER BY date_pointage
                    """, (emp['id'],))
                
                pointages = cursor.fetchall()
                
                emp['dates'] = [str(p['date_pointage']) for p in pointages]
                emp['check_ins'] = [p['check_in'] for p in pointages]
                emp['check_outs'] = [p['check_out'] for p in pointages]
                emp['attended_minutes'] = [p['minutes'] for p in pointages]
                emp['statuses'] = [p['statut'] for p in pointages]
            
            return [e for e in employees if e['dates']] # On ne retourne que ceux qui ont des données pour la période
        finally:
            cursor.close()
            conn.close()

    def get_available_periods(self):
        """Récupère la liste des mois/années disponibles dans la base de données"""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT DISTINCT YEAR(date_pointage) as year, MONTH(date_pointage) as month 
                FROM pointages 
                ORDER BY year DESC, month DESC
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # --- MÉTHODES POUR LE PLANNING ---
    def save_weekly_planning(self, employee_id_str, monday_date, data):
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO plannings (employe_id_str, semaine_lundi, data_json)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE data_json = VALUES(data_json)
            """, (str(employee_id_str), monday_date, json.dumps(data)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur save_weekly_planning: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def save_employee_planning(self, employee_id_str, monday_date, data):
        """Alias pour save_weekly_planning"""
        return self.save_weekly_planning(employee_id_str, monday_date, data)

    def get_employee_planning(self, employee_id_str, monday_date):
        conn = self.get_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT data_json FROM plannings WHERE employe_id_str = %s AND semaine_lundi = %s", (str(employee_id_str), monday_date))
            row = cursor.fetchone()
            return json.loads(row['data_json']) if row else None
        finally:
            cursor.close()
            conn.close()

    def get_templates(self):
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT nom, data FROM planning_templates")
            rows = cursor.fetchall()
            return [{'nom': r['nom'], 'planning': json.loads(r['data'])} for r in rows]
        finally:
            cursor.close()
            conn.close()

    def get_employees_with_planning(self):
        """Récupère la liste des noms qui ont au moins un créneau dans le planning"""
        conn = self.get_connection()
        if not conn: return []
        cursor = conn.cursor()
        try:
            # 1. Récupérer les ID uniques qui ont un planning
            cursor.execute("SELECT DISTINCT employe_id_str FROM plannings")
            emp_ids = [row[0] for row in cursor.fetchall() if row[0]]
            
            if not emp_ids:
                return []
                
            # 2. Récupérer les noms correspondants (Séparé pour éviter problèmes de collation JOIN)
            # On y va par batch ou simple IN clause (si la liste n'est pas trop enorme)
            names = []
            if emp_ids:
                format_strings = ','.join(['%s'] * len(emp_ids))
                cursor.execute(f"SELECT nom FROM employes WHERE person_id IN ({format_strings})", tuple(emp_ids))
                names = [row[0] for row in cursor.fetchall() if row[0]]
                
            return names
        except Exception as e:
            print(f"[ERREUR] get_employees_with_planning: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def save_template(self, nom, data):
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO planning_templates (nom, data)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE data = VALUES(data)
            """, (nom, json.dumps(data)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur save_template: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_day_planning(self, person_id, date_str):
        try:
            date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            return None # Date invalide ou malformée
        monday_date = (date_obj - timedelta(days=date_obj.weekday())).strftime('%Y-%m-%d')
        day_name = date_obj.strftime('%A')
        
        conn = self.get_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT data_json FROM plannings WHERE employe_id_str = %s AND semaine_lundi = %s", (str(person_id), monday_date))
            row = cursor.fetchone()
            if row:
                planning = json.loads(row['data_json'])
                return {
                    'heure_debut': planning[day_name]['debut'],
                    'heure_fin': planning[day_name]['fin'],
                    'est_repos': planning[day_name]['repos']
                }
            
            cursor.execute("SELECT departement FROM employes WHERE person_id = %s", (str(person_id),))
            emp = cursor.fetchone()
            if emp:
                dept_plan = self.get_function_planning(emp['departement'])
                if dept_plan and day_name in dept_plan:
                    return {
                        'heure_debut': dept_plan[day_name]['debut'],
                        'heure_fin': dept_plan[day_name]['fin'],
                        'est_repos': dept_plan[day_name]['repos']
                    }
            return None
        finally:
            cursor.close()
            conn.close()

    def save_function_planning(self, dept_name, data):
        conn = self.get_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO function_plannings (department_name, data)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE data = VALUES(data)
            """, (dept_name, json.dumps(data)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur save_function_planning: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def get_function_planning(self, dept_name):
        conn = self.get_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT data FROM function_plannings WHERE department_name = %s", (dept_name,))
            row = cursor.fetchone()
            return json.loads(row['data']) if row else None
        finally:
            cursor.close()
            conn.close()
