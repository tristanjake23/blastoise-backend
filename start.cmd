@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe scripts\check_connection.py
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
exit /b
:failure
pause
exit /b 1
