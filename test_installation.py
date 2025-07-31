#!/usr/bin/env python3
"""
XRAY Installation Test Script

This script verifies that XRAY is properly installed and functioning.
Run this after installation to ensure everything is working correctly.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}\n")

def test_imports():
    """Test that all required modules can be imported."""
    print_header("Testing Imports")
    
    try:
        import xray
        print("✅ xray module found")
    except ImportError as e:
        print(f"❌ Failed to import xray: {e}")
        return False
    
    try:
        from xray.mcp_server import server
        print("✅ MCP server module found")
    except ImportError as e:
        print(f"❌ Failed to import MCP server: {e}")
        return False
    
    try:
        import tree_sitter
        print("✅ tree-sitter module found")
    except ImportError as e:
        print(f"❌ Failed to import tree-sitter: {e}")
        return False
    
    try:
        import fastmcp
        print("✅ FastMCP module found")
    except ImportError as e:
        print(f"❌ Failed to import FastMCP: {e}")
        return False
    
    return True

def test_parsers():
    """Test that language parsers are available."""
    print_header("Testing Language Parsers")
    
    languages = ['python', 'javascript', 'typescript', 'go']
    all_good = True
    
    for lang in languages:
        try:
            module_name = f'tree_sitter_{lang}'
            __import__(module_name)
            print(f"✅ {lang.capitalize()} parser found")
        except ImportError:
            print(f"❌ Failed to import {lang} parser")
            all_good = False
    
    return all_good

def test_basic_functionality():
    """Test basic XRAY functionality."""
    print_header("Testing Basic Functionality")
    
    # Create a temporary directory with test files
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        
        # Create test Python file
        test_py = test_dir / "test.py"
        test_py.write_text('''
def greet(name):
    """Greet a person."""
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, prefix="Hello"):
        self.prefix = prefix
    
    def greet(self, name):
        return f"{self.prefix}, {name}!"

def main():
    g = Greeter()
    print(g.greet("World"))
''')
        
        # Create test JavaScript file
        test_js = test_dir / "test.js"
        test_js.write_text('''
function add(a, b) {
    return a + b;
}

class Calculator {
    multiply(x, y) {
        return x * y;
    }
}

const calc = new Calculator();
console.log(calc.multiply(5, 3));
''')
        
        try:
            from xray.core.indexer import XRayIndexer
            
            # Test indexing
            print("Testing indexer...")
            indexer = XRayIndexer(str(test_dir))
            stats = indexer.build_index()
            
            if stats['success']:
                print(f"✅ Indexer working - found {stats['files_parsed']} files, {stats['symbols_found']} symbols")
            else:
                print("❌ Indexer failed")
                return False
            
            # Test symbol search
            from xray.core.query import XRayQuery
            print("\nTesting symbol search...")
            query = XRayQuery(str(test_dir))
            results = query.find_symbols("greet")
            
            if results and len(results) > 0:
                print(f"✅ Symbol search working - found {len(results)} matches for 'greet'")
            else:
                print("❌ Symbol search failed")
                return False
            
            # Test impact analysis
            from xray.core.impact import XRayImpactAnalyzer
            print("\nTesting impact analysis...")
            analyzer = XRayImpactAnalyzer(str(test_dir))
            impact = analyzer.analyze_impact("greet")
            
            print("✅ Impact analysis working")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during functionality test: {e}")
            return False

def test_mcp_server():
    """Test that MCP server can be initialized."""
    print_header("Testing MCP Server")
    
    try:
        from xray.mcp_server import server
        print("✅ MCP server can be imported")
        
        # Check that all tools are registered
        tool_count = len(server._tools)
        print(f"✅ Found {tool_count} MCP tools registered")
        
        # List available tools
        print("\nAvailable tools:")
        for tool_name in server._tools:
            print(f"  - {tool_name}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing MCP server: {e}")
        return False

def main():
    """Run all tests."""
    print("\n🔍 XRAY Installation Test Suite")
    print("================================")
    
    # Track overall success
    all_tests_passed = True
    
    # Run tests
    if not test_imports():
        all_tests_passed = False
    
    if not test_parsers():
        all_tests_passed = False
    
    if not test_basic_functionality():
        all_tests_passed = False
    
    if not test_mcp_server():
        all_tests_passed = False
    
    # Summary
    print_header("Test Summary")
    if all_tests_passed:
        print("✅ All tests passed! XRAY is installed correctly.")
        print("\nNext steps:")
        print("1. Configure your AI assistant with the MCP server")
        print("2. Try 'use XRAY tools' in your prompts")
        print("3. Start with 'build_index' to analyze a codebase")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Ensure Python 3.11+ is installed")
        print("2. Try reinstalling with: uv pip install -e .")
        print("3. Check that all dependencies are installed")
        return 1

if __name__ == "__main__":
    sys.exit(main())