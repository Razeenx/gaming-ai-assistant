@echo off
REM Local Development Server Launcher
REM This script helps run both backend and frontend in development mode

echo.
echo ===============================================
echo Gaming AI Assistant - Local Development Server
echo ===============================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo ⚠️  Please update .env with your GROQ_API_KEY
    echo Found .env file - edit it with your actual API keys
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js 16+
    pause
    exit /b 1
)

echo ✓ Python found
echo ✓ Node.js found
echo.

REM Setup Python
if not exist .venv (
    echo Creating Python virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -r requirements.txt -q

echo.
echo ===============================================
echo Starting servers...
echo ===============================================
echo.
echo Backend will run on: http://127.0.0.1:8000
echo Frontend will run on: http://127.0.0.1:5173
echo.
echo To stop servers, press Ctrl+C in this window
echo.

REM Start backend in background
echo Starting backend...
start cmd /k "python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

REM Wait a bit for backend to start
timeout /t 2 /nobreak

REM Start frontend
echo Starting frontend...
cd frontend
call npm install -q
npm run dev

pause
