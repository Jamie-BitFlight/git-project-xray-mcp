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

# Global components (initialized on first use)
_indexer: Optional[XRayIndexer] = None
_query_engine: Optional[XRayQueryEngine] = None
_impact_analyzer: Optional[XRayImpactAnalyzer] = None


def get_repo_path() -> str:
    """Get the current working directory as repo path."""
    return os.getcwd()


def get_indexer() -> XRayIndexer:
    """Get or create indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = XRayIndexer(get_repo_path())
    return _indexer


def get_query_engine() -> XRayQueryEngine:
    """Get or create query engine instance."""
    global _query_engine
    if _query_engine is None:
        _query_engine = XRayQueryEngine(get_repo_path())
    return _query_engine


def get_impact_analyzer() -> XRayImpactAnalyzer:
    """Get or create impact analyzer instance."""
    global _impact_analyzer
    if _impact_analyzer is None:
        _impact_analyzer = XRayImpactAnalyzer(get_repo_path())
    return _impact_analyzer


@mcp.tool
def build_index(path: str = ".") -> dict:
    """Rebuild the code intelligence database.
    
    This tool walks the directory tree, parses all supported source files,
    extracts symbols (functions, classes, methods, imports), and builds
    a dependency graph for fast querying and impact analysis.
    
    Args:
        path: Directory path to index (defaults to current directory)
        
    Returns:
        Dictionary with indexing results and statistics
    """
    try:
        indexer = get_indexer()
        result = indexer.build_index(path)
        
        # Add some additional context to the result
        response = result.to_dict()
        response["message"] = "Index built successfully" if result.success else "Index build failed"
        
        if result.success:
            response["summary"] = f"Indexed {result.files_indexed} files, found {result.symbols_found} symbols, created {result.edges_created} dependency edges"
            
            if result.errors:
                response["warnings"] = result.errors
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to build index: {str(e)}",
            "files_indexed": 0,
            "symbols_found": 0,
            "edges_created": 0
        }


@mcp.tool
def find_symbol(query: str, limit: int = 50) -> dict:
    """Search for symbols by name substring.
    
    Performs fast symbol search with intelligent ranking:
    - Exact matches first
    - Prefix matches second
    - Substring matches last
    
    Args:
        query: Symbol name or partial name to search for
        limit: Maximum number of results to return (default: 50)
        
    Returns:
        Dictionary with search results and metadata
    """
    try:
        if not query.strip():
            return {
                "query": query,
                "total_matches": 0,
                "symbols": [],
                "message": "Empty query provided"
            }
        
        query_engine = get_query_engine()
        result = query_engine.find_symbols(query, limit)
        
        response = result.to_dict()
        
        if result.total_matches == 0:
            response["message"] = f"No symbols found matching '{query}'"
        elif result.total_matches == 1:
            response["message"] = f"Found 1 symbol matching '{query}'"
        else:
            response["message"] = f"Found {result.total_matches} symbols matching '{query}'"
        
        return response
        
    except Exception as e:
        return {
            "query": query,
            "total_matches": 0,
            "symbols": [],
            "error": f"Search failed: {str(e)}"
        }


@mcp.tool  
def what_breaks(symbol_name: str, max_depth: int = 5) -> dict:
    """Find what depends on this symbol (THE KILLER FEATURE).
    
    Performs breadth-first search to find all symbols that transitively
    depend on the given symbol. This answers the critical question:
    "What breaks if I change this function/class/method?"
    
    Args:
        symbol_name: Name of the symbol to analyze
        max_depth: Maximum depth for transitive analysis (default: 5)
        
    Returns:
        Dictionary with complete impact analysis
    """
    try:
        if not symbol_name.strip():
            return {
                "symbol_name": symbol_name,
                "total_impacts": 0,
                "error": "Empty symbol name provided"
            }
        
        impact_analyzer = get_impact_analyzer()
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
        
        return response
        
    except Exception as e:
        return {
            "symbol_name": symbol_name,
            "total_impacts": 0,
            "error": f"Impact analysis failed: {str(e)}"
        }


@mcp.tool
def what_depends(symbol_name: str) -> dict:
    """Find what this symbol depends on.
    
    Shows the direct dependencies of a symbol - what imports, function calls,
    and other references this symbol uses. Helps understand the requirements
    and coupling of a symbol.
    
    Args:
        symbol_name: Name of the symbol to analyze
        
    Returns:
        Dictionary with dependency information
    """
    try:
        if not symbol_name.strip():
            return {
                "symbol_name": symbol_name,
                "total_dependencies": 0,
                "error": "Empty symbol name provided"
            }
        
        impact_analyzer = get_impact_analyzer()
        result = impact_analyzer.analyze_dependencies(symbol_name)
        
        response = result.to_dict()
        
        if result.direct_dependencies:
            response["message"] = f"'{symbol_name}' depends on {len(result.direct_dependencies)} symbol{'s' if len(result.direct_dependencies) > 1 else ''}"
        else:
            response["message"] = f"'{symbol_name}' has no dependencies - it's self-contained"
        
        return response
        
    except Exception as e:
        return {
            "symbol_name": symbol_name,
            "total_dependencies": 0,
            "error": f"Dependency analysis failed: {str(e)}"
        }


@mcp.tool
def get_info(file: str, line: int) -> dict:
    """Get symbol at specific file location.
    
    Finds the symbol definition or reference at an exact file:line location.
    Essential for "what is this?" queries when you know the location but
    want to understand what symbol is defined there.
    
    Args:
        file: File path (relative to repository root)
        line: Line number (1-based)
        
    Returns:
        Dictionary with symbol information if found
    """
    try:
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
        
        query_engine = get_query_engine()
        result = query_engine.get_symbol_at_location(file, line)
        
        response = result.to_dict()
        
        if result.symbol:
            response["message"] = f"Found {result.symbol['kind']} '{result.symbol['name']}' at {file}:{line}"
        else:
            response["message"] = f"No symbol found at {file}:{line}"
        
        return response
        
    except Exception as e:
        return {
            "file": file,
            "line": line,
            "symbol": None,
            "error": f"Location query failed: {str(e)}"
        }


@mcp.tool
def get_stats() -> dict:
    """Get XRAY database and indexing statistics.
    
    Returns comprehensive statistics about the current index including
    symbol counts, database size, supported languages, and performance metrics.
    
    Returns:
        Dictionary with detailed statistics
    """
    try:
        indexer = get_indexer()
        query_engine = get_query_engine()
        
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
            "repository_path": get_repo_path()
        }
        
        # Add summary message
        if stats["index_available"]:
            total_symbols = db_stats["symbols_count"]
            total_files = len(set(detailed_stats.get("symbol_kinds", {}).keys()))
            stats["message"] = f"Index contains {total_symbols} symbols with {db_stats['edges_count']} dependency edges"
        else:
            stats["message"] = "No index available - run build_index first"
        
        return stats
        
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
def analyze_multiple_symbols(symbol_names: List[str], max_depth: int = 5) -> dict:
    """Analyze impact for multiple symbols in batch (LLM-optimized).
    
    Performs impact analysis for multiple symbols at once, providing
    comprehensive dependency information for LLM decision-making.
    
    Args:
        symbol_names: List of symbol names to analyze
        max_depth: Maximum depth for transitive analysis (default: 5)
        
    Returns:
        Dictionary with impact analysis for each symbol
    """
    try:
        if not symbol_names or not isinstance(symbol_names, list):
            return {
                "error": "symbol_names must be a non-empty list",
                "results": {}
            }
        
        impact_analyzer = get_impact_analyzer()
        results = impact_analyzer.analyze_multiple_impacts(symbol_names, max_depth)
        
        # Convert to serializable format
        serialized_results = {}
        for symbol_name, result in results.items():
            serialized_results[symbol_name] = result.to_dict()
        
        return {
            "total_symbols": len(symbol_names),
            "results": serialized_results,
            "message": f"Analyzed {len(symbol_names)} symbols successfully"
        }
        
    except Exception as e:
        return {
            "error": f"Batch analysis failed: {str(e)}",
            "results": {}
        }


@mcp.tool
def get_project_overview() -> dict:
    """Get comprehensive project-wide impact analysis (LLM-optimized).
    
    Provides a complete overview of the most critical symbols in the project,
    their interconnections, and risk assessment. Perfect for LLM-driven
    architectural analysis and refactoring decisions.
    
    Returns:
        Dictionary with project-wide analysis and critical symbols
    """
    try:
        impact_analyzer = get_impact_analyzer()
        overview = impact_analyzer.analyze_project_wide_impact(max_symbols=50)
        
        overview["message"] = f"Analyzed {overview['summary']['total_symbols_analyzed']} critical symbols"
        overview["insights"] = [
            f"Project coupling score: {overview['summary']['project_coupling_score']:.2f}",
            f"High-risk symbols: {len(overview['summary']['high_risk_symbols'])}",
            f"Most critical files: {len(overview['summary']['most_critical_files'])}"
        ]
        
        return overview
        
    except Exception as e:
        return {
            "error": f"Project overview failed: {str(e)}",
            "summary": {},
            "detailed_impacts": {}
        }


@mcp.tool
def get_dependency_graph(symbol_names: List[str]) -> dict:
    """Get complete dependency graph for multiple symbols (LLM-optimized).
    
    Provides comprehensive dependency information including both what each
    symbol depends on and what depends on it, along with coupling metrics
    for architectural analysis.
    
    Args:
        symbol_names: List of symbol names to analyze
        
    Returns:
        Complete dependency graph with coupling metrics
    """
    try:
        if not symbol_names or not isinstance(symbol_names, list):
            return {
                "error": "symbol_names must be a non-empty list",
                "dependency_graph": {}
            }
        
        impact_analyzer = get_impact_analyzer()
        graph = impact_analyzer.get_dependency_graph_for_symbols(symbol_names)
        
        # Add summary statistics
        total_dependencies = sum(len(data['dependencies']['dependencies']) for data in graph.values())
        total_impacts = sum(data['impacts']['total_impacts'] for data in graph.values())
        
        return {
            "dependency_graph": graph,
            "summary": {
                "symbols_analyzed": len(symbol_names),
                "total_dependencies": total_dependencies,
                "total_impacts": total_impacts,
                "average_coupling": (total_dependencies + total_impacts) / len(symbol_names) if symbol_names else 0
            },
            "message": f"Generated dependency graph for {len(symbol_names)} symbols"
        }
        
    except Exception as e:
        return {
            "error": f"Dependency graph generation failed: {str(e)}",
            "dependency_graph": {}
        }


if __name__ == "__main__":
    main()