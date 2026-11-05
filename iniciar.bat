@echo off
title 71 BI Mtz - Sistema de Controle de Acesso
color 0A
echo.
echo  ==========================================
echo   71 BATALHAO DE INFANTARIA MOTORIZADO
echo   Sistema de Controle de Acesso de Civis
echo  ==========================================
echo.
echo  Iniciando o sistema...
echo.

cd /d "%~dp0"

REM Tenta py, depois python
py app.py 2>nul
if errorlevel 1 (
    python app.py 2>nul
    if errorlevel 1 (
        echo.
        echo  ERRO: Python nao encontrado.
        echo  Instale em: https://www.python.org/downloads/
        echo  (marque "Add Python to PATH" na instalacao)
        echo.
        pause
    )
)
