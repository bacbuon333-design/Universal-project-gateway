@echo off
setlocal
cd /d "%~dp0"

echo [DOCTOR 1/2] Locating an existing Python 3.11 or newer runtime...
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
if exist ".venv\Scripts\python.exe" (
  set "UPG_PYTHON=.venv\Scripts\python.exe"
  goto run_doctor
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    set "UPG_PYTHON=py -3.11"
    goto run_doctor
  )
)
where python >nul 2>nul
if errorlevel 1 goto python_missing
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 goto python_missing
set "UPG_PYTHON=python"

:run_doctor
echo [DOCTOR 2/2] Running read-only Gateway diagnostics...
%UPG_PYTHON% -m universal_project_gateway.cli --root "%CD%" doctor
if errorlevel 1 (
  echo [DOCTOR] FAILED. Review the structured checks above. 1>&2
  exit /b 1
)
echo [DOCTOR] COMPLETED without failing checks.
exit /b 0

:python_missing
echo [DOCTOR] FAILED: Python 3.11 or newer was not found. 1>&2
exit /b 1
