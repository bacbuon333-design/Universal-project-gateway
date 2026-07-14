@echo off
setlocal
cd /d "%~dp0"

echo [VERIFY 1/11] Locating Python 3.11 or newer...
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
"%PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo ERROR: The selected virtual environment does not use Python 3.11 or newer. 1>&2
  exit /b 1
)

echo [VERIFY 2/11] Installing pinned project and development dependencies...
"%PYTHON%" -m pip install -r requirements.lock
if errorlevel 1 exit /b %ERRORLEVEL%
"%PYTHON%" -m pip install --no-deps -e ".[dev]"
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 3/11] Running lint checks...
"%PYTHON%" -m ruff check src scripts tests
if errorlevel 1 exit /b %ERRORLEVEL%
"%PYTHON%" -m compileall -q src scripts tests
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 4/11] Verifying project manifests...
"%PYTHON%" scripts\verify_manifest.py PROJECT_MANIFEST.yaml fixtures\python_demo\PROJECT_MANIFEST.yaml fixtures\node_demo\PROJECT_MANIFEST.yaml
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 5/11] Running unit and integration tests...
"%PYTHON%" -m pytest tests\unit tests\integration
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 6/11] Running security tests...
"%PYTHON%" -m pytest tests\security
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 7/11] Running the first end-to-end demo...
"%PYTHON%" scripts\run_demo.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 8/11] Running the second end-to-end demo...
"%PYTHON%" scripts\run_demo.py
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 9/11] Verifying the latest evidence bundle...
"%PYTHON%" scripts\verify_gateway.py --latest
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 10/11] Checking patch whitespace...
where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git is required for complete verification. 1>&2
  exit /b 1
)
git diff --check
if errorlevel 1 exit /b %ERRORLEVEL%

echo [VERIFY 11/11] Universal Project Gateway verification PASSED.
exit /b 0
