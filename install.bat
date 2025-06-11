@echo off
REM Smartcard Management Tool - Windows Installation Script
REM This script automates the installation process on Windows

echo ============================================================
echo   Smartcard Management Tool - Windows Installation
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Checking version...
python -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.7 or higher is required
    python --version
    pause
    exit /b 1
)

echo Python version is compatible.
echo.

REM Run the Python installation script
echo Running Python installation script...
python install.py

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed. Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Installation completed successfully!
echo ============================================================
echo.
echo You can now use the tool with:
echo   python ccm_tool.py --help
echo.
echo Press any key to continue...
pause >nul
