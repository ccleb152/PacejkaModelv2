#!/bin/bash
# Double-click launcher for the Pacejka tire-fitting app (Linux).
# First run: creates a local virtual environment and installs
# dependencies. Every run after that: just launches the app.
#
# NOTE: double-click support depends on your file manager. If
# double-clicking just opens this file in a text editor, either enable
# "Allow executing file as program" in its file properties, or run it
# once from a terminal (`./run_linux.sh`) after `chmod +x run_linux.sh`.

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo ""
    echo "Python 3 was not found on this computer. Install it with your"
    echo "distribution's package manager (e.g. sudo apt install python3 python3-venv) then try again."
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

source .venv/bin/activate

echo "Checking dependencies..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "Failed to install dependencies. Check your internet connection and try again."
    read -p "Press Enter to close this window..."
    exit 1
fi

echo "Starting the app -- it will open in your browser..."
streamlit run app/streamlit_app.py

echo ""
echo "The app has closed."
read -p "Press Enter to close this window..."
