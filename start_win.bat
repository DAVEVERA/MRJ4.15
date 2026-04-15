@echo off
REM start_win.bat — Quick start script for Windows

setlocal enabledelayedexpansion

echo 🚀 MRJ3.0 Quick Start (Windows)
echo ==================================

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Install from python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo ✅ %PYVER%

REM Check if venv exists
if not exist "venv" (
    echo.
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

echo.
echo 📥 Installing dependencies...
pip install -q -r requirements.txt

echo.
echo ⚙️  Setting up SAM2...
python setup_sam2.py

if %errorlevel% equ 0 (
    echo.
    echo ==================================
    echo ✅ Setup complete!
    echo.
    echo Starting Flask app on http://localhost:5000
    echo.
    python app.py
) else (
    echo.
    echo ❌ Setup failed. Check errors above.
    pause
    exit /b 1
)
