"""Tests for the MCP server functionality."""

from pathlib import Path

import pytest

from xray.mcp_server import _indexer_cache, get_indexer, mcp, normalize_path


class TestMCPServer:
    """Tests for MCP server functions."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary repository for testing."""
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
        # Check that _tool_manager has tools registered
        assert hasattr(mcp, "_tool_manager")
        assert len(mcp._tool_manager._tools) > 0

        # Get tool names
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "explore_repo" in tool_names
        assert "find_symbol" in tool_names
        assert "what_breaks" in tool_names
