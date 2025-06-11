#!/usr/bin/env python3
"""
Simple test to verify core functionality works.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_imports():
    """Test that all core modules can be imported"""
    try:
        from src.database_manager import DatabaseManager, KeysetRecord, OTAMessage
        print("✅ Database manager imported successfully")
        
        from src.ota_manager import OTAManager
        print("✅ OTA manager imported successfully")
        
        from src.config_manager import ConfigManager
        print("✅ Config manager imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_database():
    """Test basic database functionality"""
    try:
        db = DatabaseManager("test_simple.db")
        
        # Test getting keysets
        keysets = db.get_keysets()
        print(f"✅ Database has {len(keysets)} keysets")
        
        # Test getting value sets
        value_sets = db.get_value_sets()
        print(f"✅ Available value sets: {value_sets}")
        
        # Test getting OTA templates
        templates = db.get_ota_templates()
        print(f"✅ Database has {len(templates)} OTA templates")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_ota():
    """Test basic OTA functionality"""
    try:
        db = DatabaseManager("test_simple.db")
        ota = OTAManager(db)
        
        # Test AID validation
        test_aid = "A000000151000000"
        is_valid = ota.validate_aid(test_aid)
        print(f"✅ AID validation result: {is_valid}")
        
        # Test operations list
        ops = ota.get_clfdb_operations()
        print(f"✅ CLFDB operations: {ops}")
        
        return True
    except Exception as e:
        print(f"❌ OTA test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Running Simple CCM Tests...\n")
    
    success = True
    success &= test_basic_imports()
    success &= test_database()
    success &= test_ota()
    
    # Cleanup
    try:
        if os.path.exists("test_simple.db"):
            os.remove("test_simple.db")
    except:
        pass
    
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    print("\n🚀 Testing CLI components...")
    try:
        from ccm_tool import CLIInterface
        cli = CLIInterface()
        print("✅ CLI interface created successfully")
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
