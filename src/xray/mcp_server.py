"""FastMCP server for XRAY code intelligence."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastmcp import FastMCP

from .core.indexer import XRayIndexer
from .core.query import XRayQueryEngine
from .core.impact import XRayImpactAnalyzer


# Initialize FastMCP server
mcp = FastMCP("XRAY Code Intelligence")

# Cache for components per repository path
_component_cache: Dict[str, Dict[str, any]] = {}


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
        print("You are analyzing the xray-lite MCP implementation itself.", file=sys.stderr)
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
def find_symbol(query: str, limit: int = 50, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Search for symbols by name substring.
    Performs fast symbol search with intelligent ranking:
    - Exact matches first
    - Prefix matches second
    - Substring matches last
    
    IMPORTANT: This searches the INDEXED database, not live code.
    Check 'index_status' in response to see if index is STALE.
    If stale, consider running build_index first.
    
    Args:
        query: Symbol name or partial name to search for
        limit: Maximum number of results to return (default: 50)
        path: Repository path to search in (defaults to current directory)
        
    Returns:
        Dictionary with search results and metadata.
        ALWAYS includes 'index_status' with freshness information.
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
def what_breaks(symbol_name: str, max_depth: int = 5, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Find what depends on this symbol (THE KILLER FEATURE).
    Performs breadth-first search to find all symbols that transitively
    depend on the given symbol. This answers the critical question:
    "What breaks if I change this function/class/method?"
    
    IMPORTANT: This analyzes the INDEXED database, not live code.
    Check 'index_status' in response to see if index is STALE.
    If stale, the impact analysis may be outdated - run build_index first.
    
    Args:
        symbol_name: Name of the symbol to analyze
        max_depth: Maximum depth for transitive analysis (default: 5)
        path: Repository path to analyze (defaults to current directory)
        
    Returns:
        Dictionary with complete impact analysis.
        ALWAYS includes 'index_status' with freshness information.
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
def what_depends(symbol_name: str, path: str = ".") -> dict:
    """ALWAYS specify path='/your/project' - don't analyze xray itself!
    
    Find what this symbol depends on.
    Shows the direct dependencies of a symbol - what imports, function calls,
    and other references this symbol uses. Helps understand the requirements
    and coupling of a symbol.
    
    IMPORTANT: This analyzes the INDEXED database, not live code.
    Check 'index_status' in response to see if index is STALE.
    If stale, dependencies may have changed - run build_index first.
    
    Args:
        symbol_name: Name of the symbol to analyze
        path: Repository path to analyze (defaults to current directory)
        
    Returns:
        Dictionary with dependency information.
        ALWAYS includes 'index_status' with freshness information.
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