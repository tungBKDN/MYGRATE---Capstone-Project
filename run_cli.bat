@echo off
:: Set current directory to the script's directory
cd /d "%~dp0"

:: Check and activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [MYGRATE] Activating virtual environment (.venv)...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo [MYGRATE] Activating virtual environment (venv)...
    call "venv\Scripts\activate.bat"
) else (
    echo [WARNING] Virtual environment folder (.venv or venv) not found in the project root.
    echo Attempting to run with the system Python default.
)

:: Run the interactive CLI application passing any additional arguments
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" cli_app.py %*
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" cli_app.py %*
) else (
    python cli_app.py %*
)

:: Pause at the end to keep the window open if double-clicked
if "%cmdcmdline:~0,2%"=="cmd" (
    echo.
    echo Press any key to exit...
    pause > nul
)
