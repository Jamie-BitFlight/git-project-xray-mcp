#!/usr/bin/env python3
"""Test script for XRAY pure Python implementation."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from xray.core.indexer import XRayIndexer

def test_build_index():
    print("=== Testing build_index ===")
    indexer = XRayIndexer(".")
    tree = indexer.build_index()
    print(tree[:500] + "..." if len(tree) > 500 else tree)
    print()

def test_find_symbol():
    print("=== Testing find_symbol ===")
    indexer = XRayIndexer(".")
    
    # Search for "parser"
    results = indexer.find_symbol("parser", limit=5)
    print(f"Found {len(results)} results for 'parser':")
    for r in results:
        print(f"  - {r['name']} ({r['type']}) in {Path(r['path']).name}:{r['start_line']}")
    print()

def test_parsers():
    print("=== Testing language parsers ===")
    indexer = XRayIndexer(".")
    
    # Test Python parser
    test_py = '''
def hello_world():
    print("Hello, World!")

class Calculator:
    def add(self, a, b):
        return a + b
'''
    
    from xray.parsers.python import PythonParser
    py_parser = PythonParser()
    symbols = py_parser.find_definitions(test_py, "test.py")
    print(f"Python parser found {len(symbols)} symbols:")
    for s in symbols:
        print(f"  - {s.name} ({s.type})")
    
    # Test JavaScript parser
    test_js = '''
function greet(name) {
    console.log("Hello, " + name);
}

const add = (a, b) => a + b;

class User {
    constructor(name) {
        this.name = name;
    }
}
'''
    
    from xray.parsers.javascript import JavaScriptParser
    js_parser = JavaScriptParser()
    symbols = js_parser.find_definitions(test_js, "test.js")
    print(f"\nJavaScript parser found {len(symbols)} symbols:")
    for s in symbols:
        print(f"  - {s.name} ({s.type})")

if __name__ == "__main__":
    test_build_index()
    test_find_symbol()
    test_parsers()