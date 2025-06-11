#!/usr/bin/env python3
"""
Installation and setup script for the Smartcard Management Tool.
This script helps users set up the environment and dependencies.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def print_banner():
    """Print installation banner"""
    print("=" * 60)
    print("  Smartcard Management Tool - Installation Script")
    print("=" * 60)
    print()


def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_pcsc_middleware():
    """Check if PC/SC middleware is available"""
    system = platform.system().lower()
    
    print(f"🔍 Checking PC/SC middleware on {system}...")
    
    if system == "windows":
        # Windows has built-in WinSCard
        print("✅ Windows WinSCard should be available")
        return True
    elif system == "linux":
        # Check for pcscd
        try:
            subprocess.run(["pcscd", "--version"], 
                         capture_output=True, check=True)
            print("✅ PC/SC Lite found")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  PC/SC Lite not found. Install with:")
            print("   sudo apt-get install pcscd pcsc-tools")  # Debian/Ubuntu
            print("   sudo yum install pcsc-lite pcsc-tools")   # RHEL/CentOS
            return False
    elif system == "darwin":
        # macOS has built-in PC/SC framework
        print("✅ macOS PC/SC framework should be available")
        return True
    else:
        print(f"⚠️  Unknown system: {system}")
        return False


def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    try:
        # Upgrade pip first
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True)
        
        # Install requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
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
        # Test imports
        sys.path.insert(0, "src")
        
        from src.smartcard_manager import SmartcardManager
        from src.config_manager import ConfigManager
        from src.globalplatform import GlobalPlatformManager
        from src.secure_channel import SecureChannelManager
        from src.visualization import SecurityDomainVisualizer
        
        print("✅ All modules imported successfully")
        
        # Test configuration loading
        config_manager = ConfigManager()
        keysets = config_manager.list_keysets()
        print(f"✅ Configuration loaded: {len(keysets)} keysets found")
        
        # Test PC/SC reader enumeration
        sc_manager = SmartcardManager()
        readers = sc_manager.list_readers()
        print(f"✅ PC/SC interface working: {len(readers)} readers found")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def show_usage_examples():
    """Show usage examples"""
    print("\n" + "=" * 60)
    print("  Usage Examples")
    print("=" * 60)
    
    examples = [
        ("List PC/SC readers", "python ccm_tool.py list-readers"),
        ("Connect to a reader", "python ccm_tool.py connect \"Reader Name\""),
        ("List keysets", "python ccm_tool.py list-keysets"),
        ("Establish secure channel", "python ccm_tool.py establish-secure-channel default_scp03"),
        ("List security domains", "python ccm_tool.py list-security-domains"),
        ("List applications", "python ccm_tool.py list-applications"),
        ("Generate visualizations", "python ccm_tool.py visualize"),
        ("Show help", "python ccm_tool.py --help"),
    ]
    
    for description, command in examples:
        print(f"• {description}:")
        print(f"  {command}")
        print()
    
    print("For more examples, check the 'examples/' directory:")
    print("• python examples/basic_example.py")
    print("• python examples/advanced_example.py")
    print("• python examples/visualization_demo.py")


def main():
    """Main installation routine"""
    print_banner()
    
    # Check prerequisites
    if not check_python_version():
        return False
    
    if not check_pcsc_middleware():
        print("⚠️  PC/SC middleware issues detected, but continuing...")
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Create directories
    create_directories()
    
    # Test installation
    if not test_installation():
        print("❌ Installation test failed")
        return False
    
    # Success message
    print("\n" + "=" * 60)
    print("  ✅ Installation completed successfully!")
    print("=" * 60)
    
    show_usage_examples()
    
    print("\n🎉 Ready to manage smartcards!")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
