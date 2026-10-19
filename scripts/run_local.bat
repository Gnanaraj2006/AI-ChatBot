@echo off
title StudySphere AI - Local Server Launcher
echo ====================================================
echo        StudySphere AI - Cloud Study Assistant
echo ====================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install dependencies if needed
echo [1/2] Verifying dependencies...
python -m pip install -r requirements.txt --quiet

REM Launch FastAPI Server
echo [2/2] Launching StudySphere AI on http://localhost:8000 ...
python run.py
pause
