@echo off
REM Double-click launcher for the Pacejka tire-fitting app (Windows).
REM First run: creates a local virtual environment and installs
REM dependencies. Every run after that: just launches the app.
REM No terminal typing required -- just double-click this file.

setlocal
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python"
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set "PYTHON=py -3"
    ) else (
        echo.
        echo Python was not found on this computer.
        echo Install Python 3.11 or later from https://www.python.org/downloads/
        echo During install, make sure to check "Add python.exe to PATH".
        echo Then double-click this file again.
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv" (
    echo Setting up the app for the first time -- this can take a minute...
    %PYTHON% -m venv .venv
    if errorlevel 1 (
        echo.
        echo Failed to create the Python environment. See the message above.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Checking dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting the app -- it will open in your browser...
streamlit run app\streamlit_app.py

echo.
echo The app has closed. Press any key to close this window.
pause >nul
