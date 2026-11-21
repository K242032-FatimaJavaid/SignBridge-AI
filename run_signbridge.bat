@echo off
setlocal

title SignBridge AI

cd /d "%~dp0"

echo ==========================================
echo          SIGNBRIDGE AI
echo ==========================================
echo.

where npm >nul 2>&1

if errorlevel 1 (
    echo ERROR: Node.js/npm is not installed.
    echo Install Node.js and reopen PowerShell.
    pause
    exit /b 1
)

if not exist "avatar-engine\package.json" (
    echo ERROR: avatar-engine folder is missing.
    pause
    exit /b 1
)

echo Checking avatar dependencies...

pushd avatar-engine

if not exist "node_modules" (
    echo Installing avatar dependencies...
    call npm ci

    if errorlevel 1 (
        echo ERROR: npm installation failed.
        popd
        pause
        exit /b 1
    )
)

echo Building avatar signing engine...

call npm run build

if errorlevel 1 (
    echo ERROR: avatar build failed.
    popd
    pause
    exit /b 1
)

popd

echo.
echo Starting SignBridge AI dashboard...
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)

pause
