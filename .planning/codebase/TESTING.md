# Testing Patterns

**Analysis Date:** 2026-02-07

## Test Framework

**Runner:**
- pytest 9.0.2+
- Config: `pyproject.toml` lines 57-69
- Entry point: Tests in `tests/` directory, auto-discovered by pytest

**Assertion Library:**
- pytest's built-in assertions (no separate library)
- Pattern: `assert expression`, `assert x == y`, `assert "string" in value`

**Run Commands:**
```bash
uv run pytest tests/                                              # Run all tests
uv run pytest tests/ -xvs --no-cov                              # Verbose with early stop, no coverage
uv run pytest tests/test_file.py -xvs --no-cov                  # Single test file
uv run pytest tests/test_file.py::TestClass::test_method -xvs   # Single test method
uv run pytest tests/ --cov=xray --cov-report=html               # Coverage report (HTML)
```

**pytest Config Options (pyproject.toml):**
```toml
testpaths = ["tests"]                    # Where to find tests
python_files = ["test_*.py"]            # Naming pattern for test files
python_classes = ["Test*"]              # Naming pattern for test classes
python_functions = ["test_*"]           # Naming pattern for test functions
addopts = [
    "-v",                               # Verbose output
    "--strict-markers",                 # Fail on unknown markers
    "--tb=short",                       # Short traceback format
    "--cov=xray",                       # Coverage for xray package
    "--cov-report=term",                # Terminal coverage report
    "--cov-report=xml",                 # XML coverage for CI
]
```

## Test File Organization

**Location:**
- Pattern: `tests/` directory, parallel to `src/` at root level
- Co-located with source under `tests/test_*.py`
- One test file per main source module: `test_indexer.py` → `src/xray/core/indexer.py`, `test_mcp_server.py` → `src/xray/mcp_server.py`

**Naming:**
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>` (e.g., `TestXRayIndexer`, `TestMCPServer`)
- Test methods: `test_<functionality>` (e.g., `test_indexer_initialization`, `test_explore_repo_basic`)

**Structure:**
```
tests/
├── __init__.py              # Empty
├── test_indexer.py          # Tests for XRayIndexer (indexer.py)
└── test_mcp_server.py       # Tests for MCP server functions (mcp_server.py)
```

## Test Structure

**Suite Organization:**
```python
# tests/test_indexer.py
class TestXRayIndexer:
    """Tests for XRayIndexer functionality."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository with test files."""
        # Setup code - creates directories and test files
        (tmp_path / "src").mkdir()
        py_file = tmp_path / "src" / "example.py"
        py_file.write_text("...")
        return tmp_path

    def test_indexer_initialization(self, temp_repo):
        """Test that indexer initializes correctly."""
        # Arrange
        indexer = XRayIndexer(str(temp_repo))
        # Assert
        assert indexer.root_path == temp_repo
        assert isinstance(indexer._cache, dict)
```

**Patterns:**

1. **Setup - using pytest fixtures:**
```python
@pytest.fixture
def temp_repo(self, tmp_path):
    """Create a temporary repository for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    py_file = tmp_path / "src" / "main.py"
    py_file.write_text("""...""")
    return tmp_path
```
Fixtures provide clean test data, auto-cleaned by pytest after test completes.

2. **Teardown:**
- Implicit - pytest's `tmp_path` fixture automatically cleans up after each test
- No manual teardown needed (temporary files auto-deleted)
- Example: `temp_repo` fixture returns `tmp_path` which is managed by pytest

3. **Assertion pattern - Arrange-Act-Assert:**
```python
def test_normalize_path_makes_absolute(self, tmp_path):
    # Arrange
    path = str(tmp_path)
    # Act
    normalized = normalize_path(path)
    # Assert
    assert Path(normalized).is_absolute()
```

## Mocking

**Framework:** No mocking library - pytest built-in, not needed

**Pattern - Real file system tests:**
Tests use real temporary directories created by pytest's `tmp_path` fixture instead of mocks. Example from `test_indexer.py:11-56`:
```python
@pytest.fixture
def temp_repo(self, tmp_path):
    """Create a temporary repository with test files."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create real Python file
    py_file = tmp_path / "src" / "example.py"
    py_file.write_text('''"""Example module."""

def hello_world():
    """Say hello."""
    return "Hello, World!"
''')

    # Create real gitignore
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\nnode_modules/\n")

    return tmp_path
```

**What NOT to Mock:**
- File system operations - use `tmp_path` instead
- External tools that can be tested with real data - test with actual subprocess calls
- Data structures - test with real data

**What to Test with Real Data:**
- File system traversal: `_should_exclude()` tested with real paths
- Symbol extraction: tested against real Python, JS, Go files
- gitignore parsing: tested with real `.gitignore` file

## Fixtures and Factories

**Test Data:**
```python
# Fixture pattern - from test_mcp_server.py:14-54
@pytest.fixture
def temp_repo(self, tmp_path):
    """Create a temporary repository for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()

    # Create Python test files
    py_file = tmp_path / "src" / "main.py"
    py_file.write_text('''"""Main module."""

def process_data(data):
    """Process data."""
    return data.upper()

class DataProcessor:
    """Process data in a class."""

    def transform(self, value):
        """Transform a value."""
        return value * 2
''')

    other_file = tmp_path / "src" / "utils.py"
    other_file.write_text('''"""Utilities."""

def helper_function():
    """A helper function."""
    return "helper"
''')

    return tmp_path
```

**Location:**
- Fixtures defined in test class methods using `@pytest.fixture` decorator
- `tmp_path` is pytest built-in fixture (no custom implementation needed)
- Fixture parameters appear in test method signatures: `def test_foo(self, temp_repo):`

**Sharing Fixtures:**
- Currently all fixtures defined per test class
- If shared across files, move to `tests/conftest.py` (not currently used)

## Coverage

**Requirements:**
- Enabled by default in pytest config
- No minimum enforced, but coverage enabled for visibility
- Target (implicit): Aim for coverage of main functionality

**View Coverage:**
```bash
uv run pytest tests/                           # Shows terminal report
uv run pytest tests/ --cov-report=html        # Generate HTML report (htmlcov/index.html)
uv run pytest tests/ --cov-report=xml         # Generate XML for CI (coverage.xml)
```

**Coverage Options:**
- `--cov=xray` - covers only xray package
- `--cov-report=term` - terminal output
- `--cov-report=xml` - XML format for CI tools
- `--cov-report=html` - HTML interactive report

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Test with real temporary data (no mocks)
- Examples:
  - `test_language_map()` - verifies LANGUAGE_MAP constant (test_indexer.py:106-115)
  - `test_default_exclusions()` - verifies DEFAULT_EXCLUSIONS constant (test_indexer.py:117-123)
  - `test_get_cache_key()` - tests cache key generation (test_indexer.py:125-133)

**Integration Tests:**
- Scope: Multiple components working together with file system
- Approach: Create temporary repository with realistic structure
- Examples:
  - `test_explore_repo_basic()` - explores directory structure (test_indexer.py:64-71)
  - `test_explore_repo_with_symbols()` - explores with symbol extraction (test_indexer.py:73-79)
  - `test_should_exclude()` - path exclusion with gitignore patterns (test_indexer.py:81-96)
  - `test_find_symbol_basic()` - symbol finding with real files (test_indexer.py:135-145)
  - `test_get_indexer_caches()` - indexer caching across calls (test_mcp_server.py:82-90)

**E2E Tests:**
- Not used - testing at integration level sufficient for MCP server
- Could be added via MCP Inspector tool if needed

## Common Patterns

**Async Testing:**
- Not used - codebase is synchronous, no async functions

**Error Testing:**
```python
# Testing exceptions - from test_mcp_server.py:69-80
def test_normalize_path_invalid(self):
    """Test that normalize_path raises error for invalid paths."""
    with pytest.raises(ValueError, match="does not exist"):
        normalize_path("/nonexistent/path/to/nowhere")

def test_normalize_path_not_directory(self, tmp_path):
    """Test that normalize_path raises error for non-directories."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    with pytest.raises(ValueError, match="is not a directory"):
        normalize_path(str(test_file))
```

**Dependency Handling - skip tests if external tool unavailable:**
```python
# from test_indexer.py:135-145
def test_find_symbol_basic(self, temp_repo):
    """Test basic symbol finding."""
    indexer = XRayIndexer(str(temp_repo))

    try:
        symbols = indexer.find_symbol("hello")
        assert isinstance(symbols, list)
    except FileNotFoundError:
        # ast-grep not installed, skip this test
        pytest.skip("ast-grep not installed")
```

**Type Checking in Tests:**
```python
# from test_indexer.py:64-71
def test_explore_repo_basic(self, temp_repo):
    """Test basic explore_repo functionality."""
    indexer = XRayIndexer(str(temp_repo))
    tree = indexer.explore_repo()

    # Check that the tree contains directory and file information
    assert "src" in tree
    assert "tests" in tree
```

**Cache Testing:**
```python
# from test_mcp_server.py:82-90
def test_get_indexer_caches(self, temp_repo):
    """Test that get_indexer caches indexer instances."""
    path = str(temp_repo)

    indexer1 = get_indexer(path)
    indexer2 = get_indexer(path)

    # Should return the same instance
    assert indexer1 is indexer2
```

**State Testing:**
```python
# from test_mcp_server.py:92-101
def test_get_indexer_creates_instance(self, temp_repo):
    """Test that get_indexer creates indexer instances."""
    # Clear cache
    _indexer_cache.clear()

    path = str(temp_repo)
    indexer = get_indexer(path)

    assert indexer is not None
    assert path in _indexer_cache
```

**Inspecting Internal State:**
```python
# from test_indexer.py:58-62
def test_indexer_initialization(self, temp_repo):
    """Test that indexer initializes correctly."""
    indexer = XRayIndexer(str(temp_repo))
    assert indexer.root_path == temp_repo
    assert isinstance(indexer._cache, dict)
```

---

*Testing analysis: 2026-02-07*
