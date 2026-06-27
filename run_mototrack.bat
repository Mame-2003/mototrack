@echo off
title MotoTrack
cd /d "%~dp0"
start "" /b cmd.exe /c "timeout /t 5 /nobreak >nul && start \"\" \"http://127.0.0.1:8000/connexion/\""
call "%~dp0server_mototrack.bat"
