# -*- coding: utf-8 -*-
"""
Script pour analyser les horaires moyens par departement et ajuster les plannings
"""
from db_manager import DBManager
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_and_adjust_plannings():
    db = DBManager()
    conn = db.get_connection()
    if not conn:
        print("[ERREUR] Impossible de se connecter a la base de donnees")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Analyser les horaires moyens par departement et jour de la semaine
        cursor.execute("""
            SELECT e.departement, p.date_pointage, p.check_in, p.check_out, p.minutes
            FROM employes e
            JOIN pointages p ON e.id = p.employe_id
            WHERE p.check_in IS NOT NULL AND p.check_in != '-' AND p.check_in != ''
                  AND p.check_out IS NOT NULL AND p.check_out != '-' AND p.check_out != ''
                  AND p.minutes > 0
            ORDER BY e.departement, p.date_pointage
        """)
        
        # Regrouper par departement et jour de la semaine
        dept_stats = defaultdict(lambda: defaultdict(list))
        
        for row in cursor.fetchall():
            dept = row['departement']
            date = row['date_pointage']
            day_name = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][date.weekday()]
            
            try:
                check_in = datetime.strptime(row['check_in'][:5], '%H:%M')
                check_out = datetime.strptime(row['check_out'][:5], '%H:%M')
                
                dept_stats[dept][day_name].append({
                    'check_in': check_in,
                    'check_out': check_out,
                    'minutes': row['minutes']
                })
            except:
                pass
        
        # 2. Calculer les moyennes et creer les plannings ajustes
        print("\n[ANALYSE] Horaires moyens par departement:")
        print("=" * 100)
        
        for dept in sorted(dept_stats.keys()):
            print(f"\n{dept}:")
            planning = {}
            
            for day in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']:
                if day in dept_stats[dept] and len(dept_stats[dept][day]) > 0:
                    # Calculer les moyennes
                    avg_in_minutes = sum([d['check_in'].hour * 60 + d['check_in'].minute for d in dept_stats[dept][day]]) / len(dept_stats[dept][day])
                    avg_out_minutes = sum([d['check_out'].hour * 60 + d['check_out'].minute for d in dept_stats[dept][day]]) / len(dept_stats[dept][day])
                    avg_duration = sum([d['minutes'] for d in dept_stats[dept][day]]) / len(dept_stats[dept][day])
                    
                    avg_in = f"{int(avg_in_minutes // 60):02d}:{int(avg_in_minutes % 60):02d}"
                    avg_out = f"{int(avg_out_minutes // 60):02d}:{int(avg_out_minutes % 60):02d}"
                    
                    print(f"  {day}: {avg_in} - {avg_out} (moy: {int(avg_duration)}min, {len(dept_stats[dept][day])} pointages)")
                    
                    planning[day] = {
                        'debut': avg_in,
                        'fin': avg_out,
                        'repos': False
                    }
                else:
                    # Pas de donnees pour ce jour, considerer comme repos
                    print(f"  {day}: REPOS (pas de donnees)")
                    planning[day] = {
                        'debut': '09:00',
                        'fin': '17:00',
                        'repos': True
                    }
            
            # 3. Sauvegarder le planning ajuste
            print(f"\n  [MISE A JOUR] Mise a jour du planning de fonction pour {dept}...")
            success = db.save_function_planning(dept, planning)
            if success:
                print(f"  [OK] Planning mis a jour avec succes")
            else:
                print(f"  [ERREUR] Erreur lors de la mise a jour")
        
        print("\n" + "=" * 100)
        print("[TERMINE] Plannings ajustes en fonction des horaires reels!")
        
    except Exception as e:
        print(f"\n[ERREUR] Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_and_adjust_plannings()
