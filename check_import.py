
from db_manager import DBManager
import json

def verify_import():
    db = DBManager()
    conn = db.get_connection()
    if not conn:
        print("Erreur de connexion DB")
        return

    target_date = "2025-12-22"
    print(f"--- Verification des plannings pour la semaine du {target_date} ---")

    cursor = conn.cursor(dictionary=True)
    
    # 1. Recuperer les plannings sans JOIN pour eviter l'erreur de collation
    cursor.execute("SELECT employe_id_str, data_json FROM plannings WHERE semaine_lundi = %s LIMIT 5", (target_date,))
    rows = cursor.fetchall()
    
    print(f"\n{len(rows)} plannings trouves.")
    
    for row in rows:
        emp_id = row['employe_id_str']
        # Recuperer le nom de l'employe separement
        try:
            cursor.execute("SELECT nom, departement FROM employes WHERE person_id = %s", (str(emp_id),))
            emp = cursor.fetchone()
            emp_name = emp['nom'] if emp else "Inconnu"
            emp_dept = emp['departement'] if emp else "?"
        except:
            emp_name = "Erreur nom"
            emp_dept = "?"

        print(f"\nEmploye ID {emp_id} : {emp_name} ({emp_dept})")
        data = json.loads(row['data_json'])
        # Afficher juste Lundi et Mardi pour verifier
        print(f"  Lundi : {data.get('Lundi', 'N/A')}")
        print(f"  Mardi : {data.get('Mardi', 'N/A')}")

    conn.close()

if __name__ == "__main__":
    verify_import()
