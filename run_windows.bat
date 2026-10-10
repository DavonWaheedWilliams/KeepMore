@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (echo Could not create Python environment. Install Python 3.11 or newer. & pause & exit /b 1)
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 (echo Dependency installation failed. Check your internet connection. & pause & exit /b 1)
)
.venv\Scripts\python.exe -m streamlit run app.py
pause
