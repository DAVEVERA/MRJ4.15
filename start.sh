#!/bin/bash
# start.sh — Quick start script for MRJ3.0
#
# Note: venv lives in ~/mrj_venv (not on the USB drive) because
# exFAT filesystems do not support the symlinks Python venv requires.

set -e

VENV="$HOME/mrj_venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "MRJ3.0 Quick Start"
echo "=================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Install from python.org"
    exit 1
fi
echo "Python: $(python3 --version)"

# Create venv if missing
if [ ! -d "$VENV" ]; then
    echo ""
    echo "Creating virtual environment at $VENV ..."
    python3 -m venv "$VENV"
fi

# Activate venv
source "$VENV/bin/activate"

echo ""
echo "Installing / updating dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setting up SAM2..."
python "$SCRIPT_DIR/setup_sam2.py"

echo ""
echo "=================================="
echo "Setup complete — starting Flask on http://localhost:5000"
echo ""
python "$SCRIPT_DIR/app.py"
