@echo off
cd /d "%~dp0"
python -c "import PySide6" 2>nul || python -m pip install -r requirements.txt
python AnimadorApp.py
if errorlevel 1 pause
