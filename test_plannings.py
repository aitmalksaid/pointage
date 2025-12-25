# -*- coding: utf-8 -*-
"""
Script de test pour verifier et creer des plannings par defaut
"""
from db_manager import DBManager
import json

def check_and_create_default_plannings():
    db = DBManager()
    conn = db.get_connection()
    if not conn:
        print("[ERREUR] Impossible de se connecter a la base de donnees")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Verifier les departements existants
        cursor.execute("SELECT DISTINCT departement FROM employes WHERE departement IS NOT NULL AND departement != 'N/A'")
        departments = [row['departement'] for row in cursor.fetchall()]
        
        print(f"\n[DEPARTEMENTS] Departements trouves: {len(departments)}")
        for dept in departments:
            print(f"  - {dept}")
        
        # 2. Verifier les plannings de fonction existants
        cursor.execute("SELECT department_name FROM function_plannings")
        existing_func_plans = [row['department_name'] for row in cursor.fetchall()]
        
        print(f"\n[PLANNINGS] Plannings de fonction existants: {len(existing_func_plans)}")
        for dept in existing_func_plans:
            print(f"  - {dept}")
        
        # 3. Creer des plannings par defaut pour les departements sans planning
        default_planning = {
            'Lundi': {'debut': '09:00', 'fin': '17:00', 'repos': False},
            'Mardi': {'debut': '09:00', 'fin': '17:00', 'repos': False},
            'Mercredi': {'debut': '09:00', 'fin': '17:00', 'repos': False},
            'Jeudi': {'debut': '09:00', 'fin': '17:00', 'repos': False},
            'Vendredi': {'debut': '09:00', 'fin': '17:00', 'repos': False},
            'Samedi': {'debut': '09:00', 'fin': '13:00', 'repos': False},
            'Dimanche': {'debut': '09:00', 'fin': '17:00', 'repos': True}
        }
        
        created_count = 0
        for dept in departments:
            if dept not in existing_func_plans:
                print(f"\n[CREATION] Creation du planning par defaut pour: {dept}")
                success = db.save_function_planning(dept, default_planning)
                if success:
                    created_count += 1
                    print(f"  [OK] Planning cree avec succes")
                else:
                    print(f"  [ERREUR] Erreur lors de la creation")
        
        print(f"\n[RESUME] Resume:")
        print(f"  - {created_count} nouveaux plannings de fonction crees")
        print(f"  - Total plannings de fonction: {len(existing_func_plans) + created_count}")
        
        # 4. Verifier les plannings individuels
        cursor.execute("SELECT COUNT(*) as count FROM plannings")
        individual_count = cursor.fetchone()['count']
        print(f"  - Plannings individuels: {individual_count}")
        
        # 5. Afficher un exemple de calcul
        print(f"\n[TEST] Test de calcul des statistiques:")
        cursor.execute("SELECT person_id, nom FROM employes LIMIT 1")
        test_emp = cursor.fetchone()
        if test_emp:
            print(f"  Employe de test: {test_emp['nom']} (ID: {test_emp['person_id']})")
            emp_data = db.get_employee_detailed_data(test_emp['person_id'])
            if emp_data:
                from app import calculate_statistics
                calc_context = db.get_calculation_context()
                stats = calculate_statistics(emp_data, context=calc_context)
                print(f"  Stats calculees:")
                print(f"    - Total heures: {stats['total_hours']}h")
                print(f"    - Heures supp: {stats['total_overtime_minutes']} min")
                print(f"    - Heures manquantes: {stats['total_undertime_minutes']} min")
                print(f"    - Retards: {stats['total_late_minutes']} min")
        
    except Exception as e:
        print(f"\n[ERREUR] Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_and_create_default_plannings()
