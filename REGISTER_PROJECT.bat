@echo off
setlocal
cd /d "%~dp0"

set "MANIFEST=%~1"
if "%MANIFEST%"=="" set /p "MANIFEST=Path to PROJECT_MANIFEST.yaml: "

if "%MANIFEST%"=="" (
  echo ERROR: A manifest path is required. 1>&2
  exit /b 2
)

if not exist "%MANIFEST%" (
  echo ERROR: Manifest does not exist: "%MANIFEST%" 1>&2
  exit /b 2
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m universal_project_gateway.cli project register "%MANIFEST%"
  if errorlevel 1 exit /b 1
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3.11 -m universal_project_gateway.cli project register "%MANIFEST%"
  if errorlevel 1 exit /b 1
  exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.11 or newer was not found. 1>&2
  exit /b 1
)

python -m universal_project_gateway.cli project register "%MANIFEST%"
if errorlevel 1 exit /b 1
exit /b 0
