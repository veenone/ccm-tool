#!/usr/bin/env python3
"""
Test script to verify database, OTA, and GUI integration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_database_integration():
    """Test database manager functionality"""
    print("🔍 Testing Database Integration...")
    
    try:
        from src.database_manager import DatabaseManager, KeysetRecord
        
        # Initialize database
        db_manager = DatabaseManager("test_db.db")
        print("  ✅ Database initialized successfully")
        
        # Test keyset operations
        keysets = db_manager.get_keysets()
        print(f"  ✅ Found {len(keysets)} default keysets")
        
        # Test value sets
        value_sets = db_manager.get_value_sets()
        print(f"  ✅ Found value sets: {value_sets}")
        
        # Test OTA templates
        templates = db_manager.get_ota_templates()
        print(f"  ✅ Found {len(templates)} OTA templates")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False

def test_ota_integration():
    """Test OTA manager functionality"""
    print("\n🔍 Testing OTA Integration...")
    
    try:
        from src.database_manager import DatabaseManager
        from src.ota_manager import OTAManager
        
        # Initialize managers
        db_manager = DatabaseManager("test_db.db")
        ota_manager = OTAManager(db_manager)
        print("  ✅ OTA manager initialized successfully")
        
        # Test AID validation
        valid_aid = "A000000151000000"
        invalid_aid = "123"
        
        assert ota_manager.validate_aid(valid_aid) == True
        assert ota_manager.validate_aid(invalid_aid) == False
        print("  ✅ AID validation working correctly")
        
        # Test CLFDB operations list
        operations = ota_manager.get_clfdb_operations()
        print(f"  ✅ Available CLFDB operations: {operations}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ OTA test failed: {e}")
        return False

def test_config_integration():
    """Test config manager with database integration"""
    print("\n🔍 Testing Config Integration...")
    
    try:
        from src.config_manager import ConfigManager
        
        # Initialize config manager (should load from database)
        config_manager = ConfigManager()
        print("  ✅ Config manager initialized successfully")
        
        # Test value sets
        value_sets = config_manager.get_value_sets()
        print(f"  ✅ Value sets available: {value_sets}")
        
        # Test keyset loading
        keysets = config_manager.get_available_keysets()
        for vs, ks_list in keysets.items():
            print(f"  ✅ Value set '{vs}': {len(ks_list)} keysets")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Config test failed: {e}")
        return False

def test_cli_integration():
    """Test CLI commands work with new features"""
    print("\n🔍 Testing CLI Integration...")
    
    try:
        # Import CLI components
        from ccm_tool import CLIInterface
        
        cli = CLIInterface()
        print("  ✅ CLI interface initialized successfully")
        
        # Test database manager in CLI
        assert hasattr(cli, 'db_manager')
        print("  ✅ CLI has database manager")
        
        return True
        
    except Exception as e:
        print(f"  ❌ CLI test failed: {e}")
        return False

def test_gui_components():
    """Test GUI components can be imported"""
    print("\n🔍 Testing GUI Components...")
    
    try:
        # Test basic imports (may fail if dependencies not installed)
        from gui_app import SmartcardGUI, KeysetDialog
        print("  ✅ GUI classes imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"  ⚠️  GUI import failed (dependencies may not be installed): {e}")
        return False
    except Exception as e:
        print(f"  ❌ GUI test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 Running CCM Tool Integration Tests\n")
    
    tests = [
        test_database_integration,
        test_ota_integration,
        test_config_integration,
        test_cli_integration,
        test_gui_components
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check dependencies and configuration.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    
    # Clean up test database
    try:
        import os
        if os.path.exists("test_db.db"):
            os.remove("test_db.db")
            print("\n🧹 Cleaned up test database")
    except:
        pass
    
    sys.exit(exit_code)
