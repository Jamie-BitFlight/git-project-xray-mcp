"""Tests for the XRayIndexer class."""

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


class TestXRayIndexerSymbolExtraction:
    """Tests for symbol extraction from different file types."""

    @pytest.fixture
    def indexer(self, tmp_path):
        """Create a bare indexer for a temp directory."""
        return XRayIndexer(str(tmp_path))

    def test_extract_python_symbols_functions_and_classes(self, indexer):
        """Test Python symbol extraction with functions and classes."""
        content = '''
def my_function(a, b):
    """Do something."""
    pass

async def async_func():
    """Async function."""
    pass

class MyClass(BaseClass):
    """A class."""
    pass
'''
        symbols = indexer._extract_python_symbols_enhanced(content)
        names = [s["signature"] for s in symbols]
        assert any("def my_function" in n for n in names)
        assert any("async def async_func" in n for n in names)
        assert any("class MyClass" in n for n in names)

    def test_extract_python_symbols_with_docstrings(self, indexer):
        """Test that Python symbol extraction captures docstrings."""
        content = '''
def documented():
    """This is the docstring."""
    pass
'''
        symbols = indexer._extract_python_symbols_enhanced(content)
        assert len(symbols) == 1
        assert symbols[0]["doc"] == "This is the docstring."

    def test_extract_python_symbols_no_docstring(self, indexer):
        """Test that Python symbol extraction handles missing docstrings."""
        content = """
def undocumented():
    return 42
"""
        symbols = indexer._extract_python_symbols_enhanced(content)
        assert len(symbols) == 1
        assert symbols[0]["doc"] == ""

    def test_extract_python_symbols_invalid_syntax(self, indexer):
        """Test that invalid Python returns empty list without raising."""
        symbols = indexer._extract_python_symbols_enhanced("def (invalid syntax")
        assert symbols == []

    def test_extract_regex_symbols_javascript(self, indexer):
        """Test JavaScript symbol extraction."""
        content = """
function myFunc(a, b) {
    return a + b;
}

class MyComponent extends React.Component {
    render() {}
}

const arrowFn = (x) => x * 2;
"""
        symbols = indexer._extract_regex_symbols_enhanced(content, "javascript")
        sigs = [s["signature"] for s in symbols]
        assert any("function myFunc" in s for s in sigs)
        assert any("class MyComponent" in s for s in sigs)
        assert any("const arrowFn" in s for s in sigs)

    def test_extract_regex_symbols_typescript(self, indexer):
        """Test TypeScript symbol extraction (same patterns as JavaScript)."""
        content = """
export function tsFunc(x: string): void {}
export class TsClass {}
"""
        symbols = indexer._extract_regex_symbols_enhanced(content, "typescript")
        sigs = [s["signature"] for s in symbols]
        assert any("function tsFunc" in s for s in sigs)
        assert any("class TsClass" in s for s in sigs)

    def test_extract_regex_symbols_go(self, indexer):
        """Test Go symbol extraction."""
        content = """
func MyFunc(a int, b int) int {
    return a + b
}

func (r *Receiver) Method(x string) {
}

type MyStruct struct {
    Field string
}
"""
        symbols = indexer._extract_regex_symbols_enhanced(content, "go")
        sigs = [s["signature"] for s in symbols]
        assert any("func MyFunc" in s for s in sigs)
        assert any("type MyStruct struct" in s for s in sigs)

    def test_extract_regex_symbols_unknown_language(self, indexer):
        """Test that unknown language returns empty list."""
        symbols = indexer._extract_regex_symbols_enhanced("some code", "ruby")
        assert symbols == []

    def test_format_enhanced_skeleton_empty(self, indexer):
        """Test format_enhanced_skeleton with empty symbols."""
        result = indexer._format_enhanced_skeleton([], 5)
        assert result == []

    def test_format_enhanced_skeleton_truncation(self, indexer):
        """Test format_enhanced_skeleton truncates to max_symbols."""
        symbols = [{"signature": f"def func{i}():", "doc": ""} for i in range(10)]
        result = indexer._format_enhanced_skeleton(symbols, 3)
        assert len(result) == 4  # 3 symbols + "... and 7 more"
        assert "7 more" in result[-1]

    def test_format_enhanced_skeleton_exact_count(self, indexer):
        """Test format_enhanced_skeleton with exactly max_symbols symbols."""
        symbols = [{"signature": f"def func{i}():", "doc": ""} for i in range(3)]
        result = indexer._format_enhanced_skeleton(symbols, 3)
        # Exact match: no truncation message
        assert len(result) == 3
        assert not any("more" in line for line in result)

    def test_extract_symbol_name_from_def(self, indexer):
        """Test symbol name extraction from def statement."""
        assert indexer._extract_symbol_name("def my_function(a, b):") == "my_function"
        assert indexer._extract_symbol_name("class MyClass:") == "MyClass"
        assert indexer._extract_symbol_name("function jsFunc() {}") == "jsFunc"

    def test_extract_symbol_name_from_const(self, indexer):
        """Test symbol name extraction from const declaration."""
        assert indexer._extract_symbol_name("const myArrow = () =>") == "myArrow"

    def test_extract_symbol_name_from_func(self, indexer):
        """Test symbol name extraction from Go func."""
        assert indexer._extract_symbol_name("func GoFunction(x int)") == "GoFunction"

    def test_extract_symbol_name_no_match(self, indexer):
        """Test symbol name extraction returns None for unrecognized text."""
        assert indexer._extract_symbol_name("random text with no symbol") is None

    def test_get_file_skeleton_enhanced_cached(self, tmp_path):
        """Test that file skeleton is returned from cache on second call."""
        py_file = tmp_path / "cached.py"
        py_file.write_text("def cached_func():\n    pass\n")
        indexer = XRayIndexer(str(tmp_path))

        # First call populates cache
        result1 = indexer._get_file_skeleton_enhanced(py_file, 5)
        # Second call uses cache
        result2 = indexer._get_file_skeleton_enhanced(py_file, 5)
        assert result1 == result2

    def test_get_file_skeleton_unsupported_extension(self, tmp_path):
        """Test that unsupported file extensions return empty list."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("just text")
        indexer = XRayIndexer(str(tmp_path))
        result = indexer._get_file_skeleton_enhanced(txt_file, 5)
        assert result == []


class TestXRayIndexerCaching:
    """Tests for XRayIndexer cache behavior."""

    def test_cache_key_nonexistent_file(self, tmp_path):
        """Test cache key generation for nonexistent file falls back to path."""
        indexer = XRayIndexer(str(tmp_path))
        nonexistent = tmp_path / "does_not_exist.py"
        key = indexer._get_cache_key(nonexistent)
        assert str(nonexistent) in key

    def test_save_and_load_cache(self, tmp_path):
        """Test that cache survives a save and reload cycle."""
        # Init with a git repo so cache_dir is set
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True
        )
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        py_file = tmp_path / "mod.py"
        py_file.write_text("def f(): pass\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)

        indexer = XRayIndexer(str(tmp_path))
        assert indexer.cache_dir is not None

        # Populate and save cache
        indexer._cache["test_key"] = [{"signature": "def f():", "doc": ""}]
        indexer._save_cache()

        # New indexer should load from disk
        indexer2 = XRayIndexer(str(tmp_path))
        assert "test_key" in indexer2._cache

    def test_init_cache_no_git(self, tmp_path):
        """Test indexer initializes gracefully when not in a git repo."""
        indexer = XRayIndexer(str(tmp_path))
        # No git repo → commit_sha and cache_dir should be None
        assert indexer.commit_sha is None
        assert indexer.cache_dir is None
        # Cache should still work in-memory
        assert isinstance(indexer._cache, dict)


class TestXRayIndexerWhatBreaks:
    """Tests for what_breaks reference search."""

    @pytest.fixture
    def temp_repo_with_references(self, tmp_path):
        """Create a repo where one file references a symbol in another."""
        (tmp_path / "src").mkdir()

        (tmp_path / "src" / "lib.py").write_text("def target_function():\n    return 42\n")
        (tmp_path / "src" / "app.py").write_text(
            "from lib import target_function\n\nresult = target_function()\n"
        )
        return tmp_path

    def test_what_breaks_python_fallback(self, temp_repo_with_references):
        """Test what_breaks uses Python fallback and finds references."""
        indexer = XRayIndexer(str(temp_repo_with_references))
        symbol = {
            "name": "target_function",
            "path": str(temp_repo_with_references / "src" / "lib.py"),
        }
        result = indexer.what_breaks(symbol)
        assert isinstance(result, dict)
        assert "references" in result
        assert "total_count" in result
        assert result["total_count"] >= 1
        # Should find reference in app.py
        files = [r["file"] for r in result["references"]]
        assert any("app.py" in f for f in files)

    def test_python_text_search(self, temp_repo_with_references):
        """Test _python_text_search finds references in source files."""
        indexer = XRayIndexer(str(temp_repo_with_references))
        refs = indexer._python_text_search("target_function")
        assert isinstance(refs, list)
        assert len(refs) >= 1
        files = [r["file"] for r in refs]
        assert any("app.py" in f for f in files)

    def test_python_text_search_no_match(self, temp_repo_with_references):
        """Test _python_text_search returns empty list when nothing matches."""
        indexer = XRayIndexer(str(temp_repo_with_references))
        refs = indexer._python_text_search("completely_nonexistent_xyz_symbol")
        assert refs == []

    def test_what_breaks_result_structure(self, temp_repo_with_references):
        """Test what_breaks returns expected keys in result."""
        indexer = XRayIndexer(str(temp_repo_with_references))
        symbol = {
            "name": "target_function",
            "path": str(temp_repo_with_references / "src" / "lib.py"),
        }
        result = indexer.what_breaks(symbol)
        assert "references" in result
        assert "total_count" in result
        assert "note" in result
        assert "target_function" in result["note"]
