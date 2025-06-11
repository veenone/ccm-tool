#!/usr/bin/env python3
"""
Validation script for the updated smartcard management tool.
Tests both uv environment and core functionality.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()[:200]}...")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()[:200]}...")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("🎯 Smartcard Management Tool - Validation Report")
    print("=" * 60)
    
    # Test uv itself
    tests = [
        ("uv --version", "UV installation check"),
        ("uv pip list", "UV package list"),
        ('uv run python -c "import customtkinter; print(\'CustomTkinter OK\')"', "CustomTkinter import test"),
        ('uv run python -c "import smartcard; print(\'PySCard OK\')"', "PySCard import test"),
        ('uv run python -c "import sys; sys.path.insert(0, \'src\'); from src.smartcard_manager import SmartcardManager; print(\'Core modules OK\')"', "Core modules import test"),
        ("uv run python ccm_tool.py list-readers", "CLI tool test"),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 VALIDATION SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ The smartcard management tool is ready to use with UV:")
        print("   • CLI: uv run python ccm_tool.py --help")
        print("   • GUI: uv run python gui_app.py")
        print("\n📚 Key features:")
        print("   • Modern CustomTkinter GUI")
        print("   • Fast UV dependency management")
        print("   • Cross-platform support")
        print("   • PC/SC smartcard integration")
        print("   • GlobalPlatform support")
    else:
        print(f"⚠️  {total - passed} tests failed. Please check the errors above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
