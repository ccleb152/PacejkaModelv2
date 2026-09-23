#!/bin/bash
# Double-click launcher for the Pacejka tire-fitting app (macOS).
# First run: creates a local virtual environment and installs
# dependencies. Every run after that: just launches the app.
# No terminal typing required -- just double-click this file.
#
# NOTE: the first time you double-click this, macOS may say it's from
# an "unidentified developer" and refuse to open it. If so: right-click
# (or Control-click) this file -> Open -> Open, once. After that,
# double-clicking works normally.

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "Python 3 was not found on this computer."
    echo "Install it from https://www.python.org/downloads/ then try again."
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Setting up the app for the first time -- this can take a minute..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo ""
        echo "Failed to create the Python environment. See the message above."
        read -p "Press Enter to close this window..."
        exit 1
    fi
fi

# Always call the venv's own python by its full path rather than "source
# activate" + bare "pip"/"streamlit" commands -- activation only works by
# adjusting PATH, and if a venv's pip bootstrap silently failed (rare, but
# possible on some Python installs), bare commands can quietly resolve to
# a different, global Python with no error, until "streamlit" turns up
# missing when it's time to run. ".venv/bin/python" is an unambiguous path
# to this project's own interpreter -- it can't be redirected like that.
VENV_PY=".venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo ""
    echo "The virtual environment looks incomplete -- $VENV_PY is missing."
    echo "Delete the .venv folder next to this script and double-click it"
    echo "again to rebuild it from scratch."
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
fi

echo "Checking dependencies..."
"$VENV_PY" -m ensurepip --upgrade >/dev/null 2>&1
"$VENV_PY" -m pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "Failed to install dependencies. Check your internet connection and try again."
    read -p "Press Enter to close this window..."
    exit 1
fi

echo "Starting the app -- it will open in your browser..."
"$VENV_PY" -m streamlit run app/streamlit_app.py

echo ""
echo "The app has closed."
read -p "Press Enter to close this window..."
