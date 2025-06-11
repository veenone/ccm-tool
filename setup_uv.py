#!/usr/bin/env python3
"""
Setup script for Smartcard Management Tool using uv for dependency management.
This script automates the installation of uv and project dependencies.
"""

import os
import sys
import subprocess
import platform
import urllib.request
import tempfile
from pathlib import Path


def print_banner():
    """Print installation banner"""
    print("=" * 70)
    print("  Smartcard Management Tool - UV Setup Script")
    print("=" * 70)
    print()


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_uv_installed():
    """Check if uv is already installed"""
    try:
        result = subprocess.run(["uv", "--version"], 
                               capture_output=True, text=True, check=True)
        print(f"✅ UV found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("📦 UV not found, will install...")
        return False


def install_uv():
    """Install uv package manager"""
    system = platform.system().lower()
    
    print("🔧 Installing uv...")
    
    try:
        if system == "windows":
            # Install uv on Windows using PowerShell
            cmd = [
                "powershell", "-Command",
                "irm https://astral.sh/uv/install.ps1 | iex"
            ]
            subprocess.run(cmd, check=True)
        else:
            # Install uv on Unix-like systems
            cmd = ["curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"]
            subprocess.run(" ".join(cmd), shell=True, check=True)
        
        print("✅ UV installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing uv: {e}")
        print("Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/")
        return False


def check_pcsc_middleware():
    """Check if PC/SC middleware is available"""
    system = platform.system().lower()
    
    print(f"🔍 Checking PC/SC middleware on {system}...")
    
    if system == "windows":
        print("✅ Windows WinSCard should be available")
        return True
    elif system == "linux":
        try:
            subprocess.run(["pcscd", "--version"], 
                         capture_output=True, check=True)
            print("✅ PC/SC Lite found")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  PC/SC Lite not found. Install with:")
            print("   sudo apt-get install pcscd pcsc-tools")
            print("   sudo yum install pcsc-lite pcsc-tools")
            return False
    elif system == "darwin":
        print("✅ macOS PC/SC framework should be available")
        return True
    else:
        print(f"⚠️  Unknown system: {system}")
        return False


def setup_project():
    """Set up the project with uv"""
    print("📦 Setting up project with uv...")
    
    try:
        # Initialize the project (if not already done)
        if not Path("pyproject.toml").exists():
            print("Initializing new uv project...")
            subprocess.run(["uv", "init"], check=True)
        
        # Sync dependencies
        print("Installing dependencies...")
        subprocess.run(["uv", "sync"], check=True)
        
        print("✅ Project setup completed")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up project: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    directories = ["logs", "output", "output/demo", "output/custom_demo"]
    
    print("📁 Creating directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   Created: {directory}")
    
    print("✅ Directories created")


def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    try:
        # Test running with uv
        result = subprocess.run([
            "uv", "run", "python", "-c",
            "import sys; sys.path.insert(0, 'src'); "
            "from src.smartcard_manager import SmartcardManager; "
            "from src.config_manager import ConfigManager; "
            "print('✅ All modules imported successfully')"
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout.strip())
        
        # Test PC/SC reader enumeration
        result = subprocess.run([
            "uv", "run", "python", "-c",
            "import sys; sys.path.insert(0, 'src'); "
            "from src.smartcard_manager import SmartcardManager; "
            "sc = SmartcardManager(); readers = sc.list_readers(); "
            f"print(f'✅ PC/SC interface working: {{len(readers)}} readers found')"
        ], capture_output=True, text=True, check=True)
        
        print(result.stdout.strip())
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Test error: {e}")
        print("stderr:", e.stderr)
        return False


def show_usage_examples():
    """Show usage examples with uv"""
    print("\n" + "=" * 70)
    print("  Usage Examples with UV")
    print("=" * 70)
    
    examples = [
        ("Activate virtual environment", "uv shell"),
        ("Run CLI tool directly", "uv run python ccm_tool.py --help"),
        ("Run GUI application", "uv run python gui_app.py"),
        ("List PC/SC readers", "uv run python ccm_tool.py list-readers"),
        ("Connect to reader", "uv run python ccm_tool.py connect \"Reader Name\""),
        ("Run examples", "uv run python examples/basic_example.py"),
        ("Run tests", "uv run python tests/test_main.py"),
        ("Install new dependency", "uv add <package-name>"),
        ("Update dependencies", "uv sync"),
    ]
    
    for description, command in examples:
        print(f"• {description}:")
        print(f"  {command}")
        print()
    
    print("🔗 UV Documentation: https://docs.astral.sh/uv/")


def main():
    """Main setup routine"""
    print_banner()
    
    # Check prerequisites
    if not check_python_version():
        return False
    
    # Install uv if needed
    if not check_uv_installed():
        if not install_uv():
            return False
        
        # Verify installation
        if not check_uv_installed():
            print("❌ UV installation verification failed")
            return False
    
    # Check PC/SC middleware
    if not check_pcsc_middleware():
        print("⚠️  PC/SC middleware issues detected, but continuing...")
    
    # Setup project
    if not setup_project():
        return False
    
    # Create directories
    create_directories()
    
    # Test installation
    if not test_installation():
        print("⚠️  Installation test had issues, but basic setup completed")
    
    # Success message
    print("\n" + "=" * 70)
    print("  ✅ UV setup completed successfully!")
    print("=" * 70)
    
    show_usage_examples()
    
    print("\n🎉 Ready to manage smartcards with UV!")
    print("\n💡 Quick start:")
    print("   uv shell                    # Activate environment")
    print("   uv run python ccm_tool.py --help  # Run CLI")
    print("   uv run python gui_app.py    # Run GUI")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)