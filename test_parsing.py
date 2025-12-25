"""
Script de test pour vérifier le parsing du fichier Excel
"""

import pandas as pd
import os

def test_parse_excel():
    """Test de parsing du fichier Excel"""
    
    filepath = 'uploads/example.xlsx'
    
    if not os.path.exists(filepath):
        print("[ERREUR] Fichier non trouve:", filepath)
        return
    
    print("[TEST] Test de parsing du fichier Excel\n")
    print("=" * 60)
    
    # Lire le fichier
    df = pd.read_excel(filepath, engine='openpyxl', header=None)
    
    print("[OK] Fichier charge : " + str(len(df)) + " lignes\n")
    
    # Chercher les employés
    employees_found = 0
    
    for idx, row in df.iterrows():
        if pd.notna(row[0]) and str(row[0]).strip() == "Person ID":
            employees_found += 1
            
            # Extraire les infos
            person_id = row[1] if pd.notna(row[1]) else 'N/A'
            
            # Chercher le nom
            name = 'N/A'
            for i in range(len(row)):
                if pd.notna(row[i]) and str(row[i]).strip() == "Employee Name":
                    if i+3 < len(row):
                        name = str(row[i+3]) if pd.notna(row[i+3]) else 'N/A'
                        break
            
            print("\n[EMPLOYE] Employe #" + str(employees_found))
            print(f"   ID: {person_id}")
            print(f"   Nom: {name}")
            
            # Chercher les minutes travaillées
            if idx + 7 < len(df):
                attended_row = df.iloc[idx + 7]
                if pd.notna(attended_row[0]) and str(attended_row[0]).strip() == "Attended":
                    minutes = [x for x in attended_row[1:] if pd.notna(x) and str(x) != '-']
                    if minutes:
                        total_minutes = sum([int(float(m)) for m in minutes if str(m).replace('.','').isdigit()])
                        total_hours = total_minutes / 60
                        print(f"   Total minutes: {total_minutes}")
                        print(f"   Total heures: {round(total_hours, 2)} h")
    
    print("\n" + "=" * 60)
    print("[OK] Total employes trouves: " + str(employees_found))
    print("\n[OK] Test termine avec succes!")

if __name__ == "__main__":
    try:
        test_parse_excel()
    except Exception as e:
        print("[ERREUR] Erreur: " + str(e))
        import traceback
        traceback.print_exc()
