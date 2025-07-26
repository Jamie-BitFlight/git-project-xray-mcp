#!/usr/bin/env python3
"""Test script for XRAY parsers."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from xray.core.indexer import XRayIndexer

def test_parsers():
    """Test all parsers with sample files."""
    print("Testing XRAY parsers...")
    
    # Create indexer for test samples
    test_dir = os.path.join(os.path.dirname(__file__), 'test_samples')
    indexer = XRayIndexer(test_dir)
    
    # Get supported languages
    languages = indexer.get_supported_languages()
    print(f"\nSupported languages: {', '.join(languages)}")
    
    # Build index
    print(f"\nBuilding index for: {test_dir}")
    result = indexer.build_index()
    
    if result.success:
        print(f"\n✓ Index built successfully!")
        print(f"  - Files indexed: {result.files_indexed}")
        print(f"  - Symbols found: {result.symbols_found}")
        print(f"  - Edges created: {result.edges_created}")
        print(f"  - Duration: {result.duration_seconds:.3f}s")
        
        if result.errors:
            print(f"\nWarnings:")
            for error in result.errors:
                print(f"  - {error}")
        
        # Get statistics
        stats = indexer.get_database_stats()
        print(f"\nDatabase statistics:")
        print(f"  - Total symbols: {stats['symbols_count']}")
        print(f"  - Total edges: {stats['edges_count']}")
        print(f"  - Database size: {stats['database_size_kb']:.2f} KB")
        
        # Test queries
        from xray.core.query import XRayQueryEngine
        query_engine = XRayQueryEngine(test_dir)
        
        print("\nTesting symbol search...")
        test_queries = ['User', 'process', 'Service', 'fetch']
        for query in test_queries:
            result = query_engine.find_symbols(query, limit=5)
            print(f"\n  Query '{query}': {result.total_matches} matches")
            for symbol in result.symbols[:3]:  # Show first 3
                print(f"    - {symbol['name']} ({symbol['kind']}) in {symbol['file']}:{symbol['line']}")
    else:
        print(f"\n✗ Index build failed!")
        for error in result.errors:
            print(f"  - {error}")

if __name__ == "__main__":
    test_parsers()