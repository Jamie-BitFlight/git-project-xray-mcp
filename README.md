# XRAY MCP - Structural Code Intelligence for AI Assistants

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

XRAY provides:

- 🔍 **Symbol Search** - Find functions and classes with fuzzy matching
- 💥 **Impact Analysis** - Find references to a symbol by name
- 🔗 **Dependency Tracking** - Extract function calls and imports from a symbol
- 🌳 **File Tree** - Display directory structure with gitignore support
- 🚀 **Structural Search** - Uses ast-grep for syntax-aware matching

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

## Usage Examples

### Building the Index
```python
# Generate visual file tree
result = build_index("/path/to/project")
# Returns a formatted tree structure of your project
```

### Symbol Search with Fuzzy Matching
```python
# Find symbols matching "user" (fuzzy search)
result = find_symbol("/path/to/project", "user auth")
# Returns top matches for functions, classes, methods containing these terms
```

### Impact Analysis
```python
# Find references to authenticate_user
symbol = find_symbol("/path/to/project", "authenticate_user")[0]
result = what_breaks(symbol)
# Returns: {"references": [...], "total_count": 12, "note": "..."}
# Note: Matches by name, may include unrelated symbols with same name
```

### Dependency Analysis
```python
# What does UserService.authenticate depend on?
symbol = find_symbol("/path/to/project", "authenticate")[0]
result = what_depends(symbol)
# Returns: ["get_user", "verify_password", "logging", ...]
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

1. **Simple installation** - `pip install` handles dependencies
2. **No configuration** - Works with default settings
3. **Syntax-aware** - ast-grep matches code structure, not just text
4. **Stateless** - No index to maintain
5. **Based on tree-sitter** - Uses established parsing technology

XRAY provides basic code navigation tools that help AI assistants understand codebases better than plain text search.

## Stateless Design

XRAY performs on-demand structural analysis using ast-grep. There's no database to manage, no index to build, and no state to maintain. Each query runs fresh against your current code.

## Getting Started

1. **Install**: See [`getting_started.md`](getting_started.md) or [`GETTING_STARTED_UV.md`](GETTING_STARTED_UV.md) for modern installation
2. **View project structure**: `build_index("/path/to/project")`
3. **Search symbols**: `find_symbol("/path/to/project", "UserService")`
4. **Impact analysis**: Find symbol first, then `what_breaks(symbol)`
5. **Explore dependencies**: Find symbol first, then `what_depends(symbol)`

## The XRAY Philosophy

XRAY bridges the gap between simple text search and complex LSP servers:

- **More than grep** - Matches code syntax patterns, not just text
- **Less than LSP** - No language servers or complex setup
- **Practical for AI** - Provides structured data about code relationships

A simple tool that helps AI assistants navigate codebases more effectively than text search alone.
