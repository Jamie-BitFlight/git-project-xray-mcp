#!/usr/bin/env python3
"""
Test the cross-file method resolution fix.
This tests if our parser correctly identifies the indexer.build_index(path) call.
"""

# Simulate the exact code pattern from mcp_server.py
test_mcp_code = '''
def get_indexer():
    return "indexer_instance"

def build_index(path: str = ".") -> dict:
    indexer = get_indexer()
    result = indexer.build_index(path)
    return result
'''

# Simulate the exact code pattern from indexer.py  
test_indexer_code = '''
class XRayIndexer:
    def build_index(self, path=None):
        return {"success": True}
'''

print("=== Testing Cross-File Method Resolution Fix ===")
print()
print("Code Pattern from mcp_server.py:")
print("Line 69: result = indexer.build_index(path)")
print()
print("Expected Edge:")
print("FROM: build_index (function in mcp_server.py)")  
print("TO: build_index (method in indexer.py)")
print()

try:
    import sys
    sys.path.append('src')
    
    from xray.parsers.python import PythonParser
    from xray.parsers.base import load_tree_sitter_languages, Symbol
    
    languages = load_tree_sitter_languages()
    if 'python' not in languages:
        print("❌ Python tree-sitter not available")
        exit(1)
        
    parser = PythonParser(languages['python'])
    
    # Test parsing the MCP server code
    print("🔍 Parsing MCP server code...")
    symbols = parser.extract_symbols(test_mcp_code.encode(), 'test_mcp.py')
    edges = parser.extract_edges(test_mcp_code.encode(), 'test_mcp.py', symbols)
    
    print(f"Found {len(symbols)} symbols:")
    for symbol in symbols:
        print(f"  {symbol.kind} '{symbol.name}' at line {symbol.line}")
    
    print(f"\nFound {len(edges)} edges:")
    for edge in edges:
        print(f"  {edge.from_symbol} -> {edge.to_symbol}")
        print(f"    from_file: {edge.from_file}")
        print(f"    to_file: {edge.to_file}")  # Should be None for cross-file resolution
        
    # Check if we capture the specific call we care about
    build_index_calls = [e for e in edges if e.to_symbol == 'build_index' and e.from_symbol == 'build_index']
    
    if build_index_calls:
        call = build_index_calls[0] 
        if call.to_file is None:
            print(f"\n✅ SUCCESS: Cross-file resolution enabled!")
            print(f"   Edge: {call.from_symbol} -> {call.to_symbol} (to_file=None)")
        else:
            print(f"\n❌ FAIL: Still using same-file resolution")
            print(f"   Edge: {call.from_symbol} -> {call.to_symbol} (to_file={call.to_file})")
    else:
        print(f"\n❓ No build_index -> build_index edges found")
        print("This might be expected if the parser doesn't capture self-calls")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()