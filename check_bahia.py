from db_manager import DBManager
import json

def check_bahia():
    db = DBManager()
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Récupérer l'ID de Bahia
    cursor.execute("SELECT person_id FROM employes WHERE nom LIKE '%BAHIA BAGHOGH%'")
    res = cursor.fetchone()
    if not res:
        print("Employé non trouvé")
        return
        
    pid = res['person_id']
    date_lundi = "2025-12-22"
    
    cursor.execute("SELECT data_json FROM plannings WHERE employe_id_str = %s AND semaine_lundi = %s", (pid, date_lundi))
    plan_row = cursor.fetchone()
    
    if plan_row:
        data = json.loads(plan_row['data_json'])
        print(f"Planning en base pour Bahia Baghogh (Semaine du {date_lundi}) :")
        for jour in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']:
            val = data.get(jour, 'Non défini')
            print(f"  - {jour}: {val}")
    else:
        print("Aucun planning trouvé en base pour cette semaine.")
        
    conn.close()

if __name__ == "__main__":
    check_bahia()
