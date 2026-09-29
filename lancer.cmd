@echo off
rem Lanceur Windows : double-cliquer pour démarrer l'application dans le navigateur.
rem Options transmises à lancer.ps1 : -Demo, -SansNavigateur
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0lancer.ps1" %*
if errorlevel 1 pause
