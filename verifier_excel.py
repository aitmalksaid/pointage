import pandas as pd
import os
import sys

def check_excel_structure(filepath):
    print(f"ANALYSE DU FICHIER : {filepath}")
    
    try:
        # Essayer de lire avec openpyxl (xlsx) ou xlrd (xls)
        if filepath.endswith('.xlsx'):
            engine = 'openpyxl'
        else:
            engine = 'xlrd'
            
        print(f"Moteur utilisé : {engine}")
        
        # Lire sans header
        df = pd.read_excel(filepath, engine=engine, header=None)
        print("[OK] Fichier lu avec succes")
        print(f"Dimensions : {df.shape[0]} lignes, {df.shape[1]} colonnes")
        
        print("\n--- RECHERCHE DU MOT-CLÉ 'Person ID' ---")
        found = False
        for idx, row in df.head(50).iterrows(): # Vérifie les 50 premières lignes
            first_cell = str(row[0]).strip() if pd.notna(row[0]) else ""
            if "Person" in first_cell or "ID" in first_cell:
                print(f"Ligne {idx}: '{first_cell}'")
                if first_cell == "Person ID":
                    print("[OK] 'Person ID' EXACTEMENT trouve ! Le parsing devrait marcher.")
                    found = True
                else:
                    print("[ATTENTION] Similaire trouve mais pas exact. Le code attend 'Person ID'.")
        
        if not found:
            print("\n[ERREUR] ERREUR CRITIQUE : Impossible de trouver 'Person ID' dans la colonne A.")
            print("Le code actuel cherche strictement la chaîne 'Person ID'.")
            print("Si votre fichier est en anglais 'Person Id' ou 'Employee ID', ça échouera.")
            
    except Exception as e:
        print("\n[ERREUR] ERREUR DE LECTURE : " + str(e))

if __name__ == "__main__":
    # Trouver le dernier fichier uploadé
    upload_dir = 'uploads'
    if not os.path.exists(upload_dir):
        print("Dossier uploads introuvable.")
        sys.exit(1)
        
    files = [os.path.join(upload_dir, f) for f in os.listdir(upload_dir)]
    if not files:
        print("Aucun fichier dans uploads.")
        sys.exit(1)
        
    latest_file = max(files, key=os.path.getctime)
    check_excel_structure(latest_file)
    
    print("\nAppuyez sur Entrée pour quitter...")
    input()
