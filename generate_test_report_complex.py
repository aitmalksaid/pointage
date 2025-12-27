import pandas as pd
from datetime import datetime, timedelta

def create_employee_block(person_id, name, department, start_date, days=7):
    # Création des lignes pour un employé
    block = []
    
    # Ligne 1 : Les Infos Employé
    row_info = ["Person ID", person_id, "", "", "", "", "Employee Name", "", "", name, "Department", "", "", department, "Position", "", "", "Staff"]
    # On complète pour avoir assez de colonnes
    row_info.extend([None] * (days + 5 - len(row_info)))
    block.append(row_info)
    
    # Ligne 2 : Vide
    block.append([None] * (days + 5))
    
    # Ligne 3 : Dates
    row_dates = ["Date"]
    date_objs = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        date_objs.append(d)
        row_dates.append(d.strftime("%Y-%m-%d")) # Pas le format attendu par le parser (il recalcule), mais utile pour info
    block.append(row_dates)
    
    # Ligne 4 : Timetable (Fake)
    row_timetable = ["Timetable"] + ["09:00-17:00"] * days
    block.append(row_timetable)
    
    # Ligne 5 : On duty (Fake)
    row_onduty = ["On duty"] + ["09:00"] * days
    block.append(row_onduty)
    
    # Ligne 6 : Off duty (Fake)
    row_offduty = ["Off duty"] + ["17:00"] * days
    block.append(row_offduty)
    
    # Ligne 7 : Check-in1 (ENTREES)
    row_cin = ["Check-in1"]
    for i in range(days):
        d = date_objs[i]
        wd = d.weekday()
        # Logique de simulation
        if name == "MBARK EL ASRI" and i == 2: # Mercredi : Entrée mais pas sortie
            val = "09:00"
        elif name == "HANANE LAGALAOUI" or name == "FATIMA LALAOUI EL ISMAILI":
            val = "08:55"
        else:
            val = "09:00"
        
        # Weekend vide pour certains
        if wd >= 5: val = None # Samedi Dimanche
            
        row_cin.append(val if val else None)
    block.append(row_cin)
    
    # Ligne 8 : Check-out1 (SORTIES)
    row_cout = ["Check-out1"]
    for i in range(days):
        d = date_objs[i]
        wd = d.weekday()
        # Logique de simulation
        if name == "MBARK EL ASRI" and i == 2: # Mercredi : PAS DE SORTIE
            val = None
        elif name == "HANANE LAGALAOUI" or name == "FATIMA LALAOUI EL ISMAILI":
            val = "17:05"
        else:
            val = "17:00"

        # Weekend vide
        if wd >= 5: val = None
            
        row_cout.append(val if val else None)
    block.append(row_cout)

    # Ligne 9-15 : Autres infos (Fake pour remplir)
    mapping = {
        "Check-in2": None, "Check-out2": None, 
        "Break": "60", 
        "Normal": "1" if wd < 5 else "0", 
        "Real time": "480", 
        "Late": "0", 
        "Early": "0", 
        "Absent": "0", 
        "OT Time": "0", 
        "Attended": "480" if wd < 5 else "0",
        "Work time": "480",
        "Exception": "",
        "Must C/In": "True", "Must C/Out": "True",
        "Department": department,
        "NDays": "1",
        "WeekEnd": "0",
        "Holiday": "0",
        "Attended Time": "480",
        "NDays_OT": "0",
        "WeekEnd_OT": "0",
        "Holiday_OT": "0"
    }
    
    # Juste ajouter quelques lignes pour que le parser ne plante pas sur l'index
    labels = ["Check-in2", "Check-out2", "Attended", "Status"]
    for lbl in labels:
        row = [lbl]
        for i in range(days):
            if lbl == "Attended":
                val = 480 if date_objs[i].weekday() < 5 else 0
            elif lbl == "Status":
                val = "Normal" if date_objs[i].weekday() < 5 else "Weekend"
            else:
                val = None
            row.append(val)
        block.append(row)
        
    # Séparateur
    block.append([None])
    
    return block

# --- MAIN ---
start_date = datetime(2025, 12, 22) # Lundi 22 Déc 2025

all_rows = []
# Header global faux
all_rows.append(["From: 2025-12-22 To: 2025-12-28"]) 
all_rows.append([None])

# 1. HANANE LAGALAOUI (Nom CORRECT pour le pointage => Mismatch avec HANANAE du planning)
all_rows.extend(create_employee_block("101", "HANANE LAGALAOUI", "RES KABANA/MENAGE", start_date))

# 2. FATIMA LALAOUI EL ISMAILI (Nom CORRECT => Match parfait)
all_rows.extend(create_employee_block("102", "FATIMA LALAOUI EL ISMAILI", "RES KABANA/MENAGE", start_date))

# 3. MBARK EL ASRI (Anomalie de sortie le Mercredi)
all_rows.extend(create_employee_block("103", "MBARK EL ASRI", "RES KABANA/MENAGE", start_date))

# Création du DF et sauvegarde
df = pd.DataFrame(all_rows)
df.to_excel("test_report_22_28_Dec.xlsx", index=False, header=False)
print("Fichier 'test_report_22_28_Dec.xlsx' généré avec succès sur votre Bureau !")
