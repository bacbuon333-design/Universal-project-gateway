@echo off
setlocal
cd /d "%~dp0"

set "TRANSPORT=%~1"
if "%TRANSPORT%"=="" set "TRANSPORT=stdio"

if /i not "%TRANSPORT%"=="stdio" (
  echo ERROR: This MVP supports only the local stdio transport. 1>&2
  exit /b 2
)

echo Starting Universal Project Gateway with transport: %TRANSPORT%

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
  if errorlevel 1 exit /b 1
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
  if errorlevel 1 exit /b 1
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)

python -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
if errorlevel 1 exit /b 1
exit /b 0
