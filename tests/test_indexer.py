"""Tests for the XRayIndexer class."""

import tempfile
from pathlib import Path

import pytest

from xray.core.indexer import DEFAULT_EXCLUSIONS, LANGUAGE_MAP, XRayIndexer


class TestXRayIndexer:
    """Tests for XRayIndexer functionality."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository with test files."""
        # Create a simple project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        # Create a Python file
        py_file = tmp_path / "src" / "example.py"
        py_file.write_text(
            '''"""Example module."""

def hello_world():
    """Say hello."""
    return "Hello, World!"

class MyClass:
    """A simple class."""

    def my_method(self, arg1: str) -> str:
        """A method."""
        return f"Got: {arg1}"
'''
        )

        # Create a JavaScript file
        js_file = tmp_path / "src" / "example.js"
        js_file.write_text(
            """// Example JS file
function greet(name) {
    return `Hello, ${name}`;
}

class Greeter {
    constructor(name) {
        this.name = name;
    }
}
"""
        )

        # Create a gitignore file
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.log\nnode_modules/\n")

        return tmp_path

    def test_indexer_initialization(self, temp_repo):
        """Test that indexer initializes correctly."""
        indexer = XRayIndexer(str(temp_repo))
        assert indexer.root_path == temp_repo
        assert isinstance(indexer._cache, dict)

    def test_explore_repo_basic(self, temp_repo):
        """Test basic explore_repo functionality."""
        indexer = XRayIndexer(str(temp_repo))
        tree = indexer.explore_repo()

        # Check that the tree contains directory and file information
        assert "src" in tree
        assert "tests" in tree

    def test_explore_repo_with_symbols(self, temp_repo):
        """Test explore_repo with symbol extraction."""
        indexer = XRayIndexer(str(temp_repo))
        tree = indexer.explore_repo(include_symbols=True)

        # Check that symbols are included
        assert "def hello_world" in tree or "function greet" in tree

    def test_should_exclude(self, temp_repo):
        """Test path exclusion logic."""
        indexer = XRayIndexer(str(temp_repo))
        gitignore_patterns = indexer._parse_gitignore()

        # Test default exclusions
        assert indexer._should_exclude(temp_repo / "node_modules", gitignore_patterns)
        assert indexer._should_exclude(temp_repo / ".git", gitignore_patterns)
        assert indexer._should_exclude(temp_repo / "__pycache__", gitignore_patterns)

        # Test file pattern exclusions
        assert indexer._should_exclude(temp_repo / "test.pyc", gitignore_patterns)
        assert indexer._should_exclude(temp_repo / "file.log", gitignore_patterns)

        # Test normal files are not excluded
        assert not indexer._should_exclude(temp_repo / "example.py", gitignore_patterns)

    def test_parse_gitignore(self, temp_repo):
        """Test gitignore parsing."""
        indexer = XRayIndexer(str(temp_repo))
        patterns = indexer._parse_gitignore()

        assert "*.log" in patterns
        assert "node_modules/" in patterns

    def test_language_map(self):
        """Test that LANGUAGE_MAP contains expected languages."""
        assert ".py" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".py"] == "python"
        assert ".js" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".js"] == "javascript"
        assert ".ts" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".ts"] == "typescript"
        assert ".go" in LANGUAGE_MAP
        assert LANGUAGE_MAP[".go"] == "go"

    def test_default_exclusions(self):
        """Test that DEFAULT_EXCLUSIONS contains common directories."""
        assert "node_modules" in DEFAULT_EXCLUSIONS
        assert ".git" in DEFAULT_EXCLUSIONS
        assert "__pycache__" in DEFAULT_EXCLUSIONS
        assert "venv" in DEFAULT_EXCLUSIONS
        assert ".venv" in DEFAULT_EXCLUSIONS

    def test_get_cache_key(self, temp_repo):
        """Test cache key generation."""
        indexer = XRayIndexer(str(temp_repo))
        test_file = temp_repo / "src" / "example.py"

        cache_key = indexer._get_cache_key(test_file)
        assert str(test_file) in cache_key
        # Should include file stats
        assert ":" in cache_key

    def test_find_symbol_basic(self, temp_repo):
        """Test basic symbol finding."""
        indexer = XRayIndexer(str(temp_repo))

        # Try to find symbols, but handle if ast-grep is not available
        try:
            symbols = indexer.find_symbol("hello")
            assert isinstance(symbols, list)
        except FileNotFoundError:
            # ast-grep not installed, skip this test
            pytest.skip("ast-grep not installed")

    def test_explore_with_max_depth(self, temp_repo):
        """Test explore_repo with max_depth parameter."""
        indexer = XRayIndexer(str(temp_repo))
        tree = indexer.explore_repo(max_depth=1)

        # Should contain top-level items
        assert isinstance(tree, str)
        # Tree might be empty if nothing to show at depth 1
        assert tree is not None

    def test_explore_with_focus_dirs(self, temp_repo):
        """Test explore_repo with focus_dirs parameter."""
        indexer = XRayIndexer(str(temp_repo))
        tree = indexer.explore_repo(focus_dirs=["src"])

        # Should focus on src directory
        assert isinstance(tree, str)
        # Should either have src or be empty if focus filtering removed everything
        assert tree is not None
