@echo off
setlocal
cd /d "%~dp0"

:: ── Backend ──────────────────────────────────────────────────────────────
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
if not defined ABHEDYA_START_DATASET set ABHEDYA_START_DATASET=full-real

start "Abhedya Backend" cmd /k "python -m abhedya serve --host 127.0.0.1 --port 8000"

:: ── Frontend ─────────────────────────────────────────────────────────────
start "Abhedya Frontend" cmd /k "cd /d "%~dp0frontend" & npm run dev"
