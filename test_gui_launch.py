#!/usr/bin/env python3
"""
Test script to verify GUI application launches correctly
"""

import sys
import importlib.util

def test_gui_imports():
    """Test that GUI application can be imported successfully"""
    try:
        print("Testing GUI import...")
        import gui_app
        print("✅ GUI module imported successfully")
        
        # Test key components
        print("Testing component initialization...")
        
        # Test SmartcardGUI class exists
        if hasattr(gui_app, 'SmartcardGUI'):
            print("✅ SmartcardGUI class found")
        else:
            print("❌ SmartcardGUI class not found")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_core_components():
    """Test core component imports"""
    try:
        print("Testing core component imports...")
        
        from src.smartcard_manager import SmartcardManager
        from src.globalplatform import GlobalPlatformManager  
        from src.secure_channel import SecureChannelManager
        from src.config_manager import ConfigManager
        
        print("✅ All core components imported successfully")
        
        # Test basic initialization
        config_manager = ConfigManager()
        sc_manager = SmartcardManager()
        gp_manager = GlobalPlatformManager(sc_manager)
        secure_channel = SecureChannelManager(sc_manager)
        
        print("✅ All components initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing GUI Application Launch")
    print("=" * 50)
    
    # Test imports
    if not test_gui_imports():
        print("\n❌ GUI import test failed")
        return False
        
    if not test_core_components():
        print("\n❌ Core component test failed") 
        return False
    
    print("\n✅ All tests passed! GUI application should launch correctly.")
    print("\nTo run the GUI application:")
    print("  python gui_app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
