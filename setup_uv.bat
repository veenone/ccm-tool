@echo off
REM Smartcard Management Tool - UV Setup Script for Windows
REM This script automates the installation of UV and project setup

echo ======================================================================
echo   Smartcard Management Tool - UV Setup for Windows
echo ======================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Checking version...
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.8 or higher is required
    python --version
    pause
    exit /b 1
)

echo Python version is compatible.
echo.

REM Check if UV is already installed
echo Checking for UV...
uv --version >nul 2>&1
if errorlevel 1 (
    echo UV not found. Installing UV...
    echo.
    
    REM Install UV using PowerShell
    powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
    
    if errorlevel 1 (
        echo ERROR: Failed to install UV
        echo Please install UV manually: https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
    
    REM Add UV to PATH for current session
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    
    echo UV installed successfully.
) else (
    echo UV is already installed.
)

echo.

REM Run the Python setup script
echo Running Python setup script with UV...
python setup_uv.py

if errorlevel 1 (
    echo.
    echo ERROR: Setup failed. Check the output above for details.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo   Setup completed successfully!
echo ======================================================================
echo.
echo You can now use the tool with UV:
echo   uv shell                         # Activate environment
echo   uv run python ccm_tool.py --help # CLI tool
echo   uv run python gui_app.py         # GUI application
echo.
echo Press any key to continue...
pause >nul