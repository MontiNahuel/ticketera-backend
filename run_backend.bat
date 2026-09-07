@echo off
title Ticketera Backend (FastAPI)
cd /d %~dp0
echo ==========================================
echo   Iniciando Ticketera Backend (FastAPI)
echo   Documentacion: http://localhost:8000/docs
echo   Health check:  http://localhost:8000/health
echo ==========================================
venv\Scripts\uvicorn.exe src.main:app --reload --port 8000
pause
