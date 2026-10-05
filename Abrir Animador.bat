@echo off
cd /d "%~dp0"
python AnimadorApp.py
if errorlevel 1 pause
