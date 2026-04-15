#!/bin/bash
# start.sh — Quick start script for MRJ3.0

set -e

echo "🚀 MRJ3.0 Quick Start"
echo "=================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install from python.org"
    exit 1
fi

PYTHON=$(which python3)
echo "✅ Python: $PYTHON"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

echo ""
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "⚙️  Setting up SAM2..."
python setup_sam2.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ Setup complete!"
    echo ""
    echo "Starting Flask app on http://localhost:5000"
    echo ""
    python app.py
else
    echo ""
    echo "❌ Setup failed. Check errors above."
    exit 1
fi
