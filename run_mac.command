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
#
# This project folder is meant to live inside a team-shared OneDrive
# folder (so everyone gets the app and the shared Feedback file via
# OneDrive sync, no git needed). That means anything written *inside*
# this folder gets uploaded to OneDrive and synced back down to every
# other teammate's Mac. A venv is the wrong thing for that: it's ~300MB
# of thousands of small files, and it bakes in an absolute path to one
# specific Python install, so it can't be reused on a different machine.
# If OneDrive synced one teammate's .venv onto another's Mac, it would
# look "already set up" but silently be broken.
#
# So the venv is created OUTSIDE this folder, under this account's local,
# per-machine Application Support directory, which OneDrive never syncs.
# Every teammate ends up with their own local venv built from their own
# Python install, and this synced folder only ever holds the app's
# source code and shared data.
VENV_DIR="$HOME/Library/Application Support/AlabamaFSAE-PacejkaModelv2/venv"

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "Python 3 was not found on this computer."
    echo "Install it from https://www.python.org/downloads/ then try again."
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up the app for the first time -- this can take a minute..."
    python3 -m venv "$VENV_DIR"
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
# missing when it's time to run. Invoking python's full path directly is
# an unambiguous path to this project's own interpreter -- it can't be
# redirected like that.
VENV_PY="$VENV_DIR/bin/python"

if [ ! -x "$VENV_PY" ]; then
    echo ""
    echo "The virtual environment looks incomplete -- $VENV_PY is missing."
    echo "Delete this folder and double-click this script again to rebuild"
    echo "it from scratch:"
    echo "  $VENV_DIR"
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
