# XRAY MCP - Progressive Code Intelligence for AI Assistants

[![Python](https://img.shields.io/badge/Python-3.10+-green)](https://python.org) [![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io) [![ast-grep](https://img.shields.io/badge/Powered_by-ast--grep-orange)](https://ast-grep.github.io)

## ❌ Without XRAY

AI assistants struggle with codebase understanding. You get:

- ❌ "I can't see your code structure"
- ❌ "I don't know what depends on this function"
- ❌ Generic refactoring advice without impact analysis
- ❌ No understanding of symbol relationships

## ✅ With XRAY

XRAY gives AI assistants code navigation capabilities. Add `use XRAY tools` to your prompt:

```txt
Analyze the UserService class and show me what would break if I change the authenticate method. use XRAY tools
```

```txt
Find all functions that call validate_user and show their dependencies. use XRAY tools
```

XRAY provides three focused tools:

- 🗺️ **Map** (`explore_repo`) - See project structure with symbol skeletons
- 🔍 **Find** (`find_symbol`) - Locate functions and classes with fuzzy search
- 💥 **Impact** (`what_breaks`) - Find where a symbol is referenced

## 🚀 Quick Install (30 seconds)

See [`getting_started.md`](getting_started.md) for detailed installation instructions.

### Modern Install with uv (Recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install XRAY
git clone https://github.com/srijanshukla18/xray.git
cd xray
uv tool install .
```

### Traditional One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/srijanshukla18/xray/main/install.sh | bash
```

### Generate Config

```bash
# Get config for your tool
python mcp-config-generator.py cursor local_python
python mcp-config-generator.py claude docker  
python mcp-config-generator.py vscode source
```

## Language Support

XRAY uses [ast-grep](https://ast-grep.github.io), a tree-sitter powered structural search tool, providing accurate parsing for:
- **Python** - Functions, classes, methods, async functions
- **JavaScript** - Functions, classes, arrow functions, imports
- **TypeScript** - All JavaScript features plus interfaces, type aliases
- **Go** - Functions, structs, interfaces, methods

ast-grep ensures structural accuracy - it understands code syntax, not just text patterns.

## The XRAY Workflow - Progressive Discovery

### 1. Map - Start Simple, Then Zoom In
```python
# First: Get the big picture (directories only)
tree = explore_repo("/path/to/project")
# Returns:
# /path/to/project/
# ├── src/
# ├── tests/
# ├── docs/
# └── config/

# Then: Zoom into areas of interest with full details
tree = explore_repo("/path/to/project", focus_dirs=["src"], include_symbols=True)
# Returns:
# /path/to/project/
# └── src/
#     ├── auth.py
#     │   ├── class AuthService: # Handles user authentication
#     │   ├── def authenticate(username, password): # Validates user credentials
#     │   └── def logout(session_id): # Ends user session
#     └── models.py
#         ├── class User(BaseModel): # User account model
#         └── ... and 3 more

# Or: Limit depth for large codebases
tree = explore_repo("/path/to/project", max_depth=2, include_symbols=True)
```

### 2. Find - Locate Specific Symbols
```python
# Find symbols matching "authenticate" (fuzzy search)
symbols = find_symbol("/path/to/project", "authenticate")
# Returns list of exact symbol objects with name, type, path, line numbers
```

### 3. Impact - See What Would Break
```python
# Find where authenticate_user is used
symbol = symbols[0]  # From find_symbol
result = what_breaks(symbol)
# Returns: {"references": [...], "total_count": 12, 
#          "note": "Found 12 potential references based on text search..."}
```


## Architecture

```
FastMCP Server (mcp_server.py)
    ↓
Core Engine (src/xray/core/)
    └── indexer.py      # Orchestrates ast-grep for structural analysis
    ↓
ast-grep (external binary)
    └── Tree-sitter powered structural search
```

**Stateless design** - No database, no persistent index. Each operation runs fresh ast-grep queries for real-time accuracy.

## Why ast-grep?

Traditional grep searches text. ast-grep searches code structure:

- **grep**: Finds "authenticate" in function names, variables, comments, strings
- **ast-grep**: Finds only `def authenticate()` or `function authenticate()` definitions

This structural approach provides clean, accurate results essential for reliable code intelligence.

## Performance Characteristics

- **Startup**: Fast - launches ast-grep subprocess
- **File tree**: Python directory traversal
- **Symbol search**: Runs multiple ast-grep patterns, speed depends on codebase size
- **Impact analysis**: Name-based search across all files
- **Memory**: Minimal - no persistent state

## What Makes This Practical

1. **Progressive Discovery** - Start with directories, add symbols only where needed
2. **Smart Caching** - Symbol extraction cached per git commit for instant re-runs
3. **Flexible Focus** - Use `focus_dirs` to zoom into specific parts of large codebases
4. **Enhanced Symbols** - See function signatures and docstrings, not just names
5. **Based on tree-sitter** - ast-grep provides accurate structural analysis

XRAY helps AI assistants avoid information overload while providing deep code intelligence where needed.

## Stateless Design

XRAY performs on-demand structural analysis using ast-grep. There's no database to manage, no index to build, and no state to maintain. Each query runs fresh against your current code.

## Getting Started

1. **Install**: See [`getting_started.md`](getting_started.md) or [`GETTING_STARTED_UV.md`](GETTING_STARTED_UV.md) for modern installation
2. **Map the terrain**: `explore_repo("/path/to/project")`
3. **Find your target**: `find_symbol("/path/to/project", "UserService")`
4. **Assess impact**: `what_breaks(symbol)`

## The XRAY Philosophy

XRAY bridges the gap between simple text search and complex LSP servers:

- **More than grep** - Matches code syntax patterns, not just text
- **Less than LSP** - No language servers or complex setup
- **Practical for AI** - Provides structured data about code relationships

A simple tool that helps AI assistants navigate codebases more effectively than text search alone.
