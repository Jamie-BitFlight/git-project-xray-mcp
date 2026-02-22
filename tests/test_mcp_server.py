"""Tests for the MCP server functionality."""

import subprocess
from pathlib import Path

import pytest

from xray.mcp_server import (
    _indexer_cache,
    explore_repo,
    find_symbol,
    get_indexer,
    mcp,
    normalize_path,
    what_breaks,
)


class TestMCPServer:
    """Tests for MCP server functions."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary git repository for testing."""

        # Initialize a git repo so what_breaks can find the root
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True
        )

        # Create directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()

        # Create a Python file
        py_file = tmp_path / "src" / "main.py"
        py_file.write_text(
            '''"""Main module."""

def process_data(data):
    """Process data."""
    return data.upper()

class DataProcessor:
    """Process data in a class."""

    def transform(self, value):
        """Transform a value."""
        return value * 2
'''
        )

        # Create another Python file
        other_file = tmp_path / "src" / "utils.py"
        other_file.write_text(
            '''"""Utilities."""

def helper_function():
    """A helper function."""
    return "helper"

def use_processor():
    """Use the processor."""
    from main import process_data
    return process_data("test")
'''
        )

        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True
        )

        return tmp_path

    def test_normalize_path_expands_user(self, tmp_path):
        """Test that normalize_path expands ~ correctly."""
        # This might vary by system, but should not raise an error
        path = str(tmp_path)
        normalized = normalize_path(path)
        assert Path(normalized).exists()

    def test_normalize_path_makes_absolute(self, tmp_path):
        """Test that normalize_path makes paths absolute."""
        path = str(tmp_path)
        normalized = normalize_path(path)
        assert Path(normalized).is_absolute()

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

    def test_get_indexer_caches(self, temp_repo):
        """Test that get_indexer caches indexer instances."""
        path = str(temp_repo)

        indexer1 = get_indexer(path)
        indexer2 = get_indexer(path)

        # Should return the same instance
        assert indexer1 is indexer2

    def test_get_indexer_creates_instance(self, temp_repo):
        """Test that get_indexer creates indexer instances."""
        # Clear cache
        _indexer_cache.clear()

        path = str(temp_repo)
        indexer = get_indexer(path)

        assert indexer is not None
        assert path in _indexer_cache

    def test_mcp_server_initialization(self):
        """Test that MCP server is properly initialized."""
        # Test that the mcp instance exists
        assert mcp is not None
        assert mcp.name == "XRAY Code Intelligence"

    def test_mcp_server_has_registered_functions(self):
        """Test that functions are registered in the mcp server."""
        import asyncio

        # list_tools() is async in the current FastMCP API
        tools = asyncio.run(mcp.list_tools())
        tool_names = [t.name for t in tools]
        assert "explore_repo" in tool_names
        assert "find_symbol" in tool_names
        assert "what_breaks" in tool_names

    def test_explore_repo_tool_returns_string(self, temp_repo):
        """Test that explore_repo tool function returns a string."""
        result = explore_repo(str(temp_repo))
        assert isinstance(result, str)
        assert "src" in result

    def test_explore_repo_tool_with_symbols(self, temp_repo):
        """Test explore_repo tool with include_symbols=True."""
        result = explore_repo(str(temp_repo), include_symbols=True)
        assert isinstance(result, str)

    def test_explore_repo_tool_string_params(self, temp_repo):
        """Test explore_repo tool converts string params (LLM defense)."""
        result = explore_repo(str(temp_repo), max_depth="2", max_symbols_per_file="3")
        assert isinstance(result, str)

    def test_explore_repo_tool_string_include_symbols(self, temp_repo):
        """Test explore_repo tool handles string 'true' for include_symbols."""
        result = explore_repo(str(temp_repo), include_symbols="true")  # type: ignore[arg-type]
        assert isinstance(result, str)

    def test_explore_repo_tool_invalid_path(self):
        """Test explore_repo tool returns error string for invalid path."""
        result = explore_repo("/nonexistent/path/that/does/not/exist")
        assert isinstance(result, str)
        assert "Error" in result

    def test_find_symbol_tool_returns_list(self, temp_repo):
        """Test that find_symbol tool returns a list."""
        result = find_symbol(str(temp_repo), "process_data")
        assert isinstance(result, list)

    def test_find_symbol_tool_invalid_path(self):
        """Test find_symbol tool returns error list for invalid path."""
        result = find_symbol("/nonexistent/path/that/does/not/exist", "something")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "error" in result[0]

    def test_what_breaks_tool_returns_dict(self, temp_repo):
        """Test that what_breaks tool returns a dict."""
        symbol = {
            "name": "process_data",
            "type": "function",
            "path": str(temp_repo / "src" / "main.py"),
            "start_line": 3,
            "end_line": 5,
        }
        result = what_breaks(symbol)
        assert isinstance(result, dict)
        assert "references" in result
        assert "total_count" in result

    def test_what_breaks_tool_finds_references(self, temp_repo):
        """Test that what_breaks tool finds references to a symbol."""
        symbol = {
            "name": "process_data",
            "type": "function",
            "path": str(temp_repo / "src" / "main.py"),
            "start_line": 3,
            "end_line": 5,
        }
        result = what_breaks(symbol)
        # utils.py references process_data
        assert result["total_count"] >= 1

    def test_what_breaks_tool_error_on_missing_key(self):
        """Test that what_breaks tool returns error dict on bad input."""
        result = what_breaks({"type": "function"})  # Missing 'name' and 'path'
        assert isinstance(result, dict)
        assert "error" in result

    def test_explore_repo_tool_string_false_include_symbols(self, temp_repo):
        """Test explore_repo tool handles string 'false' for include_symbols."""
        result = explore_repo(str(temp_repo), include_symbols="false")  # type: ignore[arg-type]
        assert isinstance(result, str)
        # With include_symbols=False the output should not contain symbol lines
        assert "def " not in result
