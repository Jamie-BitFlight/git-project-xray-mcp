# Architecture

**Analysis Date:** 2026-02-07

## Pattern Overview

**Overall:** Progressive discovery multi-tool MCP server with external subprocess orchestration.

XRAY uses a **three-step progressive discovery workflow** where each tool builds on previous results:
1. **explore_repo()** - Broad structural overview with optional symbol skeletons
2. **find_symbol()** - Targeted fuzzy search for specific code elements
3. **what_breaks()** - Reverse dependency analysis via text search

**Key Characteristics:**
- Stateless design - no persistent indexes, all analysis runs fresh
- External tool orchestration - delegates heavy lifting to ast-grep (structural) and ripgrep (text search)
- Git commit-based caching - caches symbol extraction per repository state
- Progressive disclosure - clients control information verbosity via parameters
- Defensive parameter handling - LLMs pass strings for all inputs, server converts types

## Layers

**Presentation Layer (FastMCP):**
- Purpose: HTTP/stdio interface for Model Context Protocol clients
- Location: `src/xray/mcp_server.py`
- Contains: Tool definitions (explore_repo, find_symbol, what_breaks), path normalization, parameter defense
- Depends on: XRayIndexer
- Used by: MCP clients (Claude, other AI assistants)
- Key functions:
  - `main()` - Entry point, starts FastMCP server
  - `normalize_path()` - Validates and normalizes file paths (expands ~, makes absolute, resolves symlinks)
  - `get_indexer()` - Retrieves cached indexer instance or creates new one
  - `explore_repo()` - Tool: maps directory structure with optional symbols
  - `find_symbol()` - Tool: finds symbols via fuzzy search
  - `what_breaks()` - Tool: finds references to a symbol

**Core Analysis Engine (XRayIndexer):**
- Purpose: Orchestrates structural and text-based code analysis
- Location: `src/xray/core/indexer.py`
- Contains: Symbol extraction, directory traversal, caching, external tool invocation
- Depends on: ast-grep (subprocess), ripgrep (subprocess), Python ast module, thefuzz library
- Used by: FastMCP layer
- Key class: `XRayIndexer`
- Key methods:
  - `explore_repo()` - Builds file tree with optional symbol skeletons
  - `find_symbol()` - Runs ast-grep patterns, fuzzy-matches results
  - `what_breaks()` - Uses ripgrep or Python fallback for text search
  - `_extract_python_symbols_enhanced()` - Uses Python ast module for accurate symbol parsing
  - `_extract_regex_symbols_enhanced()` - Regex-based extraction for JS/TS/Go
  - `_parse_gitignore()` - Respects .gitignore patterns in traversal
  - Cache management: `_init_cache()`, `_load_cache()`, `_save_cache()`

## Data Flow

**explore_repo Flow:**

1. Client calls `explore_repo(root_path, max_depth, include_symbols, focus_dirs, max_symbols_per_file)`
2. FastMCP validates path, gets/creates indexer from cache
3. XRayIndexer recursively traverses root directory:
   - Respects .gitignore and DEFAULT_EXCLUSIONS
   - Applies max_depth and focus_dirs filters
   - For each code file (if include_symbols=True):
     - Checks cache by file mtime/size
     - If cached, uses cached symbols
     - If not cached: extracts symbols via ast (Python) or regex (JS/TS/Go)
     - Formats symbols with signatures and docstrings
4. Returns formatted tree string

**find_symbol Flow:**

1. Client calls `find_symbol(root_path, query)`
2. FastMCP gets/creates indexer from cache
3. XRayIndexer runs ast-grep with language-specific patterns (12 patterns total):
   - Python: `def $NAME()`, `class $NAME()`, `async def $NAME()`
   - JS/TS: `function`, `const/let/var = =>`, `class`, `interface`, `type`
   - Go: `func`, `method`, `type struct`, `type interface`
4. Aggregates all symbols from all patterns
5. Deduplicates by (name, path, start_line)
6. Fuzzy-matches query against symbol names using thefuzz.fuzz.partial_ratio()
7. Boosts score for exact substring matches
8. Returns top 10 symbols sorted by match score

**what_breaks Flow:**

1. Client calls `what_breaks(exact_symbol)` with symbol dict from find_symbol()
2. FastMCP extracts root_path from symbol path, walks up to find .git directory
3. XRayIndexer performs text search for symbol name:
   - Tries ripgrep with `rg -w --json` (whole word) for speed
   - Falls back to Python regex if ripgrep unavailable
   - Regex pattern: `\b{symbol_name}\b` (word boundaries)
   - Skips DEFAULT_EXCLUSIONS and .gitignore patterns
   - Only searches code files (checks LANGUAGE_MAP)
4. Returns list of references with file, line number, and matched text

**State Management:**

- **Per-Repository Caching**: XRayIndexer caches symbols per git commit SHA
  - Cache location: `/tmp/.xray_cache/{commit_sha}/symbols.pkl`
  - Cache key per file: `{path}:{mtime}:{size}`
  - Cache loaded on indexer init, saved after symbol extraction
  - Automatically invalidated when git commit changes

- **Server-Level Caching**: FastMCP maintains _indexer_cache dict (path -> XRayIndexer)
  - Prevents redundant indexer creation for same repository
  - Keeps in-memory cache across multiple tool invocations

## Key Abstractions

**XRayIndexer:**
- Purpose: Central orchestrator for all code analysis operations
- Examples: Single class in `src/xray/core/indexer.py`
- Pattern: Stateless design - same indexer instance can handle multiple queries
- Parameters guide behavior: max_depth, include_symbols, focus_dirs control output granularity
- Cache is instance variable, invalidated per git commit

**Symbol Object:**
- Purpose: Standard representation of code elements returned by find_symbol()
- Structure: Dictionary with keys:
  ```python
  {
      "name": str,           # Symbol name (e.g., "authenticate_user")
      "type": str,           # Symbol type (e.g., "function", "class", "method")
      "path": str,           # Absolute file path
      "start_line": int,     # Line number where definition starts
      "end_line": int        # Line number where definition ends
  }
  ```
- Usage: Passed directly to what_breaks() to find references

**File Skeleton:**
- Purpose: Human-readable summary of code symbols with signatures and docstrings
- Format: List of strings, each showing signature + first 50 chars of docstring
- Examples:
  ```
  def authenticate(username, password):  # Validates credentials
  class AuthService:  # Handles user authentication
  ... and 2 more
  ```
- Used in: explore_repo output when include_symbols=True

**Language Support:**
- Defined in: `LANGUAGE_MAP` constant in `src/xray/core/indexer.py`
- Maps: .py→python, .js/.jsx/.mjs→javascript, .ts/.tsx→typescript, .go→go
- Extraction strategy: Python uses ast module for accuracy; JS/TS/Go use regex

**Exclusion Rules:**
- Defined in: `DEFAULT_EXCLUSIONS` set in `src/xray/core/indexer.py`
- Applied in: `_should_exclude()` method
- Scope: Directories (node_modules, .git, venv, etc.) + file patterns (*.pyc, *.log, etc.)
- Augmented by: .gitignore patterns from repository

## Entry Points

**FastMCP Server:**
- Location: `src/xray/mcp_server.py:main()`
- Triggers: `git-project-xray-mcp` CLI command (entry point defined in pyproject.toml)
- Responsibilities:
  - Initializes FastMCP server instance with name "XRAY Code Intelligence"
  - Registers three MCP tools via @mcp.tool decorator
  - Starts listening for client requests
  - Maintains _indexer_cache for performance

**Three MCP Tools:**
1. `explore_repo()` (lines 77-154)
   - Entry point for discovering codebase structure
   - Progressive: start with include_symbols=False, then add detail
   - Parameters guide discovery: max_depth, focus_dirs, max_symbols_per_file

2. `find_symbol()` (lines 157-205)
   - Entry point for locating specific code elements
   - Accepts fuzzy query, returns symbol objects
   - Results feed into what_breaks()

3. `what_breaks()` (lines 208-279)
   - Entry point for impact analysis
   - Requires symbol dict from find_symbol() as input
   - Shows every place a symbol name appears in codebase

## Error Handling

**Strategy:** Return error strings/dicts instead of raising exceptions, ensuring AI assistants always get useful feedback rather than crashes.

**Patterns:**

1. **Path Validation** (`normalize_path()`):
   - Expands ~ to home directory
   - Makes path absolute
   - Resolves symlinks
   - Validates existence and is_directory
   - Raises ValueError with descriptive message on failure
   - Caught by tool functions, returned as error string

2. **External Tool Failures** (subprocess calls):
   - ast-grep failures: Caught silently, returns empty results
   - ripgrep unavailable: Falls back to Python text search
   - FileNotFoundError: Caught, Python fallback used
   - json.JSONDecodeError: Caught per-line, continues processing

3. **File Reading Errors**:
   - Encoding errors: Caught in try/except, skips file
   - Permission errors: Caught during directory traversal, continues
   - All caught at point of use, allows partial results

4. **Caching Errors**:
   - Cache load/save failures: Caught silently, continues without cache
   - Git command failures: Falls back to no caching (commit_sha stays None)
   - Pickle errors: Handled gracefully

## Cross-Cutting Concerns

**Logging:** None - project uses no logging framework. Relies on error return values and subprocess stdout/stderr.

**Validation:**
- Type conversion from LLM strings: Explicit in explore_repo() (lines 137-143)
- Path validation: normalize_path() (lines 57-66)
- File extension validation: LANGUAGE_MAP lookup (multiple places)

**Authentication:** Not applicable - operates on local filesystem only.

**Performance Optimization:**
- Git commit-based caching of symbols (`/tmp/.xray_cache/{sha}/symbols.pkl`)
- Server-level indexer instance caching (_indexer_cache dict)
- Early termination: Respect max_depth, max_symbols_per_file limits
- External tools chosen for speed: ast-grep for structure, ripgrep for text search
- Fuzzy matching with score-based ranking avoids returning huge result sets

---

*Architecture analysis: 2026-02-07*
