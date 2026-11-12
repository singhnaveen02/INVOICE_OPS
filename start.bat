@echo off
setlocal enabledelayedexpansion

echo =========================================================
echo       InvoiceOps - AI-Powered Invoice Processing
echo =========================================================
echo.

REM 1. Check Python
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PY_CMD=py -3.10
) else (
    set PY_CMD=python
)

REM 2. Start Backend
echo [1/2] Starting InvoiceOps FastAPI Backend on http://localhost:8000...
start "InvoiceOps Backend API" cmd /k "cd /d "%~dp0backend" && if not exist venv (C:\Users\singh\AppData\Local\Programs\Python\Python310\python.exe -m venv venv && venv\Scripts\pip install -r requirements.txt -q) && call venv\Scripts\activate && python init_db.py && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000"

echo Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak > nul

REM 3. Start Frontend
echo [2/2] Starting InvoiceOps React + Vite Frontend on http://localhost:5173...
start "InvoiceOps React Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo =========================================================
echo  InvoiceOps is launching!
echo  - Frontend UI:  http://localhost:5173
echo  - Backend API:  http://localhost:8000
echo  - Interactive Swagger Docs: http://localhost:8000/docs
echo =========================================================
echo.
pause
