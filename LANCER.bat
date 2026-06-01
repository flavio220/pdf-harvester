@echo off
echo ================================================
echo   PDF Harvester - Lancement du serveur
echo ================================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe.
    echo Telecharge-le sur https://python.org
    pause
    exit /b 1
)

echo Installation des dependances...
pip install -r requirements.txt -q

echo.
echo Serveur en cours de demarrage...
echo.
echo ✅ Ouvre ton navigateur sur: http://localhost:5000
echo    (ne pas ouvrir les fichiers .html directement)
echo.
echo Pour arreter le serveur: CTRL+C
echo ================================================
echo.

python wsgi.py
pause
