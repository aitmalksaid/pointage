# 🚀 GUIDE DE DÉMARRAGE RAPIDE

## ⚡ Installation en 3 étapes

### 1️⃣ Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2️⃣ Démarrer l'application
```bash
python app_fixed.py
```

### 3️⃣ Ouvrir dans le navigateur
```
http://127.0.0.1:5000
```

---

## 📊 Utilisation du Dashboard

Une fois le fichier uploadé, vous serez redirigé vers le **dashboard interactif** :

### Statistiques Globales
- Nombre total d'employés
- Total des heures travaillées
- Moyenne heures/employé
- Taux de présence

### 🔍 Recherche et Filtres (NOUVEAU !)
1. **Rechercher** : Tapez un nom ou ID d'employé
2. **Filtrer** : Sélectionnez un département
3. **Trier** : Choisissez un critère de tri (nom, heures, jours, absences)

### 📊 Graphiques Analytiques
- Heures travaillées par employé (barres)
- Répartition Présence/Absence (donut)
- Heures par département (barres horizontales)
- Comparaison des performances (ligne)

### 📋 Tableau Récapitulatif
- Vue détaillée de tous les employés
- Filtrage et tri en temps réel
- Badges colorés pour les statistiques

---

## 🎨 Nouvelles Fonctionnalités v2.0

### ✨ Interface Premium
- **Particules animées** : Arrière-plan dynamique avec 8 particules flottantes
- **Animations fluides** : Transitions et effets de survol améliorés
- **Design responsive** : Optimisé pour tous les écrans

### 🔍 Recherche Intelligente
- **Temps réel** : Résultats instantanés pendant la saisie
- **Multi-critères** : Recherche par nom ou ID
- **Insensible à la casse** : Fonctionne avec majuscules/minuscules

### 🎯 Filtrage Avancé
- **Par département** : Isolez les employés d'un département
- **Tri multiple** : 4 critères de tri disponibles
- **Combinaison** : Utilisez plusieurs filtres simultanément

---

## 📄 Génération du PDF

Cliquez sur le bouton **"Générer PDF"** dans le dashboard pour :
- Créer un rapport professionnel au format PDF
- Inclure toutes les statistiques et détails
- Télécharger automatiquement le fichier

---

## 🔍 Test Rapide

### Tester le parsing du fichier
```bash
python test_parsing.py
```

Cela affichera :
- Nombre d'employés trouvés
- ID et nom de chaque employé
- Total heures calculées

---

## 📂 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `app_fixed.py` | ✅ Application corrigée (UTILISER CELUI-CI) |
| `app.py` | ❌ Ancienne version (NE PAS UTILISER) |
| `templates/index_new.html` | ✅ Interface moderne |
| `templates/index.html` | ❌ Ancienne interface |
| `requirements.txt` | Dépendances Python |
| `test_parsing.py` | Script de test |

---

## ⚠️ Problèmes Courants

### Erreur : "Module not found"
**Solution :**
```bash
pip install -r requirements.txt
```

### Erreur : "xlrd version"
**Solution :**
```bash
pip install --upgrade xlrd
```

### Erreur : "File is not a zip file"
**Cause :** Fichier Excel corrompu

**Solution :**
1. Ouvrir le fichier dans Excel
2. Enregistrer sous → nouveau fichier .xlsx
3. Réessayer

### L'application ne démarre pas
**Vérifier :**
```bash
python --version  # Doit être Python 3.8+
pip list          # Vérifier les packages installés
```

---

## 📊 Format du Fichier Excel Attendu

Votre fichier Excel doit contenir :
- **Person ID** : Identifiant employé
- **Employee Name** : Nom
- **Department** : Département
- **Date** : Jours du mois
- **Check-in1** : Heure d'entrée
- **Check-out1** : Heure de sortie
- **Attended** : Minutes travaillées
- **Status** : W (Worked), A (Absent)

---

## ✅ Vérification de l'Installation

```bash
# Vérifier Python
python --version

# Vérifier pip
pip --version

# Vérifier les packages
pip list | findstr "Flask pandas openpyxl xlrd reportlab"
```

Vous devriez voir :
```
Flask          3.0.0
pandas         2.1.4
openpyxl       3.1.2
xlrd           2.0.1
reportlab      4.0.7
```

---

## 🎯 Résultat Attendu

Le PDF généré contiendra :

### 📋 Statistiques Globales
- Nombre total d'employés
- Total heures travaillées
- Moyenne heures/employé

### 👥 Détails par Employé
- Nom et ID
- Département et poste
- Jours travaillés
- Jours d'absence
- **Total heures travaillées**
- **Moyenne heures/jour**

---

## 💡 Astuces

### Utiliser l'interface moderne
Remplacer `index.html` par `index_new.html` dans `app_fixed.py` :
```python
# Ligne 23
return render_template('index_new.html')  # Au lieu de 'index.html'
```

### Changer le port
```python
# Dernière ligne de app_fixed.py
app.run(debug=True, port=8000)  # Au lieu de 5000
```

### Mode production
```python
app.run(debug=False, host='0.0.0.0')
```

---

## 📞 Besoin d'Aide ?

1. **Vérifier les logs** dans le terminal
2. **Tester le parsing** avec `test_parsing.py`
3. **Vérifier le format** du fichier Excel
4. **Consulter** `ANALYSE_CORRECTIONS.md` pour les détails

---

## 🎉 C'est Tout !

Votre application est maintenant prête à générer des rapports PDF professionnels !

**Bon travail ! 🚀**
