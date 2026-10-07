@echo off@echo off
REM Arranca Sentinel en la red local (Windows, doble clic).
REM Para HTTPS (camara en el celular) usa:  iniciar-https.bat
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo No se encontro 'uv'. Instalalo desde https://docs.astral.sh/uv/
    pause
    exit /b 1
)

echo Instalando dependencias...
call uv sync

set PORT=5000
call uv run python servidor.py
endlocal