import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import tree_sitter
from xray.parsers.base import load_tree_sitter_languages

def debug_parse(lang: str, file_path: str):
    """Debug Tree-sitter parsing for a specific language and file."""
    languages = load_tree_sitter_languages()
    
    if lang not in languages:
        print(f"Error: Language '{lang}' not supported or not found.")
        return
    
    language = languages[lang]
    parser = tree_sitter.Parser(language)
    
    try:
        with open(file_path, 'rb') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return
    
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
    
    # Define common queries for debugging
    queries = {
        "javascript": {
            "function": "(function_declaration name: (identifier) @name)",
            "class": "(class_declaration name: (identifier) @name)",
            "class_expr": "(variable_declarator value: (class_expression (identifier) @name))",
            "import": "(import_statement source: (string (string_fragment) @name))"
        },
        "typescript": {
            "function": "(function_declaration name: (identifier) @name)",
            "class": "(class_declaration name: (type_identifier) @name)",
            "class_expr": "(variable_declarator value: (class_expression (type_identifier) @name))",
            "import": "(import_statement source: (string (string_fragment) @name))"
        },
        "python": {
            "function": "(function_definition name: (identifier) @name)",
            "class": "(class_definition name: (identifier) @name)",
            "import": "(import_statement name: (dotted_name) @name)"
        },
        "go": {
            "function": "(function_declaration name: (identifier) @name)",
            "type_declaration": "(type_declaration name: (type_identifier) @name)",
            "import": "(import_declaration path: (string_literal) @name)"
        }
    }

    # Test queries based on language
    if lang in queries:
        for query_name, query_str in queries[lang].items():
            try:
                query = tree_sitter.Query(language, query_str)
                query_cursor = tree_sitter.QueryCursor(query)
                matches = query_cursor.matches(tree.root_node)
                print(f"\n{query_name.capitalize()} query matches: {len(list(matches))}")
                
                # Re-run query to iterate and print matches
                matches = query_cursor.matches(tree.root_node)
                for match in matches:
                    for capture_name, node in match[1].items():
                        print(f"  {capture_name}: {node.text.decode('utf-8')}")
            except Exception as e:
                print(f"{query_name.capitalize()} query error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug Tree-sitter parsing.")
    parser.add_argument("--lang", required=True, help="Language to parse (e.g., javascript, typescript, python, go)")
    parser.add_argument("--file", required=True, help="Path to the file to parse")
    args = parser.parse_args()
    
    debug_parse(args.lang, args.file)
