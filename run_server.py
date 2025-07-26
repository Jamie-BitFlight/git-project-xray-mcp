#!/usr/bin/env python3
"""Simple runner for XRAY-Lite MCP server."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xray.mcp_server import mcp

if __name__ == "__main__":
    print("Starting XRAY-Lite MCP Server...")
    print("Available tools:")
    print("  - build_index(path): Rebuild code intelligence database")
    print("  - find_symbol(query, limit): Search symbols by name")
    print("  - what_breaks(symbol_name, max_depth): Impact analysis")
    print("  - what_depends(symbol_name): Dependency analysis") 
    print("  - get_info(file, line): Get symbol at location")
    print("  - get_stats(): Get database statistics")
    print()
    print("Server running on STDIO transport...")
    
    mcp.run()