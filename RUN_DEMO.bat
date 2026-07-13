@echo off
setlocal
cd /d "%~dp0"

echo [DEMO 1/2] Locating an existing Python 3.11 or newer runtime...

if exist ".venv\Scripts\python.exe" (
  echo [DEMO 2/2] Running the deterministic Gateway demo...
  ".venv\Scripts\python.exe" scripts\run_demo.py
  if errorlevel 1 goto demo_failed
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  echo [DEMO 2/2] Running the deterministic Gateway demo...
  py -3.11 scripts\run_demo.py
  if errorlevel 1 goto demo_failed
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)

echo [DEMO 2/2] Running the deterministic Gateway demo...
python scripts\run_demo.py
if errorlevel 1 goto demo_failed
exit /b 0

:demo_failed
echo [DEMO] FAILED. 1>&2
exit /b 1
