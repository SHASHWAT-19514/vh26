@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
if not defined ABHEDYA_START_DATASET set ABHEDYA_START_DATASET=full-real
python -m abhedya serve --host 127.0.0.1 --port 8000
