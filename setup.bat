@echo off
cd /d "%~dp0"
echo DronePanoRAW 360 (DPR360) - Setup
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" echo Setup terminato con codice %RC%.
pause
exit /b %RC%
