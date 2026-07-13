@echo off
setlocal
cd /d "%~dp0"

set "TRANSPORT=%~1"
if "%TRANSPORT%"=="" set "TRANSPORT=stdio"

if /i not "%TRANSPORT%"=="stdio" (
  echo ERROR: This MVP supports only the local stdio transport. 1>&2
  exit /b 2
)

echo [START 1/2] Locating an existing Python 3.11 or newer runtime...

if exist ".venv\Scripts\python.exe" (
  echo [START 2/2] Starting the local MCP stdio server...
  ".venv\Scripts\python.exe" -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
  if errorlevel 1 goto start_failed
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  echo [START 2/2] Starting the local MCP stdio server...
  py -3.11 -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
  if errorlevel 1 goto start_failed
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)

echo [START 2/2] Starting the local MCP stdio server...
python -m universal_project_gateway.mcp_server --transport "%TRANSPORT%"
if errorlevel 1 goto start_failed
exit /b 0

:start_failed
echo [START] FAILED: The MCP server exited with an error. 1>&2
exit /b 1
