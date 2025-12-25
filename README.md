# 📊 Application de Rapport d'Assiduité

Application Flask pour générer automatiquement des rapports PDF d'assiduité à partir de fichiers Excel.

## ✨ Fonctionnalités

### 🎯 Fonctionnalités Principales

- ✅ **Upload de fichiers Excel** (.xls et .xlsx)
- 📈 **Analyse automatique** des données d'assiduité
- 📊 **Dashboard interactif** avec visualisations
- 📄 **Génération de PDF professionnel** avec ReportLab
- 🎨 **Interface moderne** avec drag-and-drop

### 📊 Statistiques et Analyses

- 💼 **Heures travaillées** par employé
- 📅 **Jours d'absence** et de présence
- ⏱️ **Moyenne d'heures** par jour
- 📈 **Statistiques globales** de l'entreprise
- 🏢 **Analyse par département**

### 🔍 Nouvelles Fonctionnalités v2.0

- **🔎 Recherche en temps réel** : Trouvez instantanément un employé par nom ou ID
- **🎯 Filtrage par département** : Isolez les employés d'un département spécifique
- **📊 Tri multi-critères** : Triez par nom, heures, jours travaillés ou absences
- **🎨 Particules animées** : Arrière-plan dynamique avec effets visuels premium
- **📈 4 types de graphiques** : Barres, donut, horizontales et ligne
- **⚡ Performance optimisée** : Filtrage instantané côté client

### 🎨 Interface Premium

- **Animations fluides** : Transitions et effets de survol
- **Design responsive** : Optimisé pour desktop, tablette et mobile
- **Effets visuels** : Particules flottantes et dégradés modernes
- **Feedback visuel** : Indicateurs colorés et badges interactifs

## 🔧 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Vérifier l'installation

```bash
pip list
```

Vous devriez voir :
- Flask
- pandas
- openpyxl
- xlrd
- reportlab
- Werkzeug

## 🚀 Utilisation

### Démarrer l'application

```bash
python app_fixed.py
```

L'application sera accessible sur : `http://127.0.0.1:5000`

### Utiliser l'interface

1. Ouvrez votre navigateur à `http://127.0.0.1:5000`
2. Cliquez ou glissez-déposez votre fichier Excel
3. Cliquez sur "Générer le Rapport PDF"
4. Vous serez redirigé vers le **Dashboard Interactif**

### 📊 Utiliser le Dashboard

#### Visualiser les Statistiques Globales
- **Nombre d'employés** : Total des employés dans le fichier
- **Heures totales** : Somme de toutes les heures travaillées
- **Moyenne par employé** : Heures moyennes par employé
- **Taux de présence** : Pourcentage de présence globale

#### 🔍 Rechercher et Filtrer

**Recherche :**
1. Tapez un nom ou ID dans le champ "Rechercher un employé"
2. Les résultats s'affichent instantanément

**Filtrage par département :**
1. Sélectionnez un département dans le menu déroulant
2. Seuls les employés de ce département s'affichent

**Tri des données :**
1. Choisissez un critère dans "Trier par"
   - Nom (A-Z) : Ordre alphabétique
   - Heures : Du plus grand au plus petit
   - Jours travaillés : Par présence
   - Absences : Par nombre d'absences

**Combiner les filtres :**
- Utilisez plusieurs filtres simultanément
- Exemple : Rechercher "Ahmed" + Département "RES KABANA" + Trier par "Heures"

#### 📈 Analyser les Graphiques

**4 graphiques interactifs :**
1. **Heures par employé** (Barres) : Comparez les heures travaillées
2. **Présence/Absence** (Donut) : Visualisez la répartition
3. **Heures par département** (Barres horizontales) : Analysez par département
4. **Performances** (Ligne) : Suivez les tendances

**Interactions :**
- Survolez les graphiques pour voir les détails
- Les graphiques se mettent à jour automatiquement

#### 📄 Générer le PDF Final

1. Cliquez sur le bouton "📄 Générer PDF" en haut à droite
2. Le PDF sera automatiquement téléchargé
3. Le rapport contient toutes les statistiques et détails

## 📁 Structure du Projet

```
kabana/python/
├── app_fixed.py              # Application Flask corrigée
├── app.py                    # Ancienne version (à remplacer)
├── requirements.txt          # Dépendances Python
├── templates/
│   ├── index_new.html       # Nouvelle interface moderne
│   └── index.html           # Ancienne interface
├── uploads/                 # Fichiers Excel uploadés
└── reports/                 # Rapports PDF générés
```

## 🔍 Problèmes Corrigés

### 1. ❌ Mauvais moteur Excel
**Avant :** `engine = 'pyxlsb'` pour les fichiers .xls
**Après :** `engine = 'xlrd'` pour les fichiers .xls

### 2. ❌ Génération PDF non fonctionnelle
**Avant :** Tentative de conversion Excel → PDF avec pdfkit
**Après :** Utilisation de ReportLab pour créer des PDF natifs

### 3. ❌ Analyse des données inadaptée
**Avant :** Recherche d'une colonne "Attendance" inexistante
**Après :** Parsing intelligent du format de rapport d'assiduité

### 4. ✅ Nouvelles fonctionnalités
- Extraction des données par employé
- Calcul des heures travaillées (minutes → heures)
- Statistiques détaillées
- PDF professionnel avec tableaux et mise en forme

## 📊 Format du Fichier Excel

L'application attend un fichier Excel avec la structure suivante :

```
Person ID: [ID]    Employee Name: [Nom]    Department: [Département]
Date:      24  25  26  27  28  29  30  31  1  2  3  ...
Check-in1: 09:00 ...
Check-out1: 18:00 ...
Attended:  540 ...  (minutes)
Status:    W  A  W-# ...
Summary:   Normal Attendance:12; Weekend:10; ...
```

## 📄 Contenu du Rapport PDF

Le rapport PDF généré contient :

1. **En-tête**
   - Titre du rapport
   - Date de génération

2. **Statistiques Globales**
   - Nombre total d'employés
   - Total heures travaillées
   - Moyenne heures/employé

3. **Détails par Employé**
   - Nom et ID
   - Département et poste
   - Jours travaillés
   - Jours d'absence
   - Total heures travaillées
   - Moyenne heures/jour

## 🐛 Dépannage

### Erreur : "Module not found"
```bash
pip install -r requirements.txt
```

### Erreur : "xlrd version"
```bash
pip install --upgrade xlrd
```

### Erreur : "File is not a zip file"
Le fichier Excel est corrompu. Essayez de :
1. Ouvrir le fichier dans Excel
2. Enregistrer sous → nouveau fichier .xlsx
3. Réessayer l'upload

## 📝 Notes

- Les fichiers uploadés sont sauvegardés dans `uploads/`
- Les rapports PDF sont sauvegardés dans `reports/`
- L'application supporte les fichiers .xls (ancien format) et .xlsx (nouveau format)

## 🎯 Prochaines Améliorations Possibles

### ✅ Déjà Implémenté (v2.0)
- [x] Dashboard interactif avec graphiques
- [x] Filtrage par département
- [x] Recherche en temps réel
- [x] Tri multi-critères

### 🔮 Roadmap Future
- [ ] Ajout de graphiques dans le PDF
- [ ] Export Excel des données filtrées
- [ ] Comparaison entre mois
- [ ] Envoi automatique par email
- [ ] Interface multi-langue (FR, EN, AR)
- [ ] Mode sombre/clair
- [ ] Sauvegarde des filtres préférés
- [ ] Alertes pour absences répétées
- [ ] Application mobile native
- [ ] API REST complète

### 📚 Documentation Complète

- **README.md** : Ce fichier - Documentation principale
- **QUICKSTART.md** : Guide de démarrage rapide
- **NOUVELLES_FONCTIONNALITES.md** : Guide détaillé des nouvelles fonctionnalités
- **CHANGELOG.md** : Historique des versions et modifications
- **ANALYSE_CORRECTIONS.md** : Analyse des bugs corrigés

## 📞 Support

Pour toute question ou problème, vérifiez :
1. Les logs de l'application dans le terminal
2. Le format de votre fichier Excel
3. Les dépendances installées

---

**Version :** 2.0 (Corrigée)
**Date :** Décembre 2025
