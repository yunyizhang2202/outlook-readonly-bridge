@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
where py >nul 2>&1
if errorlevel 1 goto usepython
py -3 -m venv .venv
goto install
:usepython
python -m venv .venv
:install
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" check.py
exit /b %errorlevel%

