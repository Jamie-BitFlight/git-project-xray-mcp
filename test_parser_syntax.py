#!/usr/bin/env python3
"""Test that parser files have correct syntax."""

import ast
import os

def check_python_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    """Check syntax of all parser files."""
    parser_dir = os.path.join(os.path.dirname(__file__), 'src', 'xray', 'parsers')
    
    files_to_check = [
        'base.py',
        'python.py',
        'javascript.py',
        'typescript.py',
        'go.py',
        '__init__.py'
    ]
    
    print("Checking parser file syntax...")
    all_ok = True
    
    for file_name in files_to_check:
        file_path = os.path.join(parser_dir, file_name)
        if os.path.exists(file_path):
            ok, error = check_python_syntax(file_path)
            if ok:
                print(f"✓ {file_name}: OK")
            else:
                print(f"✗ {file_name}: SYNTAX ERROR")
                print(f"  {error}")
                all_ok = False
        else:
            print(f"✗ {file_name}: FILE NOT FOUND")
            all_ok = False
    
    if all_ok:
        print("\n✓ All parser files have valid syntax!")
    else:
        print("\n✗ Some parser files have issues!")
    
    # Also check that imports would work
    print("\n\nChecking parser class definitions...")
    parser_classes = {
        'python.py': 'PythonParser',
        'javascript.py': 'JavaScriptParser',
        'typescript.py': 'TypeScriptParser',
        'go.py': 'GoParser'
    }
    
    for file_name, class_name in parser_classes.items():
        file_path = os.path.join(parser_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                code = f.read()
            try:
                tree = ast.parse(code)
                classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                if class_name in classes:
                    print(f"✓ {file_name}: Found {class_name}")
                else:
                    print(f"✗ {file_name}: {class_name} not found! Found: {classes}")
            except Exception as e:
                print(f"✗ {file_name}: Error parsing: {e}")

if __name__ == "__main__":
    main()