#!/bin/bash
# Script to run Q-Wave GUI using system Python (with Tkinter) and venv packages

cd "$(dirname "$0")"

# Use system Python which has Tkinter support
SYSTEM_PYTHON=/usr/bin/python3

# Check if system Python has Tkinter
if ! "$SYSTEM_PYTHON" -c "import tkinter" 2>/dev/null; then
    echo "Error: System Python does not have Tkinter support."
    echo "Please install python-tk: brew install python-tk"
    exit 1
fi

# Add virtual environment packages to Python path
VENV_PACKAGES="$(pwd)/venv/lib/python3.12/site-packages"
export PYTHONPATH="$VENV_PACKAGES:$PYTHONPATH"

# Check if required packages are available
if ! "$SYSTEM_PYTHON" -c "import qiskit, librosa, numpy, scipy, soundfile, pygame" 2>/dev/null; then
    echo "Warning: Some packages may not be compatible with system Python 3.9"
    echo "Attempting to run anyway..."
fi

# Run the GUI application
exec "$SYSTEM_PYTHON" qwave_gui.py

