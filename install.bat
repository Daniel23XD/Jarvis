@echo off
chcp 65001 >nul 2>&1
title JARVIS - Instalador

echo.
echo ============================================
echo   INSTALADOR DE J.A.R.V.I.S.
echo ============================================
echo.

REM ─── Check Python ───
echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ❌ Python NO esta instalado.
    echo   Descargalo de: https://www.python.org/downloads/
    echo   IMPORTANTE: Marca la casilla "Add Python to PATH"
    echo.
    pause
    exit /b
)
echo   ✅ Python encontrado
echo.

REM ─── Install Python dependencies ───
echo [2/3] Instalando dependencias de Python...
pip install -r "%~dp0requirements.txt" --quiet
if errorlevel 1 (
    echo   ❌ Error instalando dependencias
    pause
    exit /b
)
echo   ✅ Dependencias instaladas
echo.

REM ─── Check Ollama ───
echo [3/3] Verificando Ollama...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ❌ Ollama NO esta instalado.
    echo   Descargalo de: https://ollama.com/download
    echo   Instala Ollama y ejecuta este script otra vez.
    echo.
    pause
    exit /b
)
echo   ✅ Ollama encontrado
echo.

REM ─── Pull model ───
echo ============================================
echo   Descargando modelo de IA...
echo   (Esto puede tomar varios minutos
echo    dependiendo de tu internet)
echo ============================================
echo.
ollama pull llama3.1:8b

echo.
echo ============================================
echo   ✅ INSTALACION COMPLETA
echo.
echo   Para iniciar JARVIS ejecuta:
echo     start.bat
echo ============================================
echo.
pause
