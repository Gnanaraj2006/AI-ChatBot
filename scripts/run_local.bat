@echo off
title StudySphere AI - Local Server Launcher
echo ====================================================
echo        StudySphere AI - Cloud Study Assistant
echo ====================================================
echo.

REM Find Python executable
set "PY_CMD=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
    ) else (
        echo [ERROR] Python is not installed or not in PATH.
        pause
        exit /b 1
    )
)

REM Install dependencies if needed
echo [1/2] Verifying dependencies...
%PY_CMD% -m pip install -r requirements.txt --quiet

REM Launch FastAPI Server
echo [2/2] Launching StudySphere AI on http://localhost:8000 ...
%PY_CMD% run.py
pause
