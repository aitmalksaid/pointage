@echo off
echo ===================================================
echo   LANCEMENT DE L'APPLICATION RAPPORT D'ASSIDUITE
echo ===================================================
echo.

echo 1. Verification des dependances...
pip install -r requirements.txt

echo.
echo 2. Lancement de l'application...
echo.
echo L'application sera accessible a l'adresse: http://127.0.0.1:5000
echo Appuyez sur Ctrl+C pour arreter le serveur.
echo.

python app.py

pause
