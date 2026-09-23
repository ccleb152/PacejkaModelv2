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

REM Always call the venv's own python.exe by its full path rather than
REM relying on "call activate.bat" + bare "pip"/"streamlit" commands.
REM Activation only works by adjusting PATH, and on some Windows Python
REM installs (seen with a per-user "PythonCore" install where pip's own
REM bootstrap silently failed during venv creation) that leaves "pip" and
REM "streamlit" resolving to a *different*, global Python instead of this
REM project's isolated one -- with no error, just packages landing in the
REM wrong place and "streamlit is not recognized" when it's time to run.
REM Invoking ".venv\Scripts\python.exe" directly can't be redirected like
REM that: it's an unambiguous path to this project's own interpreter.
set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo.
    echo The virtual environment looks incomplete -- %VENV_PY% is missing.
    echo Delete the .venv folder next to this script and double-click it
    echo again to rebuild it from scratch.
    echo.
    pause
    exit /b 1
)

echo Checking dependencies...
"%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
"%VENV_PY%" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Check your internet connection and try again.
    pause
    exit /b 1
)

echo Starting the app -- it will open in your browser...
"%VENV_PY%" -m streamlit run app\streamlit_app.py

echo.
echo The app has closed. Press any key to close this window.
pause >nul
