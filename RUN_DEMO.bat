@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\run_demo.py
  if errorlevel 1 exit /b 1
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 scripts\run_demo.py
  if errorlevel 1 exit /b 1
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)

python scripts\run_demo.py
if errorlevel 1 exit /b 1
exit /b 0
