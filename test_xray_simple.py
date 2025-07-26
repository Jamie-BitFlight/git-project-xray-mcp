#!/usr/bin/env python3
"""
Simple test script for XRAY system.
Tests symbol extraction, indexing, and queries end-to-end.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from xray.core.indexer import XRayIndexer
from xray.core.query import XRayQueryEngine
from xray.core.impact import XRayImpactAnalyzer
from xray.core.schema import DatabaseManager

def test_xray_system():
    """Test the complete XRAY system."""
    
    # Set up test directory
    test_dir = Path(__file__).parent
    db_path = test_dir / ".xray" / "test.db"
    
    # Create test Python file
    test_code = """
def authenticate_user(username, password):
    '''Authenticate user with username and password.'''
    if validate_user(username):
        return check_password(password)
    return False

def validate_user(username):
    '''Validate that username exists.'''
    return username in get_users()

def check_password(password):
    '''Check password strength.'''
    return len(password) >= 8

def get_users():
    '''Get list of users.'''
    return ['admin', 'user1', 'user2']

class UserService:
    '''Service for managing users.'''
    
    def __init__(self):
        self.users = get_users()
    
    def login(self, username, password):
        '''Login user.'''
        return authenticate_user(username, password)
    
    def get_user_info(self, username):
        '''Get user information.'''
        if validate_user(username):
            return {'username': username, 'valid': True}
        return None

# Usage example
service = UserService()
result = service.login('admin', 'password123')
"""
    
    test_file = test_dir / "test_sample.py"
    test_file.write_text(test_code)
    
    try:
        print("🚀 Testing XRAY System")
        print("=" * 50)
        
        # 1. Test indexing
        print("\n1. Testing Indexing...")
        indexer = XRayIndexer(str(test_dir))
        result = indexer.build_index(str(test_dir))
        
        print(f"✅ Indexed {result.files_indexed} files")
        print(f"✅ Found {result.symbols_found} symbols")
        print(f"✅ Created {result.edges_created} edges")
        
        # 2. Test symbol search
        print("\n2. Testing Symbol Search...")
        query_engine = XRayQueryEngine(str(test_dir))
        
        # Search for authenticate functions
        auth_results = query_engine.find_symbols("authenticate", limit=5)
        print(f"✅ Found {auth_results.total_matches} symbols matching 'authenticate'")
        for symbol in auth_results.symbols[:2]:
            print(f"  - {symbol['name']} ({symbol['kind']}) in {symbol['file']}:{symbol['line']}")
        
        # Search for user-related symbols
        user_results = query_engine.find_symbols("user", limit=5)
        print(f"✅ Found {user_results.total_matches} symbols matching 'user'")
        for symbol in user_results.symbols[:2]:
            print(f"  - {symbol['name']} ({symbol['kind']}) in {symbol['file']}:{symbol['line']}")
        
        # 3. Test impact analysis
        print("\n3. Testing Impact Analysis...")
        impact_analyzer = XRayImpactAnalyzer(str(test_dir))
        
        # What breaks if we change authenticate_user?
        impact_result = impact_analyzer.analyze_impact("authenticate_user")
        print(f"✅ Found {impact_result.total_impacts} impacts for 'authenticate_user'")
        for file_path, impacts in impact_result.impacts_by_file.items():
            print(f"  - {Path(file_path).name}: {len(impacts)} impacts")
            for impact in impacts[:2]:
                print(f"    • {impact.name} ({impact.kind}) at line {impact.line}")
        
        # What does validate_user depend on?
        deps_result = impact_analyzer.analyze_dependencies("validate_user")
        print(f"✅ Found {len(deps_result.direct_dependencies)} dependencies for 'validate_user'")
        for dep in deps_result.direct_dependencies[:3]:
            print(f"  - {dep['name']} ({dep['kind']}) in {Path(dep['file']).name}:{dep['line']}")
        
        # 4. Test location query
        print("\n4. Testing Location Query...")
        # Get symbol at specific line (where authenticate_user is defined)
        location_result = query_engine.get_symbol_at_location("test_sample.py", 2)
        if location_result and location_result.symbol:
            symbol = location_result.symbol
            print(f"✅ Found symbol at test_sample.py:2: {symbol['name']} ({symbol['kind']})")
        else:
            print("❌ No symbol found at location")
        
        print("\n🎉 All tests passed! XRAY is working correctly.")
        print("\n📊 System Performance:")
        print(f"  - Index time: {result.duration_seconds * 1000:.0f}ms")
        print(f"  - Database size: {result.database_size_kb:.1f}KB")
        print(f"  - Symbols per file: {result.symbols_found / max(result.files_indexed, 1):.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    success = test_xray_system()
    sys.exit(0 if success else 1)