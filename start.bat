@echo off
cd /d "%~dp0"
title MRJ3.0 — Mr. Jealousy

REM ── Kill any existing Python server ─────────────────────────
echo Checking for running Python processes...
taskkill /f /im python.exe >nul 2>&1
if errorlevel 1 (
    echo No existing Python process found.
) else (
    echo Stopped previous Python process.
    timeout /t 1 /nobreak >nul
)

REM ── Install / verify dependencies ────────────────────────────
echo Installing / verifying dependencies...
python -m pip install -r requirements.txt --quiet --no-warn-script-location
if errorlevel 1 (
    echo WARNING: pip install reported issues. Attempting to continue...
)

REM ── Start Flask server ───────────────────────────────────────
REM  .env is loaded by load_dotenv() inside app.py — no batch parsing needed.
echo.
echo ============================================================
echo   MRJ3.0 is starting op http://localhost:5000
echo   Open je browser en ga naar http://localhost:5000
echo   Druk Ctrl+C om de server te stoppen.
echo ============================================================
echo.
python app.py

pause
