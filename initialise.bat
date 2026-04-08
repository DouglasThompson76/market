@echo off
setlocal

cd /d "%~dp0"

echo Initialising Market project environment...
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    echo Install Python 3.12+ and re-run this script.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo Reusing existing virtual environment in .venv...
)

echo.
echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    exit /b 1
)

echo.
echo Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo.
echo Environment ready.
echo.
echo PowerShell next steps:
echo   .\.venv\Scripts\Activate.ps1
echo   uvicorn app:app --reload
echo.
echo Or run without activating:
echo   .\.venv\Scripts\python.exe app.py

exit /b 0
