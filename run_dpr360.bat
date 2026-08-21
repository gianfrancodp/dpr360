@echo off
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente Python non trovato. Esegui prima setup.bat
  pause
  exit /b 2
)
".venv\Scripts\python.exe" -m streamlit run app.py
