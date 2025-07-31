"""FastMCP server for XRAY code intelligence."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from functools import wraps

from fastmcp import FastMCP

from .core.indexer import XRayIndexer
from .core.query import XRayQueryEngine
from .core.impact import XRayImpactAnalyzer


# Initialize FastMCP server
mcp = FastMCP("XRAY Code Intelligence")

# Cache for components per repository path
_component_cache: Dict[str, Dict[str, any]] = {}


def validate_params(valid_params: Dict[str, type], common_errors: Dict[str, str] = None):
    """
    Decorator to validate parameters and provide LLM-friendly error messages.
    
    Args:
        valid_params: Dictionary of parameter names and their types
        common_errors: Dictionary of common parameter mistakes and their corrections
    """
    def decorator(func):
        @wraps(func)
        def wrapper(**kwargs):
            # Check for unexpected parameters
            unexpected = set(kwargs.keys()) - set(valid_params.keys())
            if unexpected:
                param = list(unexpected)[0]
                func_name = func.__name__
                
                # Check if this is a common error
                if common_errors and param in common_errors:
                    return {
                        "error": f"Invalid parameter '{param}' for {func_name}",
                        "correction": common_errors[param],
                        "valid_parameters": list(valid_params.keys()),
                        "example": f"{func_name}({', '.join(f'{k}=...' for k in list(valid_params.keys())[:2])})"
                    }
                
                # Default error for unexpected parameters
                return {
                    "error": f"Parameter '{param}' is not supported by {func_name}",
                    "valid_parameters": list(valid_params.keys()),
                    "suggestion": f"Remove the '{param}' parameter and use only the valid parameters listed above",
                    "example": f"{func_name}({', '.join(f'{k}=...' for k in list(valid_params.keys())[:2])})"
                }
            
            # Check for missing required parameters
            required = {k for k, v in valid_params.items() if not (hasattr(v, '__args__') and type(None) in v.__args__)}
            missing = required - set(kwargs.keys())
            if missing and 'path' not in missing:  # path has a default
                param = list(missing)[0]
                return {
                    "error": f"Missing required parameter '{param}'",
                    "required_parameters": list(required),
                    "all_parameters": list(valid_params.keys()),
                    "suggestion": f"Add the '{param}' parameter to your call"
                }
            
            # All good, call the function
            try:
                return func(**kwargs)
            except Exception as e:
                return {
                    "error": f"Tool execution failed: {type(e).__name__}",
                    "details": str(e),
                    "suggestion": "Check your input values and try again"
                }
        
        return wrapper
    return decorator


def friendly_error_handler(func):
    """Decorator to provide friendly error messages for LLMs."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TypeError as e:
            # Handle unexpected keyword arguments
            error_msg = str(e)
            if "unexpected keyword argument" in error_msg:
                # Extract the problematic parameter
                import re
                match = re.search(r"unexpected keyword argument '(\w+)'", error_msg)
                if match:
                    param = match.group(1)
                    func_name = func.__name__
                    
                    # Provide specific guidance based on the function and parameter
                    if param == "file" and func_name in ["what_depends", "what_breaks", "find_symbol"]:
                        return {
                            "error": f"Parameter '{param}' is not supported by {func_name}.",
                            "suggestion": f"Remove the '{param}' parameter. This tool operates on symbol names across the entire indexed project.",
                            "example": f"{func_name}('function_name') or {func_name}('ClassName')",
                            "hint": "Symbol names are function names, class names, or method names - not file paths."
                        }
                    else:
                        return {
                            "error": f"Unexpected parameter '{param}' for {func_name}.",
                            "suggestion": f"Check the tool documentation for valid parameters.",
                            "valid_params": str(func.__annotations__.keys()) if hasattr(func, '__annotations__') else "See documentation"
                        }
            
            # Generic type error
            return {
                "error": "Invalid parameters provided.",
                "details": str(e),
                "suggestion": "Check the tool documentation for correct parameter usage."
            }
        except Exception as e:
            # Handle other errors with context
            return {
                "error": f"Tool execution failed: {type(e).__name__}",
                "details": str(e),
                "suggestion": "Check your input parameters and try again."
            }
    
    return wrapper


def normalize_path(path: str) -> str:
    """Normalize a path to absolute form."""
    # Expand user home directory
    path = os.path.expanduser(path)
    # Convert to absolute path
    path = os.path.abspath(path)
    # Resolve symlinks and normalize
    path = str(Path(path).resolve())
    
    if not os.path.exists(path):
        raise ValueError(f"Path '{path}' does not exist")
    if not os.path.isdir(path):
        raise ValueError(f"Path '{path}' is not a directory")
    
    return path


def check_self_analysis(path: str) -> bool:
    """Check if we're analyzing the xray codebase itself and warn."""
    xray_src_path = Path(__file__).parent.parent.parent.resolve()
    is_self_analysis = Path(path).resolve() == xray_src_path or Path(path).resolve().is_relative_to(xray_src_path)
    
    if is_self_analysis:
        import sys
        print("\n" + "="*80, file=sys.stderr)
        print("⚠️  WARNING: XRAY IS ANALYZING ITS OWN CODEBASE! ⚠️", file=sys.stderr)
        print("="*80, file=sys.stderr)
        print("You are analyzing the xray MCP implementation itself.", file=sys.stderr)
        print("To analyze a different codebase, specify the path parameter:", file=sys.stderr)
        print('  Example: build_index(path="/path/to/your/project")', file=sys.stderr)
        print("="*80 + "\n", file=sys.stderr)
    
    return is_self_analysis


def add_self_analysis_warning(response: dict, path: str) -> dict:
    """Add warning to response if analyzing own codebase."""
    if check_self_analysis(path):
        response["⚠️ CRITICAL_WARNING"] = "YOU ARE ANALYZING XRAY'S OWN IMPLEMENTATION! Use path='/your/project' to analyze your actual codebase."
        response["self_analysis"] = True
    return response


def get_indexer(path: str = ".") -> XRayIndexer:
    """Get or create indexer instance for the given path."""
    path = normalize_path(path)
    
    if path not in _component_cache:
        _component_cache[path] = {}
    
    if 'indexer' not in _component_cache[path]:
        check_self_analysis(path)
        _component_cache[path]['indexer'] = XRayIndexer(path)
    
    return _component_cache[path]['indexer']


def get_query_engine(path: str = ".") -> XRayQueryEngine:
    """Get or create query engine instance for the given path."""
    path = normalize_path(path)
    
    if path not in _component_cache:
        _component_cache[path] = {}
    
    if 'query_engine' not in _component_cache[path]:
        check_self_analysis(path)
        _component_cache[path]['query_engine'] = XRayQueryEngine(path)
    
    return _component_cache[path]['query_engine']


def get_impact_analyzer(path: str = ".") -> XRayImpactAnalyzer:
    """Get or create impact analyzer instance for the given path."""
    path = normalize_path(path)
    
    if path not in _component_cache:
        _component_cache[path] = {}
    
    if 'impact_analyzer' not in _component_cache[path]:
        check_self_analysis(path)
        _component_cache[path]['impact_analyzer'] = XRayImpactAnalyzer(path)
    
    return _component_cache[path]['impact_analyzer']


@mcp.tool
def get_current_directory() -> dict:
    """Check current working directory BEFORE using other tools.
    
    Use this to understand where the MCP is running from, then specify
    the correct path parameter in other tools to analyze YOUR project,
    not the xray implementation.
    
    Returns:
        Dictionary with:
        - current_directory: Where MCP is running from
        - is_xray_directory: Whether this is the xray codebase
        - suggestion: What to do next
    """
    cwd = os.getcwd()
    xray_src_path = Path(__file__).parent.parent.parent.resolve()
    is_xray = Path(cwd).resolve() == xray_src_path or Path(cwd).resolve().is_relative_to(xray_src_path)
    
    result = {
        "current_directory": cwd,
        "is_xray_directory": is_xray,
    }
    
    if is_xray:
        result["⚠️ WARNING"] = "MCP is running from xray's own directory!"
        result["suggestion"] = "Use path parameter in all tools, e.g., build_index(path='/path/to/your/project')"
    else:
        result["suggestion"] = "Good! Not in xray directory. You can use path='.' or specify another path."
    
    return result


@mcp.tool
@validate_params(
    valid_params={'path': str},
    common_errors={
        'directory': "Use 'path' instead of 'directory' for the parameter name.",
        'folder': "Use 'path' instead of 'folder' for the parameter name.",
        'repo': "Use 'path' instead of 'repo' for the parameter name.",
        'project': "Use 'path' instead of 'project' for the parameter name.",
        'force': "Force rebuild is always performed. No need for a 'force' parameter."
    }
)
def build_index(path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Rebuild the code intelligence database - REQUIRED before using other tools.
    This tool walks the directory tree, parses all supported source files
    (Python, JavaScript, TypeScript, Go), extracts symbols (functions, classes,
    methods, imports), and builds a dependency graph for fast querying.
    
    WHEN TO USE:
    - First time analyzing a repository
    - When 'index_status.is_stale' is true in other tool responses
    - After significant code changes
    
    PERFORMANCE: ~1000 files/second on modern hardware
    
    Args:
        path: Directory path to index (defaults to current directory)
        
    COMMON ERRORS:
    1. "Path does not exist" → Ensure the path points to a valid directory.
    2. "Path is not a directory" → The path must point to a directory, not a file.
    3. Analyzing xray itself → Always specify path='/path/to/your/project' to analyze your code.
    4. "No supported source files found" → Ensure the directory contains .py, .js, .ts, or .go files.
        
    Returns:
        Dictionary with:
        - success: Whether indexing succeeded
        - files_indexed: Number of files processed
        - symbols_found: Number of symbols extracted
        - duration_seconds: Time taken
        - index_status: Freshness information
        - errors: Any parsing errors encountered
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        indexer = get_indexer(path)
        result = indexer.build_index(path)
        
        # Add some additional context to the result
        response = result.to_dict()
        response["message"] = "Index built successfully" if result.success else "Index build failed"
        
        if result.success:
            response["summary"] = f"Indexed {result.files_indexed} files, found {result.symbols_found} symbols, created {result.edges_created} dependency edges"
            
            if result.errors:
                response["warnings"] = result.errors
            
            # Add freshness info
            freshness = indexer.db.get_index_freshness()
            response["index_status"] = freshness
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to build index: {str(e)}",
            "files_indexed": 0,
            "symbols_found": 0,
            "edges_created": 0
        }


@mcp.tool
@validate_params(
    valid_params={'pattern': str, 'path': str},
    common_errors={
        'query': "Use 'pattern' instead of 'query' for the search term.",
        'name': "Use 'pattern' instead of 'name' for the search term.",
        'filename': "Use 'pattern' instead of 'filename' for the search term.",
        'extension': "Use 'pattern' to search for extensions (e.g., pattern='.py')."
    }
)
def find_files(pattern: str, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Search for FILES by name pattern - complements find_symbol.
    
    ACCEPTS ONLY:
    - pattern: Substring to search in filenames (e.g., "test", "slo", ".py")
    - path: Repository path (default: ".")
    
    USE THIS WHEN:
    - Looking for files with specific keywords (e.g., "slo", "config", "test")
    - find_symbol returns nothing (keyword might be in filename only)
    - Need to explore project structure
    
    EXAMPLES:
    ✓ find_files(pattern="slo", path="/my/project") - Finds scx-slo.bpf.c
    ✓ find_files(pattern=".test.") - Finds all test files
    ✓ find_files(pattern="config") - Finds configuration files
    
    COMMON ERRORS:
    1. "Unexpected keyword argument 'query'" → Use 'pattern' instead of 'query' for the search term.
    2. Searching for symbols → This tool searches filenames only. Use find_symbol() for code symbols.
    3. Complex patterns → This uses simple substring matching, not regex or glob patterns.
    
    Returns:
        Dictionary with:
        - files: List of matching file paths
        - total_matches: Number found
        - grouped_by_dir: Files organized by directory
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        # Get the indexer to access file list
        indexer = get_indexer(path)
        
        # Search through indexed files
        matching_files = []
        pattern_lower = pattern.lower()
        
        # Walk the repository
        for root, dirs, files in os.walk(path):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.xray'}]
            
            for file in files:
                if pattern_lower in file.lower():
                    file_path = os.path.relpath(os.path.join(root, file), path)
                    matching_files.append(file_path)
        
        # Group by directory
        grouped = {}
        for file_path in sorted(matching_files):
            dir_name = os.path.dirname(file_path) or "."
            if dir_name not in grouped:
                grouped[dir_name] = []
            grouped[dir_name].append(os.path.basename(file_path))
        
        response = {
            "pattern": pattern,
            "total_matches": len(matching_files),
            "files": matching_files[:100],  # Limit to prevent huge responses
            "grouped_by_dir": grouped,
            "message": f"Found {len(matching_files)} files matching '{pattern}'"
        }
        
        if len(matching_files) > 100:
            response["note"] = f"Showing first 100 of {len(matching_files)} matches"
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "pattern": pattern,
            "total_matches": 0,
            "files": [],
            "error": f"File search failed: {str(e)}"
        }


@mcp.tool
@validate_params(
    valid_params={'query': str, 'limit': int, 'path': str},
    common_errors={
        'file': "The 'file' parameter is not supported. Use 'query' to search for symbol names across the entire project.",
        'symbol': "Use 'query' instead of 'symbol' for the search term.",
        'name': "Use 'query' instead of 'name' for the search term.",
        'pattern': "Use 'query' for the symbol name to search. For file name patterns, use find_files() instead."
    }
)
def find_symbol(query: str, limit: int = 50, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Search for SYMBOL NAMES (functions, classes, methods) by substring.
    
    ACCEPTS ONLY:
    - query: Symbol name to search (e.g., "UserService", "validate", "main")
    - limit: Max results (default: 50)
    - path: Repository path (default: ".")
    
    COMMON MISTAKES:
    ❌ find_symbol(query="SLO") - Won't find if SLO only in comments/filenames
    ❌ find_symbol(file="main.py") - NO 'file' parameter! Use symbol names only
    ❌ find_symbol("keyword in comment") - Only finds defined symbols, not text
    
    CORRECT USAGE:
    ✓ find_symbol(query="UserService", path="/my/project")
    ✓ find_symbol(query="validate", limit=20)
    ✓ find_symbol(query="process_") - Finds all symbols starting with process_
    
    IMPORTANT: Searches indexed symbols only. Check 'index_status.is_stale'.
    
    COMMON ERRORS:
    1. "Unexpected keyword argument 'file'" → Remove 'file' parameter. This tool searches symbol names across the entire indexed project.
    2. "No symbols found" for keywords → This tool only finds defined symbols (functions, classes, methods). Use find_files() for filename searches.
    3. "Empty query provided" → The 'query' parameter must contain the symbol name to search for.
    
    Returns:
        Dictionary with:
        - symbols: List of matching symbols with file, line, signature
        - total_matches: Number found
        - index_status: Freshness info (CHECK is_stale!)
        - message: Human-readable summary
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not query.strip():
            return {
                "query": query,
                "total_matches": 0,
                "symbols": [],
                "message": "Empty query provided"
            }
        
        query_engine = get_query_engine(path)
        result = query_engine.find_symbols(query, limit)
        
        response = result.to_dict()
        
        if result.total_matches == 0:
            response["message"] = f"No symbols found matching '{query}'"
        elif result.total_matches == 1:
            response["message"] = f"Found 1 symbol matching '{query}'"
        else:
            response["message"] = f"Found {result.total_matches} symbols matching '{query}'"
        
        # Add freshness info
        freshness = query_engine.db.get_index_freshness()
        response["index_status"] = freshness
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "query": query,
            "total_matches": 0,
            "symbols": [],
            "error": f"Search failed: {str(e)}"
        }


@mcp.tool
@validate_params(
    valid_params={'symbol_name': str, 'max_depth': int, 'path': str},
    common_errors={
        'file': "The 'file' parameter is not supported. This tool analyzes symbols across the entire indexed project.",
        'symbol': "Use 'symbol_name' instead of 'symbol' for the parameter name.",
        'name': "Use 'symbol_name' instead of 'name' for the parameter name.",
        'function': "Use 'symbol_name' for any symbol type (function, class, method).",
        'query': "Use 'symbol_name' for the exact symbol to analyze. Use find_symbol() for searching."
    }
)
def what_breaks(symbol_name: str, max_depth: int = 5, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Find what depends on this symbol - "What breaks if I change this?"
    
    ACCEPTS ONLY:
    - symbol_name: Exact symbol name (e.g., "authenticate_user", "Database")
    - max_depth: How deep to trace impacts (default: 5)
    - path: Repository path (default: ".")
    
    COMMON MISTAKES:
    ❌ what_breaks(file="auth.py", symbol_name="login") - NO 'file' parameter!
    ❌ what_breaks("auth.login") - Use just "login", not dotted paths
    ❌ what_breaks(symbol="UserClass") - Parameter is 'symbol_name' not 'symbol'
    
    CORRECT USAGE:
    ✓ what_breaks(symbol_name="authenticate_user", path="/my/project")
    ✓ what_breaks(symbol_name="Database", max_depth=3)
    ✓ what_breaks(symbol_name="validate_input")
    
    IMPORTANT: Uses indexed data. Check 'index_status.is_stale'.
    
    COMMON ERRORS:
    1. "Unexpected keyword argument 'file'" → Remove 'file' parameter. This tool analyzes impact across the entire project.
    2. "Symbol not found" → Ensure the symbol name is exact (case-sensitive) and exists in the indexed code.
    3. "Empty symbol name provided" → The 'symbol_name' parameter is required and must be non-empty.
    4. Using dotted paths like "module.function" → Use just the symbol name "function".
    
    Returns:
        Dictionary with:
        - impacts_summary: Overview of what depends on this
        - direct_impacts: Immediate dependents
        - transitive_impacts: All affected symbols by depth
        - total_impacts: Count of everything affected
        - index_status: Freshness info (CHECK is_stale!)
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not symbol_name.strip():
            return {
                "symbol_name": symbol_name,
                "total_impacts": 0,
                "error": "Empty symbol name provided"
            }
        
        impact_analyzer = get_impact_analyzer(path)
        result = impact_analyzer.analyze_impact(symbol_name, max_depth)
        
        response = result.to_dict()
        
        if result.total_impacts == 0:
            response["message"] = f"Safe to modify - no symbols depend on '{symbol_name}'"
        elif result.total_impacts == 1:
            response["message"] = f"1 symbol depends on '{symbol_name}' - low risk"
        elif result.total_impacts <= 5:
            response["message"] = f"{result.total_impacts} symbols depend on '{symbol_name}' - medium risk"
        else:
            response["message"] = f"{result.total_impacts} symbols depend on '{symbol_name}' - high risk"
        
        # Add freshness info
        freshness = impact_analyzer.db.get_index_freshness()
        response["index_status"] = freshness
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "symbol_name": symbol_name,
            "total_impacts": 0,
            "error": f"Impact analysis failed: {str(e)}"
        }


@mcp.tool
@validate_params(
    valid_params={'symbol_name': str, 'path': str},
    common_errors={
        'file': "The 'file' parameter is not supported. This tool analyzes symbols across the entire indexed project.",
        'symbol': "Use 'symbol_name' instead of 'symbol' for the parameter name.",
        'name': "Use 'symbol_name' instead of 'name' for the parameter name.",
        'function': "Use 'symbol_name' for any symbol type (function, class, method).",
        'query': "Use 'symbol_name' for the exact symbol to analyze. Use find_symbol() for searching."
    }
)
def what_depends(symbol_name: str, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Find what this symbol depends on - its imports and calls.
    
    ACCEPTS ONLY:
    - symbol_name: Exact symbol name (e.g., "process_data", "UserModel")
    - path: Repository path (default: ".")
    
    COMMON MISTAKES:
    ❌ what_depends(file="main.py", symbol_name="main") - NO 'file' parameter!
    ❌ what_depends("utils.helper") - Use just "helper", not dotted paths
    ❌ what_depends(function="validate") - Parameter is 'symbol_name'
    
    CORRECT USAGE:
    ✓ what_depends(symbol_name="process_data", path="/my/project")
    ✓ what_depends(symbol_name="UserModel")
    ✓ what_depends(symbol_name="main")
    
    NOTE: Shows what THIS symbol needs, not what needs IT.
    For reverse, use what_breaks().
    
    COMMON ERRORS:
    1. "Unexpected keyword argument 'file'" → Remove 'file' parameter. This tool analyzes symbols across the entire project.
    2. "Symbol not found" → Ensure the symbol name is exact (case-sensitive) and exists in the indexed code.
    3. "Empty symbol name provided" → The 'symbol_name' parameter is required and must be non-empty.
    4. Confusing with what_breaks() → This shows dependencies OF the symbol, not what depends ON it.
    
    Returns:
        Dictionary with:
        - direct_dependencies: What this symbol imports/calls
        - total_dependencies: Count
        - dependency_types: Breakdown by import/call/etc
        - index_status: Freshness info (CHECK is_stale!)
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not symbol_name.strip():
            return {
                "symbol_name": symbol_name,
                "total_dependencies": 0,
                "error": "Empty symbol name provided"
            }
        
        impact_analyzer = get_impact_analyzer(path)
        result = impact_analyzer.analyze_dependencies(symbol_name)
        
        response = result.to_dict()
        
        if result.direct_dependencies:
            response["message"] = f"'{symbol_name}' depends on {len(result.direct_dependencies)} symbol{'s' if len(result.direct_dependencies) > 1 else ''}"
        else:
            response["message"] = f"'{symbol_name}' has no dependencies - it's self-contained"
        
        # Add freshness info
        freshness = impact_analyzer.db.get_index_freshness()
        response["index_status"] = freshness
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "symbol_name": symbol_name,
            "total_dependencies": 0,
            "error": f"Dependency analysis failed: {str(e)}"
        }


@mcp.tool
@validate_params(
    valid_params={'file': str, 'line': int, 'path': str},
    common_errors={
        'file_path': "Use 'file' instead of 'file_path' for the parameter name.",
        'filename': "Use 'file' instead of 'filename' for the parameter name.",
        'line_number': "Use 'line' instead of 'line_number' for the parameter name.",
        'lineno': "Use 'line' instead of 'lineno' for the parameter name.",
        'column': "Column information is not needed. Use only 'file' and 'line' parameters."
    }
)
def get_info(file: str, line: int, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Get symbol at specific file location - "What is at this line?"
    Finds the symbol definition or reference at an exact file:line location.
    Essential for understanding what's defined at a specific location.
    
    WHEN TO USE:
    - You have a file path and line number
    - Want to know what symbol is defined there
    - Need context about a specific location
    
    IMPORTANT: Uses indexed data. Check 'index_status.is_stale'.
    
    Args:
        file: File path relative to repository root (e.g., "src/main.py")
        line: Line number (1-based, e.g., 42)
        path: Repository path to analyze (defaults to current directory)
        
    COMMON ERRORS:
    1. "Empty file path provided" → The 'file' parameter must be a non-empty path string.
    2. "Line number must be >= 1" → Line numbers start at 1, not 0.
    3. Using absolute paths → Use paths relative to the repository root (e.g., "src/main.py" not "/home/user/project/src/main.py").
    4. "No symbol found at location" → Not every line has a symbol definition. Try nearby lines.
        
    Returns:
        Dictionary with:
        - symbol: Symbol info if found (name, kind, signature)
        - message: Human-readable result
        - index_status: Freshness information
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not file.strip():
            return {
                "file": file,
                "line": line,
                "symbol": None,
                "error": "Empty file path provided"
            }
        
        if line < 1:
            return {
                "file": file,
                "line": line,
                "symbol": None,
                "error": "Line number must be >= 1"
            }
        
        query_engine = get_query_engine(path)
        result = query_engine.get_symbol_at_location(file, line)
        
        response = result.to_dict()
        
        if result.symbol:
            response["message"] = f"Found {result.symbol['kind']} '{result.symbol['name']}' at {file}:{line}"
        else:
            response["message"] = f"No symbol found at {file}:{line}"
        
        # Add freshness info
        freshness = query_engine.db.get_index_freshness()
        response["index_status"] = freshness
        
        return add_self_analysis_warning(response, path)
        
    except Exception as e:
        return {
            "file": file,
            "line": line,
            "symbol": None,
            "error": f"Location query failed: {str(e)}"
        }


@mcp.tool
@validate_params(
    valid_params={'path': str},
    common_errors={
        'directory': "Use 'path' instead of 'directory' for the parameter name.",
        'repo': "Use 'path' instead of 'repo' for the parameter name.",
        'project': "Use 'path' instead of 'project' for the parameter name."
    }
)
def get_stats(path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Get database statistics and check index health.
    Returns comprehensive statistics about the current index. Use this to:
    - Check if an index exists
    - See index freshness/staleness
    - Get symbol counts by type
    - Monitor database size
    
    WHEN TO USE:
    - Before running queries to check index exists
    - To verify index health
    - To understand codebase metrics
    
    Args:
        path: Repository path to get stats for (defaults to current directory)
    
    COMMON ERRORS:
    1. "No index available" → Run build_index() first to create the database.
    2. Index is stale → Check 'index_status.is_stale' and rebuild if needed.
    
    Returns:
        Dictionary with:
        - database: Symbol/edge counts, size in KB
        - symbol_breakdown: Counts by type (function, class, etc)
        - index_available: Whether index exists
        - index_status: DETAILED freshness information
        - message: Human-readable summary
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        indexer = get_indexer(path)
        query_engine = get_query_engine(path)
        
        # Get basic database stats
        db_stats = indexer.get_database_stats()
        
        # Get detailed statistics from query engine
        detailed_stats = query_engine.get_statistics()
        
        # Combine and enhance
        stats = {
            "database": {
                "symbols_count": db_stats["symbols_count"],
                "edges_count": db_stats["edges_count"],
                "database_size_kb": db_stats["database_size_kb"],
                "database_path": db_stats["database_path"]
            },
            "symbol_breakdown": detailed_stats.get("symbol_kinds", {}),
            "supported_languages": indexer.get_supported_languages(),
            "index_available": indexer.is_index_available(),
            "repository_path": normalize_path(path)
        }
        
        # Add summary message
        if stats["index_available"]:
            total_symbols = db_stats["symbols_count"]
            total_files = len(set(detailed_stats.get("symbol_kinds", {}).keys()))
            stats["message"] = f"Index contains {total_symbols} symbols with {db_stats['edges_count']} dependency edges"
        else:
            stats["message"] = "No index available - run build_index first"
        
        # Add freshness info
        freshness = indexer.db.get_index_freshness()
        stats["index_status"] = freshness
        
        return add_self_analysis_warning(stats, path)
        
    except Exception as e:
        return {
            "error": f"Failed to get statistics: {str(e)}",
            "index_available": False
        }


def main():
    """Main entry point for the MCP server."""
    if __name__ == "__main__":
        mcp.run()


@mcp.tool
def analyze_multiple_symbols(symbol_names: List[str], max_depth: int = 5, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Batch analyze impact for multiple symbols - EFFICIENT for refactoring.
    Analyzes multiple symbols in one call, perfect for understanding
    the impact of changing multiple related functions/classes.
    
    WHEN TO USE:
    - Refactoring multiple related functions
    - Analyzing a whole module/class
    - Understanding interconnected changes
    
    IMPORTANT: Uses indexed data. Check 'index_status.is_stale'.
    
    Args:
        symbol_names: List of symbol names to analyze (e.g., ["UserService", "AuthManager"])
        max_depth: How deep to trace dependencies (default: 5)
        path: Repository path to analyze (defaults to current directory)
        
    Returns:
        Dictionary with:
        - results: Impact analysis for each symbol
        - total_symbols: Number analyzed
        - index_status: Freshness information
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not symbol_names or not isinstance(symbol_names, list):
            return {
                "error": "symbol_names must be a non-empty list",
                "results": {}
            }
        
        impact_analyzer = get_impact_analyzer(path)
        results = impact_analyzer.analyze_multiple_impacts(symbol_names, max_depth)
        
        # Convert to serializable format
        serialized_results = {}
        for symbol_name, result in results.items():
            serialized_results[symbol_name] = result.to_dict()
        
        # Add freshness info
        freshness = impact_analyzer.db.get_index_freshness()
        
        return {
            "total_symbols": len(symbol_names),
            "results": serialized_results,
            "message": f"Analyzed {len(symbol_names)} symbols successfully",
            "index_status": freshness
        }
        
    except Exception as e:
        return {
            "error": f"Batch analysis failed: {str(e)}",
            "results": {}
        }


@mcp.tool
def get_project_overview(path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Get project-wide analysis - find the MOST CRITICAL code to be careful with.
    Analyzes the entire project to identify:
    - Most depended-upon symbols (high risk if changed)
    - Tightly coupled areas
    - Architectural bottlenecks
    
    WHEN TO USE:
    - Starting a major refactoring
    - Understanding project architecture
    - Finding risky areas before changes
    
    IMPORTANT: Uses indexed data. Check 'index_status.is_stale'.
    
    Args:
        path: Repository path to analyze (defaults to current directory)
    
    Returns:
        Dictionary with:
        - summary: Project metrics and critical symbols
        - detailed_impacts: Top symbols by impact
        - insights: Risk assessments
        - index_status: Freshness information
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        impact_analyzer = get_impact_analyzer(path)
        overview = impact_analyzer.analyze_project_wide_impact(max_symbols=50)
        
        overview["message"] = f"Analyzed {overview['summary']['total_symbols_analyzed']} critical symbols"
        overview["insights"] = [
            f"Project coupling score: {overview['summary']['project_coupling_score']:.2f}",
            f"High-risk symbols: {len(overview['summary']['high_risk_symbols'])}",
            f"Most critical files: {len(overview['summary']['most_critical_files'])}"
        ]
        
        # Add freshness info
        freshness = impact_analyzer.db.get_index_freshness()
        overview["index_status"] = freshness
        
        return add_self_analysis_warning(overview, path)
        
    except Exception as e:
        return {
            "error": f"Project overview failed: {str(e)}",
            "summary": {},
            "detailed_impacts": {}
        }


@mcp.tool
def get_dependency_graph(symbol_names: List[str], path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Get full dependency graph - see ALL connections between symbols.
    Shows complete bidirectional dependencies:
    - What each symbol depends on (imports, calls)
    - What depends on each symbol (usage)
    - Coupling metrics for architecture decisions
    
    WHEN TO USE:
    - Architectural analysis
    - Planning module boundaries
    - Understanding coupling between components
    
    IMPORTANT: Uses indexed data. Check 'index_status.is_stale'.
    
    Args:
        symbol_names: List of symbols to analyze (e.g., ["Database", "Cache", "Logger"])
        path: Repository path to analyze (defaults to current directory)
        
    Returns:
        Dictionary with:
        - dependency_graph: Full graph for each symbol
        - summary: Aggregate metrics
        - index_status: Freshness information
    """
    try:
        # Normalize path once at entry point
        path = normalize_path(path)
        
        if not symbol_names or not isinstance(symbol_names, list):
            return {
                "error": "symbol_names must be a non-empty list",
                "dependency_graph": {}
            }
        
        impact_analyzer = get_impact_analyzer(path)
        graph = impact_analyzer.get_dependency_graph_for_symbols(symbol_names)
        
        # Add summary statistics
        total_dependencies = sum(len(data['dependencies']['dependencies']) for data in graph.values())
        total_impacts = sum(data['impacts']['total_impacts'] for data in graph.values())
        
        # Add freshness info
        freshness = impact_analyzer.db.get_index_freshness()
        
        return {
            "dependency_graph": graph,
            "summary": {
                "symbols_analyzed": len(symbol_names),
                "total_dependencies": total_dependencies,
                "total_impacts": total_impacts,
                "average_coupling": (total_dependencies + total_impacts) / len(symbol_names) if symbol_names else 0
            },
            "message": f"Generated dependency graph for {len(symbol_names)} symbols",
            "index_status": freshness
        }
        
    except Exception as e:
        return {
            "error": f"Dependency graph generation failed: {str(e)}",
            "dependency_graph": {}
        }


if __name__ == "__main__":
    main()