@echo off
title MotoTrack - Serveur actif
cd /d "%~dp0"
echo ==================================================
echo              MOTOTRACK - SERVEUR ACTIF
echo ==================================================
echo.
echo Adresse PC : http://127.0.0.1:8000/connexion/
echo Adresse reseau ESP32 : http://192.168.1.158:8000/
echo Ne fermez pas cette fenetre pendant l'utilisation.
echo.
".venv\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 (
  echo.
  echo ERREUR : impossible de preparer la base de donnees.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000 --noreload
echo.
echo Le serveur s'est arrete.
pause
