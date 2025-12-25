-- 1. Création de la base de données
CREATE DATABASE IF NOT EXISTS kabana_attendance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Sélection de la base
USE kabana_attendance;

-- 3. Table des Employés (Information statique)
CREATE TABLE IF NOT EXISTS employes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    person_id VARCHAR(50) NOT NULL UNIQUE, -- ID unique de la pointeuse
    nom VARCHAR(100),
    departement VARCHAR(100),
    poste VARCHAR(100),
    date_embauche VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Table des Rapports (Statistiques par upload)
CREATE TABLE IF NOT EXISTS rapports_mensuels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employe_id INT NOT NULL,
    total_heures DECIMAL(10, 2),
    jours_travailles INT,
    jours_absences INT,
    weekends INT,
    moyenne_heures_jour DECIMAL(10, 2),
    date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employe_id) REFERENCES employes(id) ON DELETE CASCADE
);

-- 5. Table des Détails Journaliers (Optionnel - pour historique précis)
CREATE TABLE IF NOT EXISTS details_journaliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rapport_id INT NOT NULL,
    date_jour VARCHAR(20),
    statut VARCHAR(20),
    check_in VARCHAR(20),
    check_out VARCHAR(20),
    minutes_presence INT,
    FOREIGN KEY (rapport_id) REFERENCES rapports_mensuels(id) ON DELETE CASCADE
);
