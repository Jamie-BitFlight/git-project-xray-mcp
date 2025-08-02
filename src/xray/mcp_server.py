import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

"""FastMCP server for XRAY code intelligence - ast-grep powered structural analysis."""

import os
from typing import Dict, List, Any, Optional

from fastmcp import FastMCP

from xray.core.indexer import XRayIndexer

# Initialize FastMCP server
mcp = FastMCP("XRAY Code Intelligence")

# Cache for indexer instances per repository path
_indexer_cache: Dict[str, XRayIndexer] = {}


def normalize_path(path: str) -> str:
    """Normalize a path to absolute form."""
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    path = str(Path(path).resolve())
    if not os.path.exists(path):
        raise ValueError(f"Path '{path}' does not exist")
    if not os.path.isdir(path):
        raise ValueError(f"Path '{path}' is not a directory")
    return path


def get_indexer(path: str) -> XRayIndexer:
    """Get or create indexer instance for the given path."""
    path = normalize_path(path)
    if path not in _indexer_cache:
        _indexer_cache[path] = XRayIndexer(path)
    return _indexer_cache[path]


@mcp.tool
def build_index(root_path: str) -> str:
    """
    Generate a visual file tree of the repository.
    
    This tool provides a high-level structural view of your codebase,
    showing the directory and file organization while respecting .gitignore
    rules and common exclusion patterns.
    
    Args:
        root_path: Absolute path to the project directory
        
    Returns:
        A formatted tree representation of the project structure
    """
    try:
        indexer = get_indexer(root_path)
        tree = indexer.build_index()
        return tree
    except Exception as e:
        return f"Error building index: {str(e)}"


@mcp.tool
def find_symbol(root_path: str, query: str) -> List[Dict[str, Any]]:
    """
    Search for symbol definitions using fuzzy matching.
    
    This tool finds functions, classes, methods, and other symbols that match
    your query. Results may include symbols from comments or strings - evaluate
    the context to determine relevance. This approach ensures no important 
    symbols are missed.
    
    Args:
        root_path: Absolute path to the project directory
        query: Fuzzy search term (e.g., "auth service", "validate", "UserModel")
        
    Returns:
        List of matching symbols with:
        - name: Symbol name
        - type: Symbol type (function, class, method, etc.)
        - path: File path
        - start_line/end_line: Location in file
        - context: Surrounding code
        - confidence: Parsing confidence (high for AST, medium for regex)
    """
    try:
        indexer = get_indexer(root_path)
        results = indexer.find_symbol(query)
        return results
    except Exception as e:
        return [{"error": f"Error finding symbol: {str(e)}"}]


@mcp.tool
def what_depends(exact_symbol: Dict[str, Any]) -> List[str]:
    """
    Find what a specific symbol depends on (imports and function calls).
    
    Takes a symbol object from find_symbol and analyzes what it uses within
    its definition. Results may include false positives (e.g., if statements
    may be detected as function calls) - evaluate based on context.
    
    Args:
        exact_symbol: Symbol object from find_symbol containing:
            - path: File path
            - start_line: Start line of symbol
            - end_line: End line of symbol
            
    Returns:
        List of dependency names (functions called, modules imported)
    """
    try:
        # Extract root path from the symbol's path
        symbol_path = Path(exact_symbol['path'])
        root_path = str(symbol_path.parent)
        
        # Find a suitable root (go up until we find a git repo or reach root)
        while root_path != '/':
            if (Path(root_path) / '.git').exists():
                break
            parent = Path(root_path).parent
            if parent == Path(root_path):
                break
            root_path = str(parent)
        
        indexer = get_indexer(root_path)
        dependencies = indexer.what_depends(exact_symbol)
        return dependencies
    except Exception as e:
        return [f"Error: {str(e)}"]


@mcp.tool  
def what_breaks(exact_symbol: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find what would break if a symbol is changed (reverse dependencies).
    
    Searches the entire codebase for references to the given symbol.
    Note: This search is based on the symbol's name and may include 
    references to other items with the same name in different modules.
    
    Args:
        exact_symbol: Symbol object from find_symbol containing:
            - name: Symbol name to search for
            - path: Original file path
            
    Returns:
        Dictionary with:
        - references: List of locations using this symbol
        - total_count: Number of references found
        - note: Caveat about name-based matching
    """
    try:
        # Extract root path from the symbol's path
        symbol_path = Path(exact_symbol['path'])
        root_path = str(symbol_path.parent)
        
        # Find a suitable root
        while root_path != '/':
            if (Path(root_path) / '.git').exists():
                break
            parent = Path(root_path).parent
            if parent == Path(root_path):
                break
            root_path = str(parent)
        
        indexer = get_indexer(root_path)
        return indexer.what_breaks(exact_symbol)
    except Exception as e:
        return {"error": f"Error finding references: {str(e)}"}


def main():
    """Main entry point for the XRAY MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()