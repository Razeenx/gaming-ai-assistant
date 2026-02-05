#!/bin/bash

# Local Development Server Launcher for Linux/Mac
# This script helps run both backend and frontend in development mode

echo ""
echo "==============================================="
echo "Gaming AI Assistant - Local Development Server"
echo "==============================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please update .env with your GROQ_API_KEY"
    echo "Found .env file - edit it with your actual API keys"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found! Please install Python 3.8+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found! Please install Node.js 16+"
    exit 1
fi

echo "✓ Python 3 found"
echo "✓ Node.js found"
echo ""

# Setup Python
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt -q

echo ""
echo "==============================================="
echo "Starting servers..."
echo "==============================================="
echo ""
echo "Backend will run on: http://127.0.0.1:8000"
echo "Frontend will run on: http://127.0.0.1:5173"
echo ""
echo "To stop servers, press Ctrl+C"
echo ""

# Start backend in background
echo "Starting backend..."
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo "Starting frontend..."
cd frontend
npm install -q 2>/dev/null || true
npm run dev

# Cleanup
kill $BACKEND_PID 2>/dev/null || true
