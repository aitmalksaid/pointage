#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test rapide pour l'application Rapport d'Assiduité v2.0
Ce script vérifie que toutes les dépendances sont installées et que l'application fonctionne.
"""

import sys
import os

def print_header(text):
    """Affiche un en-tête formaté"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_success(text):
    """Affiche un message de succès"""
    print(f"[OK] {text}")

def print_error(text):
    """Affiche un message d'erreur"""
    print(f"[ERREUR] {text}")

def print_info(text):
    """Affiche un message d'information"""
    print(f"[INFO] {text}")

def check_python_version():
    """Vérifie la version de Python"""
    print_header("Vérification de Python")
    version = sys.version_info
    print_info(f"Version Python: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print_success("Version Python compatible (3.8+)")
        return True
    else:
        print_error("Version Python incompatible. Requis: 3.8+")
        return False

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    print_header("Vérification des Dépendances")
    
    dependencies = {
        'flask': 'Flask',
        'pandas': 'Pandas',
        'openpyxl': 'OpenPyXL',
        'xlrd': 'XLRD',
        'reportlab': 'ReportLab',
        'werkzeug': 'Werkzeug'
    }
    
    all_installed = True
    
    for module, name in dependencies.items():
        try:
            __import__(module)
            print_success(f"{name} installé")
        except ImportError:
            print_error(f"{name} NON installé")
            all_installed = False
    
    return all_installed

def check_directories():
    """Vérifie que les dossiers nécessaires existent"""
    print_header("Vérification des Dossiers")
    
    directories = ['uploads', 'reports', 'templates']
    all_exist = True
    
    for directory in directories:
        if os.path.exists(directory):
            print_success(f"Dossier '{directory}' existe")
        else:
            print_error(f"Dossier '{directory}' manquant")
            all_exist = False
    
    return all_exist

def check_templates():
    """Vérifie que les fichiers template existent"""
    print_header("Vérification des Templates")
    
    templates = ['templates/index.html', 'templates/dashboard.html']
    all_exist = True
    
    for template in templates:
        if os.path.exists(template):
            print_success(f"Template '{template}' existe")
        else:
            print_error(f"Template '{template}' manquant")
            all_exist = False
    
    return all_exist

def check_app_file():
    """Vérifie que le fichier app_fixed.py existe"""
    print_header("Vérification de l'Application")
    
    if os.path.exists('app_fixed.py'):
        print_success("Fichier 'app_fixed.py' existe")
        return True
    else:
        print_error("Fichier 'app_fixed.py' manquant")
        return False

def test_import_app():
    """Teste l'import de l'application"""
    print_header("Test d'Import de l'Application")
    
    try:
        # Essayer d'importer l'application
        import app_fixed
        print_success("Application importée avec succès")
        
        # Vérifier que Flask app existe
        if hasattr(app_fixed, 'app'):
            print_success("Flask app trouvée")
            return True
        else:
            print_error("Flask app non trouvée")
            return False
    except Exception as e:
        print_error(f"Erreur lors de l'import: {str(e)}")
        return False

def print_summary(results):
    """Affiche un résumé des tests"""
    print_header("Résumé des Tests")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print(f"\nTotal: {total} tests")
    print_success(f"Réussis: {passed}")
    if failed > 0:
        print_error(f"Échoués: {failed}")
    
    print("\nDetails:")
    for test, result in results.items():
        status = "[OK]" if result else "[ERREUR]"
        print(f"  {status} {test}")
    
    if all(results.values()):
        print("\n" + "="*70)
        print("  TOUS LES TESTS SONT PASSES !")
        print("  L'application est prete a etre utilisee.")
        print("  Lancez: python app_fixed.py")
        print("="*70)
        return True
    else:
        print("\n" + "="*70)
        print("  CERTAINS TESTS ONT ECHOUE")
        print("  Veuillez corriger les erreurs ci-dessus.")
        print("="*70)
        return False

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("  TEST DE L'APPLICATION RAPPORT D'ASSIDUITÉ v2.0")
    print("="*70)
    
    results = {}
    
    # Exécuter tous les tests
    results['Python Version'] = check_python_version()
    results['Dépendances'] = check_dependencies()
    results['Dossiers'] = check_directories()
    results['Templates'] = check_templates()
    results['Fichier App'] = check_app_file()
    results['Import App'] = test_import_app()
    
    # Afficher le résumé
    success = print_summary(results)
    
    # Retourner le code de sortie approprié
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
