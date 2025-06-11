#!/usr/bin/env python3
"""
Test installation of all dependencies and core modules.
"""

def test_dependencies():
    """Test that all dependencies are properly installed."""
    try:
        # Test GUI dependencies
        import customtkinter as ctk
        print("✅ CustomTkinter imported successfully")
        
        from PIL import Image, ImageTk
        print("✅ PIL/Pillow imported successfully")
          # Test smartcard dependencies
        import smartcard
        print("✅ PySCard (smartcard module) imported successfully")
        
        from smartcard.util import toHexString
        print("✅ Smartcard utilities imported successfully")
        
        # Test other dependencies
        import click
        print("✅ Click imported successfully")
        
        import colorama
        print("✅ Colorama imported successfully")
        
        import matplotlib
        print("✅ Matplotlib imported successfully")
        
        import networkx
        print("✅ NetworkX imported successfully")
        
        import yaml
        print("✅ PyYAML imported successfully")
        
        import cryptography
        print("✅ Cryptography imported successfully")
        
        # Test core modules
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from src.smartcard_manager import SmartcardManager
        print("✅ SmartcardManager imported successfully")
        
        from src.globalplatform import GlobalPlatformManager
        print("✅ GlobalPlatformManager imported successfully")
        
        from src.config_manager import ConfigManager
        print("✅ ConfigManager imported successfully")
        
        from src.visualization import VisualizationGenerator
        print("✅ VisualizationGenerator imported successfully")
        
        print("\n🎉 All dependencies and modules imported successfully!")
        print("The smartcard management tool is ready to use.")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_gui_creation():
    """Test that the GUI can be created without errors."""
    try:
        import customtkinter as ctk
        
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create a simple test window
        root = ctk.CTk()
        root.title("Test Window")
        root.geometry("200x100")
        
        label = ctk.CTkLabel(root, text="GUI Test")
        label.pack(pady=20)
        
        # Don't show the window, just test creation
        root.withdraw()
        root.destroy()
        
        print("✅ GUI framework test passed")
        return True
        
    except Exception as e:
        print(f"❌ GUI test error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Smartcard Management Tool Installation")
    print("=" * 50)
    
    deps_ok = test_dependencies()
    gui_ok = test_gui_creation()
    
    if deps_ok and gui_ok:
        print("\n🎉 Installation test completed successfully!")
        print("\nYou can now run:")
        print("  uv run python ccm_tool.py --help      # CLI interface")
        print("  uv run python gui_app.py              # GUI interface")
    else:
        print("\n❌ Installation test failed. Please check the errors above.")
