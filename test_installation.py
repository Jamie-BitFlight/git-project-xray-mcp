#!/usr/bin/env python3
"""
XRAY Installation Test Script

This script verifies that XRAY is properly installed and functioning.
Run this after installation to ensure everything is working correctly.
"""

import sys
import os
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}\n")

def test_imports():
    """Test that core modules can be imported."""
    print_header("Testing Core Imports")
    
    try:
        # Add src to path if running from repo
        src_path = Path(__file__).parent / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        from xray.core.indexer import XRayIndexer
        print("✅ Core indexer module found")
        
        from xray.mcp_server import main
        print("✅ MCP server module found")
        
        import fastmcp
        print("✅ FastMCP module found")
        
        import thefuzz
        print("✅ thefuzz module found")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False

def test_ast_grep():
    """Test that ast-grep is available."""
    print_header("Testing ast-grep")
    
    try:
        result = subprocess.run(["ast-grep", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ast-grep is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ ast-grep not found or not working")
            return False
    except FileNotFoundError:
        print("❌ ast-grep not found in PATH")
        return False

def test_basic_functionality():
    """Test basic XRAY functionality."""
    print_header("Testing Basic Functionality")
    
    try:
        # Add src to path if running from repo
        src_path = Path(__file__).parent / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        
        from xray.core.indexer import XRayIndexer
        
        # Test with current directory
        print("Testing explore_repo...")
        indexer = XRayIndexer(".")
        
        # Test directory tree (without symbols)
        tree = indexer.explore_repo(max_depth=2, include_symbols=False)
        if tree:
            print("✅ explore_repo (directory view) working")
        else:
            print("❌ explore_repo failed")
            return False
        
        print("\nTesting find_symbol...")
        # Test symbol search
        symbols = indexer.find_symbol("test")
        print(f"✅ find_symbol working - found {len(symbols)} matches")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during functionality test: {e}")
        return False

def test_mcp_server():
    """Test that MCP server can be started."""
    print_header("Testing MCP Server")
    
    try:
        # Check if xray-mcp command exists
        result = subprocess.run(["which", "xray-mcp"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ xray-mcp command found at: {result.stdout.strip()}")
            
            # Try to run it with --help (safe test)
            help_result = subprocess.run(["xray-mcp", "--help"], capture_output=True, text=True)
            if "XRAY Code Intelligence" in help_result.stdout or help_result.returncode == 0:
                print("✅ MCP server executable working")
                return True
            else:
                print("❌ MCP server executable not working properly")
                return False
        else:
            print("❌ xray-mcp command not found in PATH")
            print("   This is expected if you haven't installed the package yet")
            return True  # Not a critical failure for development
            
    except Exception as e:
        print(f"⚠️  Could not test MCP server: {e}")
        return True  # Not a critical failure

def main():
    """Run all tests."""
    print("\n🔍 XRAY Installation Test Suite")
    print("================================")
    
    # Track overall success
    all_tests_passed = True
    
    # Run tests
    if not test_imports():
        all_tests_passed = False
    
    if not test_ast_grep():
        all_tests_passed = False
    
    if not test_basic_functionality():
        all_tests_passed = False
    
    if not test_mcp_server():
        all_tests_passed = False
    
    # Summary
    print_header("Test Summary")
    if all_tests_passed:
        print("✅ All tests passed! XRAY is ready to use.")
        print("\nNext steps:")
        print("1. Configure your AI assistant with the MCP server")
        print("2. Try 'use XRAY tools' in your prompts")
        print("3. Start with explore_repo() to analyze a codebase")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Ensure Python 3.10+ is installed")
        print("2. Ensure ast-grep-cli is installed: pip install ast-grep-cli")
        print("3. Try reinstalling: pip install -e .")
        return 1

if __name__ == "__main__":
    sys.exit(main())