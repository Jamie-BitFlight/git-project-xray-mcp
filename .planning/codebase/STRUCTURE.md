# Codebase Structure

**Analysis Date:** 2026-02-07

## Directory Layout

```
/home/user/git-project-xray-mcp/
├── src/xray/                           # Main source package
│   ├── __init__.py                     # Version definition (__version__ = "0.1.0")
│   ├── mcp_server.py                   # FastMCP server (850 lines) - PRIMARY ENTRY POINT
│   └── core/
│       ├── __init__.py                 # Package marker
│       └── indexer.py                  # XRayIndexer implementation (670 lines) - CORE ENGINE
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── test_mcp_server.py              # Tests for FastMCP layer (120 lines)
│   └── test_indexer.py                 # Tests for indexer (166 lines)
├── pyproject.toml                      # Project metadata, dependencies, build config
├── CLAUDE.md                           # Development guidance (79 lines)
├── README.md                           # User documentation (640 lines)
├── getting_started.md                  # Installation & quick start guide
├── LICENSE                             # MIT license
├── .gitignore                          # Git ignore patterns
├── .github/                            # GitHub workflows
│   └── workflows/                      # CI/CD pipelines
├── .planning/                          # GSD planning documents (auto-generated)
├── sessions/                           # CC sessions collaboration data
├── .xray/                              # Build/tool output directory
├── .python-version                     # Python version pin (3.10+)
├── mcp-config-generator.py             # Helper script for MCP client config
├── install.sh                          # Installation helper script
└── uninstall.sh                        # Uninstallation helper script
```

## Directory Purposes

**src/xray/**
- Purpose: Main package containing all source code
- Contains: FastMCP server, core analysis engine, version info
- Key files: `mcp_server.py` (server), `core/indexer.py` (engine)

**src/xray/core/**
- Purpose: Core analysis functionality separated from MCP transport
- Contains: XRayIndexer class and all symbol extraction logic
- Single file: `indexer.py` (670 lines) contains everything for code analysis

**tests/**
- Purpose: Test suite for all functionality
- Contains: Unit tests for FastMCP layer and indexer engine
- Test coverage: Path validation, indexer caching, symbol extraction, tool registration

**.github/workflows/**
- Purpose: CI/CD automation
- Contains: GitHub Actions workflows for lint, type-check, test, and auto-publish

## Key File Locations

**Entry Points:**
- `src/xray/mcp_server.py:main()` (line 282-284) - FastMCP server startup
- `pyproject.toml` [project.scripts] (line 36-37) - CLI entry point: `git-project-xray-mcp`

**Configuration:**
- `pyproject.toml` - Project metadata, dependencies, tool config
- `pyproject.toml` [tool.pytest.ini_options] - Test framework settings
- `pyproject.toml` [tool.ruff] - Linting and formatting rules
- `pyproject.toml` [tool.mypy] - Type checking settings
- `CLAUDE.md` - Development environment and workflow guidance

**Core Logic:**
- `src/xray/mcp_server.py` - FastMCP server + three MCP tool definitions
  - Lines 57-66: `normalize_path()` - Path validation
  - Lines 69-74: `get_indexer()` - Indexer caching
  - Lines 77-154: `explore_repo()` tool
  - Lines 157-205: `find_symbol()` tool
  - Lines 208-279: `what_breaks()` tool

- `src/xray/core/indexer.py` - XRayIndexer class with all analysis methods
  - Lines 14-48: `DEFAULT_EXCLUSIONS` - Files/dirs to skip
  - Lines 51-59: `LANGUAGE_MAP` - File extension to language mapping
  - Lines 62-115: `XRayIndexer.__init__()` and cache initialization
  - Lines 124-305: `explore_repo()` method and tree building
  - Lines 306-473: Symbol extraction methods (Python AST, regex for JS/TS/Go)
  - Lines 475-569: `find_symbol()` method with fuzzy matching
  - Lines 587-671: `what_breaks()` method and text search fallback

**Testing:**
- `tests/test_mcp_server.py` - FastMCP layer tests (normalizer, caching, registration)
- `tests/test_indexer.py` - XRayIndexer tests (exclusions, symbol extraction, gitignore)

## Naming Conventions

**Files:**
- Python source: `lowercase_with_underscores.py` - e.g., `mcp_server.py`, `indexer.py`
- Test files: `test_*.py` format - e.g., `test_mcp_server.py`, `test_indexer.py`
- Config: `lowercase.toml`, `.lowercase`, lowercase UPPERCASE - e.g., `pyproject.toml`, `.gitignore`, `CLAUDE.md`

**Directories:**
- Package directories: `lowercase` - e.g., `xray`, `core`, `tests`
- Hidden directories: `.lowercase` - e.g., `.github`, `.planning`, `.xray`
- Documentation: UPPERCASE - e.g., `README.md`, `LICENSE`

**Functions & Methods:**
- Public: `lowercase_with_underscores()` - e.g., `normalize_path()`, `explore_repo()`, `find_symbol()`
- Private: `_lowercase_with_underscores()` - e.g., `_init_cache()`, `_should_exclude()`, `_extract_python_symbols_enhanced()`
- Class methods: CamelCase with lowercase start in method names - e.g., `_extract_python_symbols_enhanced()`, `_build_tree_recursive_enhanced()`

**Variables & Constants:**
- Constants: `UPPERCASE_WITH_UNDERSCORES` - e.g., `DEFAULT_EXCLUSIONS`, `LANGUAGE_MAP`
- Instance variables: `_lowercase_with_underscores` (private) - e.g., `self._cache`, `self._indexer_cache`
- Type hints: Used throughout - e.g., `dict[str, XRayIndexer]`, `list[str] | None`

**Types:**
- Type hints in function signatures: PEP 604 union syntax (Python 3.10+) - e.g., `int | str | None`
- Dict/list type hints: `dict[str, type]`, `list[type]`

## Where to Add New Code

**New Tool/Feature:**
- Add tool function in `src/xray/mcp_server.py` after line 279
- Decorate with `@mcp.tool`
- Include detailed docstring with examples
- Add path normalization and error handling wrapping
- Add corresponding tests in `tests/test_mcp_server.py`

**New Symbol Extraction Method:**
- Add method to XRayIndexer class in `src/xray/core/indexer.py`
- Follow pattern of `_extract_python_symbols_enhanced()` (lines 357-402)
- Use LANGUAGE_MAP to determine when to call method
- Implement caching with `_get_cache_key()` and `self._cache`
- Return list of dicts with `{"signature": str, "doc": str}` format
- Add tests in `tests/test_indexer.py`

**New Language Support:**
1. Add file extension mapping to LANGUAGE_MAP in `src/xray/core/indexer.py` (lines 51-59)
2. Add extraction method: `_extract_{language}_symbols_enhanced()` following existing patterns
3. Add ast-grep patterns to find_symbol() in indexer.py (lines 485-503)
4. Update symbol extraction dispatcher in `_get_file_skeleton_enhanced()` (lines 322-325)
5. Add tests in `tests/test_indexer.py`

**Shared Utilities:**
- File/path utilities: `src/xray/mcp_server.py` normalize_path() can be extended
- Symbol utilities: Add methods to XRayIndexer class
- No separate utilities module yet - keep small functions inline or in appropriate class

**Configuration Changes:**
- Tool settings: `pyproject.toml` [tool.section]
- Linting/formatting: `pyproject.toml` [tool.ruff.lint]
- Type checking: `pyproject.toml` [tool.mypy]
- Testing: `pyproject.toml` [tool.pytest.ini_options]

## Special Directories

**.planning/codebase/**
- Purpose: Generated codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by /gsd:map-codebase command)
- Committed: Yes - documents tracked in git

**.xray/**
- Purpose: Build artifacts and tool outputs
- Generated: Yes
- Committed: No (not in gitignore but typically ignored)

**.github/workflows/**
- Purpose: GitHub Actions CI/CD pipelines
- Workflow names: lint.yml, type-check.yml, test.yml, auto-publish.yml
- Committed: Yes - workflows are source of truth

**sessions/**
- Purpose: CC (Claude Code) session collaboration data
- Structure: Includes tasks, protocols, transcripts, hooks, API definitions
- Generated: Yes (by CC during collaborative sessions)
- Committed: Yes - collaboration history preserved

## File Organization Principles

1. **Separation of Concerns:**
   - MCP server logic isolated in mcp_server.py (transport layer)
   - Core analysis logic isolated in indexer.py (business logic)
   - Clean interface: mcp_server.py imports and uses XRayIndexer

2. **Single Responsibility:**
   - XRayIndexer: All code analysis (no UI, no HTTP)
   - FastMCP tools: Parameter validation and error wrapping only
   - Each method does one thing: explore, find, or analyze impact

3. **No Database/Persistent Index:**
   - All analysis runs fresh per invocation
   - Only git-commit-keyed symbol cache in /tmp
   - Stateless design means same indexer can handle any query

4. **Error Handling at Boundaries:**
   - mcp_server.py tools return error strings/dicts
   - indexer.py methods raise exceptions or return empty/None
   - No exception propagation to client - all caught at tool level

## Code Dependencies

**Internal:**
- `mcp_server.py` → `core/indexer.py` (XRayIndexer class)
- Tests import from both modules

**External (from pyproject.toml):**
- `fastmcp>=0.1.0` - MCP server framework
- `ast-grep-cli>=0.39.0` - Structural code search via subprocess
- `thefuzz>=0.20.0` - Fuzzy string matching for find_symbol()

**Standard Library:**
- `subprocess` - Running ast-grep and ripgrep
- `pathlib.Path` - File path handling throughout
- `ast` - Python symbol extraction via AST module
- `json` - Parsing ast-grep/ripgrep JSON output
- `pickle` - Caching extracted symbols
- `re` - Regex-based extraction for JS/TS/Go
- `fnmatch` - .gitignore pattern matching

---

*Structure analysis: 2026-02-07*
