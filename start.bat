@echo off
chcp 65001 >nul 2>&1
title J.A.R.V.I.S.

echo.
echo   Iniciando J.A.R.V.I.S...
echo.

REM ─── Start Ollama if not running ───
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul 2>&1
if errorlevel 1 (
    echo   Iniciando Ollama en segundo plano...
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul
)

REM ─── Start JARVIS ───
cd /d "%~dp0"
python run.py

pause
