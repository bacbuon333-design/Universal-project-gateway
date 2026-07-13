@echo off
setlocal
cd /d "%~dp0"

echo [1/10] Locating Python 3.11 or newer...
if exist ".venv\Scripts\python.exe" goto venv_ready

where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -m venv .venv
  if not errorlevel 1 goto venv_ready
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)
python -m venv .venv
if errorlevel 1 exit /b %ERRORLEVEL%

:venv_ready
set "PYTHON=.venv\Scripts\python.exe"

echo [2/10] Installing pinned project and development dependencies...
"%PYTHON%" -m pip install -r requirements.lock
if errorlevel 1 exit /b %ERRORLEVEL%
"%PYTHON%" -m pip install --no-deps -e ".[dev]"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [3/10] Running lint checks...
"%PYTHON%" -m ruff check src scripts tests
if errorlevel 1 exit /b %ERRORLEVEL%
"%PYTHON%" -m compileall -q src scripts tests
if errorlevel 1 exit /b %ERRORLEVEL%

echo [4/10] Running unit and integration tests...
"%PYTHON%" -m pytest tests\unit tests\integration
if errorlevel 1 exit /b %ERRORLEVEL%

echo [5/10] Running security tests...
"%PYTHON%" -m pytest tests\security
if errorlevel 1 exit /b %ERRORLEVEL%

echo [6/10] Running the first end-to-end demo...
"%PYTHON%" scripts\run_demo.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [7/10] Running the second end-to-end demo...
"%PYTHON%" scripts\run_demo.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [8/10] Verifying the latest evidence bundle...
"%PYTHON%" scripts\verify_gateway.py --latest
if errorlevel 1 exit /b %ERRORLEVEL%

echo [9/10] Checking patch whitespace...
where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git is required for complete verification. 1>&2
  exit /b 1
)
git diff --check
if errorlevel 1 exit /b %ERRORLEVEL%

echo [10/10] Universal Project Gateway verification PASSED.
exit /b 0
