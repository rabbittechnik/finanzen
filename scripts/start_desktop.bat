@echo off
setlocal
title Finanzen
cd /d "%~dp0.."
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_desktop.ps1"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo Beendet mit Fehlercode %ERR%.
  pause
)
endlocal
