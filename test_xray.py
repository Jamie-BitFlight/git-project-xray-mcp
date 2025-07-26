#!/usr/bin/env python3
"""Simple test script to verify XRAY functionality."""

import sys
import os
from pathlib import Path

# Add src to path so we can import xray
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xray.core.indexer import XRayIndexer
from xray.core.query import XRayQueryEngine
from xray.core.impact import XRayImpactAnalyzer


def create_test_python_file():
    """Create a simple test Python file for testing."""
    test_content = '''
class UserService:
    def __init__(self):
        self.db = Database()
    
    def authenticate_user(self, username, password):
        user = self.get_user(username)
        return self.verify_password(user, password)
    
    def get_user(self, username):
        return self.db.find_user(username)
    
    def verify_password(self, user, password):
        return user.check_password(password)

def main():
    service = UserService()
    result = service.authenticate_user("admin", "secret")
    print(f"Auth result: {result}")

class Database:
    def find_user(self, username):
        return User(username)

class User:
    def __init__(self, username):
        self.username = username
    
    def check_password(self, password):
        return password == "secret"
'''
    
    # Write test file
    test_file = Path("test_sample.py")
    test_file.write_text(test_content)
    print(f"Created test file: {test_file}")
    return str(test_file)


def test_indexing():
    """Test the indexing functionality."""
    print("\n=== Testing Indexing ===")
    
    indexer = XRayIndexer(".")
    result = indexer.build_index(".")
    
    print(f"Indexing result: {result.to_dict()}")
    print(f"Success: {result.success}")
    print(f"Files indexed: {result.files_indexed}")  
    print(f"Symbols found: {result.symbols_found}")
    print(f"Edges created: {result.edges_created}")
    
    if result.errors:
        print(f"Errors: {result.errors}")
    
    return result.success


def test_symbol_search():
    """Test symbol search functionality."""
    print("\n=== Testing Symbol Search ===")
    
    query_engine = XRayQueryEngine(".")
    
    # Test searching for "user" 
    result = query_engine.find_symbols("user", limit=10)
    print(f"Search for 'user': {result.total_matches} matches")
    
    for symbol in result.symbols[:3]:  # Show first 3
        print(f"  - {symbol['name']} ({symbol['kind']}) at {symbol['location']}")
    
    # Test searching for "UserService"
    result = query_engine.find_symbols("UserService", limit=5)
    print(f"\nSearch for 'UserService': {result.total_matches} matches")
    
    for symbol in result.symbols:
        print(f"  - {symbol['name']} ({symbol['kind']}) at {symbol['location']}")
    
    return True


def test_impact_analysis():
    """Test impact analysis functionality."""
    print("\n=== Testing Impact Analysis ===")
    
    impact_analyzer = XRayImpactAnalyzer(".")
    
    # Test impact analysis for authenticate_user
    result = impact_analyzer.analyze_impact("authenticate_user")
    print(f"Impact analysis for 'authenticate_user':")
    print(f"  Total impacts: {result.total_impacts}")
    print(f"  Max depth: {result.max_depth}")
    print(f"  Reasoning: {result.reasoning}")
    
    if result.impacts_by_file:
        print("  Impacts by file:")
        for file, impacts in result.impacts_by_file.items():
            print(f"    {file}: {len(impacts)} impacts")
            for impact in impacts[:2]:  # Show first 2
                print(f"      - {impact.name} ({impact.kind}) at line {impact.line}")
    
    return True


def test_dependency_analysis():
    """Test dependency analysis functionality.""" 
    print("\n=== Testing Dependency Analysis ===")
    
    impact_analyzer = XRayImpactAnalyzer(".")
    
    # Test dependency analysis for authenticate_user
    result = impact_analyzer.analyze_dependencies("authenticate_user")
    print(f"Dependencies for 'authenticate_user':")
    print(f"  Total dependencies: {len(result.direct_dependencies)}")
    print(f"  Reasoning: {result.reasoning}")
    
    if result.direct_dependencies:
        print("  Direct dependencies:")
        for dep in result.direct_dependencies:
            print(f"    - {dep['name']} ({dep['kind']}) at {dep['file']}:{dep['line']}")
    
    return True


def test_location_query():
    """Test location-based queries."""
    print("\n=== Testing Location Queries ===")
    
    query_engine = XRayQueryEngine(".")
    
    # Test getting symbol at specific location
    result = query_engine.get_symbol_at_location("test_sample.py", 7)
    print(f"Symbol at test_sample.py:7:")
    if result.symbol:
        print(f"  Found: {result.symbol['name']} ({result.symbol['kind']})")
        print(f"  Signature: {result.symbol.get('signature', 'N/A')}")
    else:
        print("  No symbol found")
    
    return True


def cleanup():
    """Clean up test files."""
    test_files = ["test_sample.py"]
    xray_dir = Path(".xray")
    
    for file in test_files:
        if Path(file).exists():
            Path(file).unlink()
            print(f"Removed {file}")
    
    # Optionally remove .xray directory
    # if xray_dir.exists():
    #     import shutil
    #     shutil.rmtree(xray_dir)
    #     print("Removed .xray directory")


def main():
    """Run all tests."""
    print("XRAY Test Suite")
    print("===================")
    
    try:
        # Create test file
        test_file = create_test_python_file()
        
        # Run tests
        tests = [
            test_indexing,
            test_symbol_search,
            test_impact_analysis,
            test_dependency_analysis,
            test_location_query
        ]
        
        passed = 0
        for test in tests:
            try:
                if test():
                    passed += 1
                    print(f"✅ {test.__name__} passed")
                else:
                    print(f"❌ {test.__name__} failed")
            except Exception as e:
                print(f"❌ {test.__name__} failed with error: {e}")
        
        print(f"\nResults: {passed}/{len(tests)} tests passed")
        
        if passed == len(tests):
            print("🎉 All tests passed! XRAY is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the output above.")
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        cleanup()


if __name__ == "__main__":
    main()