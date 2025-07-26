#!/usr/bin/env python3
"""Debug Tree-sitter parsing to understand node types."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import tree_sitter
import tree_sitter_python

def debug_parse():
    """Debug Tree-sitter parsing."""
    # Create language and parser
    PY_LANGUAGE = tree_sitter.Language(tree_sitter_python.language())
    parser = tree_sitter.Parser(PY_LANGUAGE)
    
    # Simple test code
    code = b'''
def hello():
    pass

class MyClass:
    def method(self):
        return "test"

import os
from pathlib import Path
'''
    
    # Parse the code
    tree = parser.parse(code)
    
    def print_tree(node, depth=0):
        """Recursively print the tree structure."""
        indent = "  " * depth
        print(f"{indent}{node.type} [{node.start_point[0]}:{node.start_point[1]}-{node.end_point[0]}:{node.end_point[1]}]")
        
        if node.text and len(node.text) < 50:
            print(f"{indent}  text: {node.text}")
        
        for child in node.children:
            print_tree(child, depth + 1)
    
    print("Tree structure:")
    print_tree(tree.root_node)
    
    # Test simple queries
    try:
        matches = PY_LANGUAGE.query("(function_definition name: (identifier) @name)").matches(tree.root_node)
        print(f"\nFunction query matches: {len(matches)}")
        
        for match in matches:
            for node in match[1].values():
                print(f"  function: {node.text}")
    except Exception as e:
        print(f"Function query error: {e}")
    
    try:
        matches = PY_LANGUAGE.query("(class_definition name: (identifier) @name)").matches(tree.root_node)
        print(f"\nClass query matches: {len(matches)}")
        
        for match in matches:
            for node in match[1].values():
                print(f"  class: {node.text}")
    except Exception as e:
        print(f"Class query error: {e}")
        
    try:
        matches = PY_LANGUAGE.query("(import_statement name: (dotted_name) @name)").matches(tree.root_node)
        print(f"\nImport query matches: {len(matches)}")
        
        for match in matches:
            for node in match[1].values():
                print(f"  import: {node.text}")
    except Exception as e:
        print(f"Import query error: {e}")

if __name__ == "__main__":
    debug_parse()