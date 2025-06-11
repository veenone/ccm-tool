#!/bin/bash
# Smartcard Management Tool - UV Setup Script for Unix/Linux/macOS
# This script automates the installation of UV and project setup

set -e  # Exit on any error

echo "======================================================================"
echo "  Smartcard Management Tool - UV Setup for Unix/Linux/macOS"
echo "======================================================================"
echo

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager or https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "❌ ERROR: Python 3.8 or higher is required"
    echo "Current version: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version: $PYTHON_VERSION"
echo

# Check if UV is installed
echo "Checking for UV..."
if command -v uv &> /dev/null; then
    echo "✅ UV is already installed: $(uv --version)"
else
    echo "📦 UV not found. Installing UV..."
    
    # Install UV
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add UV to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Verify installation
    if command -v uv &> /dev/null; then
        echo "✅ UV installed successfully: $(uv --version)"
    else
        echo "❌ ERROR: UV installation failed"
        echo "Please install UV manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

echo

# Run the Python setup script
echo "Running Python setup script with UV..."
python3 setup_uv.py

echo
echo "======================================================================"
echo "  Setup completed successfully!"
echo "======================================================================"
echo
echo "You can now use the tool with UV:"
echo "  source ~/.local/bin/env      # Add UV to PATH (if needed)"
echo "  uv shell                     # Activate environment"
echo "  uv run python ccm_tool.py --help  # CLI tool"
echo "  uv run python gui_app.py    # GUI application"
echo
echo "🎉 Ready to manage smartcards with UV!"