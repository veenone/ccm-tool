"""
Simple test script to verify the tool structure without external dependencies.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test if all modules can be imported"""
    print("Testing module imports...")
    
    try:
        # Test core modules
        print("  ✓ Importing smartcard_manager...")
        from smartcard_manager import SmartcardManager, APDUCommand, APDUResponse
        
        print("  ✓ Importing config_manager...")
        from config_manager import ConfigManager
        
        print("  ✓ Importing globalplatform...")
        from globalplatform import GlobalPlatformManager, SecurityDomainInfo, ApplicationInfo
        
        print("  ✓ Importing secure_channel...")
        from secure_channel import SecureChannelManager, KeySet
        
        print("  ✓ All core modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from config_manager import ConfigManager
        
        config_manager = ConfigManager()
        keysets = config_manager.list_keysets()
        print(f"  ✓ Found {len(keysets)} keysets")
        
        templates = config_manager.list_security_domain_templates()
        print(f"  ✓ Found {len(templates)} security domain templates")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False


def test_apdu_functionality():
    """Test APDU command/response functionality"""
    print("\nTesting APDU functionality...")
    
    try:
        from smartcard_manager import APDUCommand, APDUResponse
        
        # Test APDU command
        cmd = APDUCommand(0x80, 0xF2, 0x80, 0x00, b'\x04\x01\x02\x03', 0x00)
        bytes_data = cmd.to_bytes()
        print(f"  ✓ APDU command created: {len(bytes_data)} bytes")
        
        # Test APDU response
        response = APDUResponse([0x01, 0x02, 0x03, 0x90, 0x00])
        print(f"  ✓ APDU response parsed: SW={response.sw:04X}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ APDU test error: {e}")
        return False


def test_keyset_functionality():
    """Test keyset functionality"""
    print("\nTesting keyset functionality...")
    
    try:
        from secure_channel import KeySet
        
        keyset = KeySet.from_hex(
            enc_hex="404142434445464748494A4B4C4D4E4F",
            mac_hex="404142434445464748494A4B4C4D4E4F", 
            dek_hex="404142434445464748494A4B4C4D4E4F",
            key_version=1,
            protocol="SCP03"
        )
        
        print(f"  ✓ KeySet created: {keyset.protocol} v{keyset.key_version}")
        return True
        
    except Exception as e:
        print(f"  ✗ KeySet test error: {e}")
        return False


def show_project_structure():
    """Show the project structure"""
    print("\nProject Structure:")
    print("==================")
    
    def show_directory(path, prefix=""):
        try:
            items = sorted(os.listdir(path))
            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                
                print(f"{prefix}{current_prefix}{item}")
                
                if os.path.isdir(item_path) and not item.startswith('.'):
                    extension = "    " if is_last else "│   "
                    show_directory(item_path, prefix + extension)
        except PermissionError:
            pass
    
    show_directory(".")


def main():
    """Main test routine"""
    print("=" * 60)
    print("  Smartcard Management Tool - Structure Test")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_imports,
        test_configuration,
        test_apdu_functionality,
        test_keyset_functionality
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"  Test Results: {passed}/{len(tests)} passed")
    print(f"{'='*60}")
    
    if passed == len(tests):
        print("🎉 All tests passed! The tool structure is correct.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    # Show project structure
    show_project_structure()
    
    print(f"\n📁 Current directory: {os.getcwd()}")
    print(f"📄 Main script: ccm_tool.py")
    print(f"📄 README: README.md")
    print(f"⚙️  Configuration: config/")
    print(f"🔬 Examples: examples/")
    print(f"🧪 Tests: tests/")
    
    return passed == len(tests)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
