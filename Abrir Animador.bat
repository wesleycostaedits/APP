@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Animador

rem Procura o Python: primeiro o inicializador "py", depois "python".
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY (
    echo.
    echo  Python nao encontrado.
    echo  Instale em https://www.python.org/downloads/
    echo  e marque "Add python.exe to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo  Instalando o PySide6 ^(so na primeira vez, pode levar alguns minutos^)...
    %PY% -m pip install --user -r requirements.txt
    if errorlevel 1 (
        echo.
        echo  Nao consegui instalar o PySide6. Veja a mensagem acima.
        pause
        exit /b 1
    )
)

%PY% AnimadorApp.py
if errorlevel 1 pause
