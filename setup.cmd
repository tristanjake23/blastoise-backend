@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failure
if not exist .env copy .env.example .env >nul
echo Open .env and fill in your keys sa supabase tol. Run doctor-publication.sql in Supabase.
pause
exit /b 0
:failure
echo Setup failed. Read the error above.
pause
exit /b 1
