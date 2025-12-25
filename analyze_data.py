# -*- coding: utf-8 -*-
"""
Script d'analyse des donnees de pointage et de planning
"""
from db_manager import DBManager
from datetime import datetime, timedelta

def analyze_data():
    db = DBManager()
    conn = db.get_connection()
    if not conn:
        print("[ERREUR] Impossible de se connecter a la base de donnees")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Analyser les pointages
        cursor.execute("""
            SELECT e.person_id, e.nom, COUNT(p.id) as nb_pointages,
                   MIN(p.date_pointage) as premiere_date,
                   MAX(p.date_pointage) as derniere_date
            FROM employes e
            LEFT JOIN pointages p ON e.id = p.employe_id
            GROUP BY e.id
            LIMIT 5
        """)
        
        print("\n[ANALYSE] Analyse des pointages (5 premiers employes):")
        print("-" * 80)
        
        for row in cursor.fetchall():
            print(f"\nEmploye: {row['nom']} (ID: {row['person_id']})")
            print(f"  Nombre de pointages: {row['nb_pointages']}")
            print(f"  Periode: {row['premiere_date']} -> {row['derniere_date']}")
            
            if row['premiere_date']:
                # Calculer le lundi de la premiere semaine
                first_date = row['premiere_date']
                monday = first_date - timedelta(days=first_date.weekday())
                print(f"  Lundi de la premiere semaine: {monday}")
                
                # Verifier si un planning existe pour cette semaine
                cursor.execute("""
                    SELECT COUNT(*) as count FROM plannings 
                    WHERE employe_id_str = %s AND semaine_lundi = %s
                """, (str(row['person_id']), monday))
                
                has_planning = cursor.fetchone()['count'] > 0
                print(f"  Planning individuel pour cette semaine: {'OUI' if has_planning else 'NON'}")
                
                # Recuperer le departement
                cursor.execute("SELECT departement FROM employes WHERE person_id = %s", (str(row['person_id']),))
                dept = cursor.fetchone()['departement']
                print(f"  Departement: {dept}")
                
                # Verifier si un planning de fonction existe
                cursor.execute("""
                    SELECT COUNT(*) as count FROM function_plannings 
                    WHERE department_name = %s
                """, (dept,))
                
                has_func_planning = cursor.fetchone()['count'] > 0
                print(f"  Planning de fonction: {'OUI' if has_func_planning else 'NON'}")
                
                # Analyser un pointage specifique
                cursor.execute("""
                    SELECT date_pointage, check_in, check_out, minutes, statut
                    FROM pointages 
                    WHERE employe_id = (SELECT id FROM employes WHERE person_id = %s)
                    ORDER BY date_pointage
                    LIMIT 3
                """, (str(row['person_id']),))
                
                print(f"  Exemples de pointages:")
                for p in cursor.fetchall():
                    print(f"    {p['date_pointage']}: {p['check_in']} -> {p['check_out']} ({p['minutes']} min) [{p['statut']}]")
        
        print("\n" + "=" * 80)
        print("[CONCLUSION]")
        print("Pour que les calculs fonctionnent, il faut:")
        print("  1. Soit des plannings individuels pour chaque semaine")
        print("  2. Soit des plannings de fonction (deja crees)")
        print("  3. Les plannings de fonction sont utilises comme fallback")
        print("\nLes calculs devraient maintenant fonctionner avec les plannings de fonction!")
        
    except Exception as e:
        print(f"\n[ERREUR] Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_data()
