@echo off
setlocal
cd /d "%~dp0"

echo [PULL 1/5] Checking Git availability...
where git >nul 2>nul
if errorlevel 1 goto git_missing
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto not_repository

echo [PULL 2/5] Refusing a dirty working tree...
set "DIRTY_TREE="
for /f "delims=" %%A in ('git status --porcelain --untracked-files^=normal 2^>nul') do set "DIRTY_TREE=1"
if defined DIRTY_TREE goto dirty_tree

echo [PULL 3/5] Confirming the checked-out branch is main...
for /f "delims=" %%B in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%B"
if /i not "%CURRENT_BRANCH%"=="main" goto wrong_branch

echo [PULL 4/5] Pulling origin/main with fast-forward only...
git pull --ff-only origin main
if errorlevel 1 goto pull_failed

echo [PULL 5/5] Running the complete Gateway verification...
call VERIFY_GATEWAY.bat
if errorlevel 1 goto verify_failed

echo [PULL] PASSED: origin/main was pulled and verified.
exit /b 0

:git_missing
echo [PULL] FAILED: Git is required. 1>&2
exit /b 1
:not_repository
echo [PULL] FAILED: The script directory is not a Git worktree. 1>&2
exit /b 1
:dirty_tree
echo [PULL] REFUSED: The working tree is dirty. Commit or preserve changes first. 1>&2
exit /b 2
:wrong_branch
echo [PULL] REFUSED: This helper only updates main; current branch is "%CURRENT_BRANCH%". 1>&2
exit /b 2
:pull_failed
echo [PULL] FAILED: git pull --ff-only origin main did not complete. 1>&2
exit /b 1
:verify_failed
echo [PULL] FAILED: VERIFY_GATEWAY.bat reported an error. 1>&2
exit /b 1
