# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XRAY is an MCP (Model Context Protocol) server that provides progressive code intelligence for AI assistants. It uses ast-grep for structural code analysis, offering three core capabilities:

1. **Map** (`explore_repo`) - Progressive codebase exploration (directories → symbols)
2. **Find** (`find_symbol`) - Fuzzy symbol search for functions, classes, methods
3. **Impact** (`what_breaks`) - Reverse dependency analysis

**Key Philosophy**: Stateless design with smart caching per git commit. No database, no persistent index - all analysis runs fresh via ast-grep.

## Development Commands

### Installation and Setup

```bash
# Install from PyPI (recommended for users)
pip install git-project-xray-mcp

# Or with uv (faster)
uv pip install git-project-xray-mcp

# Install as uv tool from source (recommended for development)
uv tool install .

# Development installation (editable)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Quick test run without installation
uvx --from . git-project-xray-mcp
```

**Note**: The package is published to PyPI and available for direct installation. For development, clone the repository and use `uv tool install .` from the project directory.

### Testing the MCP Server

MCP servers are invoked by MCP clients (AI assistants), not run directly. For testing:

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector --cli uvx --from . git-project-xray-mcp

# Or configure in your AI assistant's MCP settings to use:
# - If installed as tool: git-project-xray-mcp
# - If local development from repo root: uvx --from . git-project-xray-mcp
```

### Testing

Currently no test suite. When tests are added, use:

```bash
# Run specific test file
uv run pytest tests/test_file.py -xvs --no-cov

# Run single test
uv run pytest tests/test_file.py::TestClass::test_method -xvs --no-cov
```

### Configuration Generation

Generate MCP configuration for different AI assistants:

```bash
# For Claude Desktop
uv run mcp-config-generator.py claude docker

# For Cursor
uv run mcp-config-generator.py cursor local_python

# For VS Code
uv run mcp-config-generator.py vscode source
```

### Building and Distribution

```bash
# Build package
uv build

# Install locally from source
uv tool install .

# Update after changes
uv tool install --force .
```

**Publishing to PyPI**:

The package is automatically published to PyPI on every push to main via GitHub Actions. The consolidated workflow:

1. Push a commit to main
2. GitHub Actions automatically creates an annotated git tag (e.g., v0.2.4)
3. Critical step: Fetches tags and checks out the new tag (enables hatch-vcs to read version)
4. Builds the package with `uv build` (hatch-vcs automatically detects version from git tag)
5. Publishes to PyPI using Trusted Publishing (id-token:write)
6. Creates a GitHub Release with artifacts and changelog

**Version Management**:

Version is managed automatically via `hatch-vcs` from git tags - no manual version updates needed in pyproject.toml. The build system extracts the version from the git tag when the tag is checked out.

**Key Implementation Detail**:

The `git fetch --tags` and `git checkout ${{ steps.tag_version.outputs.new_tag }}` steps are critical. They ensure hatch-vcs can read the git tag and compute the correct version during the build. Without these steps, the build would fail.

See `.github/workflows/auto-publish.yml` for the automated publishing workflow.

## Architecture

### Project Structure

```
xray/
├── src/xray/
│   ├── mcp_server.py       # FastMCP server, tool definitions, entry point
│   ├── core/
│   │   └── indexer.py      # Core XRayIndexer class, ast-grep orchestration
│   └── lsp_config.json     # Language server configuration
├── tests/                   # Test suite (minimal currently)
├── install.sh              # Automated installation script
├── mcp-config-generator.py # Generate MCP configs for various tools
└── pyproject.toml          # Project metadata, dependencies, entry points
```

### Key Components

**mcp_server.py** (src/xray/mcp_server.py):
- FastMCP server initialization
- Three main tools: `explore_repo`, `find_symbol`, `what_breaks`
- Indexer caching per repository path
- Path normalization and validation
- Entry point: `main()` function

**indexer.py** (src/xray/core/indexer.py):
- `XRayIndexer` class: Core engine for all code analysis
- Git-based caching: Uses commit SHA to cache symbol extraction
- File tree generation with progressive symbol inclusion
- ast-grep subprocess management for structural search
- Fuzzy symbol matching via thefuzz library
- Ripgrep integration for fast text search (with Python fallback)

### Data Flow

```
AI Assistant Request
    ↓
FastMCP Server (mcp_server.py)
    ↓
XRayIndexer (indexer.py)
    ↓
ast-grep subprocess (structural analysis)
    OR
ripgrep subprocess (reference search)
    ↓
Results formatted and returned
```

### Caching Strategy

- **Cache key**: Git commit SHA + file mtime + file size
- **Cache location**: `/tmp/.xray_cache/{commit_sha}/symbols.pkl`
- **Cache content**: Extracted symbol info (signatures, docstrings)
- **Invalidation**: Automatic per git commit change
- **Benefit**: Instant re-runs for same commit, no database maintenance

## Language Support

Via ast-grep (tree-sitter based):
- **Python** (.py): Functions, classes, methods, async functions
- **JavaScript** (.js, .jsx, .mjs): Functions, classes, arrow functions
- **TypeScript** (.ts, .tsx): All JS features + interfaces, type aliases
- **Go** (.go): Functions, structs, interfaces, methods

See `LANGUAGE_MAP` in indexer.py:28-36.

## Development Patterns

### Tool Parameter Handling

LLMs may pass strings for all parameters. The codebase defensively converts:
```python
# In explore_repo (mcp_server.py:137-143)
if max_depth is not None and isinstance(max_depth, str):
    max_depth = int(max_depth)
if isinstance(include_symbols, str):
    include_symbols = include_symbols.lower() in ('true', '1', 'yes')
```

Apply this pattern when adding new tool parameters.

### Path Normalization

Always use absolute paths internally (mcp_server.py:57-66):
```python
path = os.path.expanduser(path)  # Expand ~
path = os.path.abspath(path)     # Make absolute
path = str(Path(path).resolve()) # Resolve symlinks
```

### Progressive Discovery Pattern

The core workflow encourages starting simple, then zooming in:
1. First call: Directories only (`include_symbols=False`)
2. Zoom in: Focus on specific dirs with symbols (`focus_dirs=["src"]`, `include_symbols=True`)
3. Find targets: Use `find_symbol()` for specific functions/classes
4. Analyze impact: Use `what_breaks()` to see usage

This prevents information overload for AI assistants working with large codebases.

### Symbol Extraction

- Python: Uses `ast` module for accurate parsing (indexer.py:331-376)
- JS/TS/Go: Regex-based with comment extraction (indexer.py:378-421)
- Enhanced info: Includes function signatures and first line of docstring/comment

### Error Handling

Functions return user-friendly error messages rather than raising exceptions:
```python
try:
    # ... operation ...
except Exception as e:
    return f"Error exploring repository: {str(e)}"
```

This ensures MCP tools always return useful information to AI assistants.

## Important Patterns

### Exclusions

Default exclusions defined in `DEFAULT_EXCLUSIONS` (indexer.py:16-25):
- Standard directories: node_modules, venv, __pycache__, .git, etc.
- Build artifacts: build, dist, target
- IDE files: .idea, .vscode
- Compiled files: *.pyc, *.so, *.dll

Gitignore patterns also respected via `_parse_gitignore()`.

### Symbol Deduplication

`find_symbol()` deduplicates by (name, path, start_line) to avoid showing same symbol multiple times from different ast-grep patterns.

### Fuzzy Matching

Uses `thefuzz.fuzz.partial_ratio()` for fuzzy symbol search. Boosts score to 80 for exact substring matches (indexer.py:509-522).

### Reference Search Strategy

`what_breaks()` prioritizes ripgrep if available, falls back to Python text search:
1. Try ripgrep with `--json` output for speed
2. On failure/not found, use Python's `rglob` + regex
3. Always uses word boundary matching (`\b` in regex, `-w` in rg)

## Dependencies

Minimal by design:
- **fastmcp** (>=0.1.0): FastMCP framework for building MCP servers
- **ast-grep-cli** (>=0.39.0): Tree-sitter powered structural search
- **thefuzz** (>=0.20.0): Fuzzy string matching for symbol search

Python requirement: >=3.10

## Entry Points

Defined in pyproject.toml:
```toml
[project.scripts]
git-project-xray-mcp = "xray.mcp_server:main"
```

The `git-project-xray-mcp` command calls `main()` in mcp_server.py, which starts the FastMCP server.

## Configuration Management

The `mcp-config-generator.py` script generates correct JSON configuration for:
- Claude Desktop (local_python, docker, installed_script)
- Cursor (local_python)
- VS Code (source)

Run with: `uv run mcp-config-generator.py <tool> <method>`

## Claude Code Sessions Integration

This repository uses the cc-sessions framework. See `sessions/CLAUDE.sessions.md` for collaboration workflows and DAIC mode protocols.

## Future Development Notes

When adding features:
1. Maintain stateless design - no persistent state beyond git commit caching
2. Follow progressive discovery pattern - start simple, add detail on demand
3. Use ast-grep for structural analysis, not regex
4. Provide user-friendly error messages from all tools
5. Test with multiple languages from LANGUAGE_MAP
6. Consider adding formal test suite using pytest
7. Document all tool parameters with examples in docstrings
