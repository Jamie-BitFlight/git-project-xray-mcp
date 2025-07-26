# XRAY MCP - Fast Code Intelligence for AI Assistants

[![Docker](https://img.shields.io/badge/Docker-Available-blue)](https://hub.docker.com) [![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org) [![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io)

## ❌ Without XRAY

AI assistants struggle with codebase understanding. You get:

- ❌ "I can't see your code structure"
- ❌ "I don't know what depends on this function"
- ❌ Generic refactoring advice without impact analysis
- ❌ No understanding of symbol relationships

## ✅ With XRAY

XRAY gives AI assistants **actual code intelligence**. Add `use XRAY tools` to your prompt:

```txt
Analyze the UserService class and show me what would break if I change the authenticate method. use XRAY tools
```

```txt
Find all functions that call validate_user and show their dependencies. use XRAY tools
```

XRAY provides:

- 🔍 **Fast Symbol Search** - Find functions, classes instantly  
- 💥 **Impact Analysis** - "What breaks if I change this?" (THE KILLER FEATURE)
- 🔗 **Dependency Tracking** - What does this symbol depend on?
- 📍 **Location Queries** - What symbol is at file:line?

## 🚀 Quick Install (30 seconds)

See [`getting_started.md`](getting_started.md) for detailed installation instructions.

### One-Line Install

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

Currently supported:
- **Python** - Functions, classes, methods, imports, function calls

Planned:
- **JavaScript/TypeScript** - Functions, classes, methods, imports, calls  
- **Go** - Functions, structs, methods, imports, calls

## Usage Examples

### Building the Index
```python
# Index current directory
result = build_index(".")
# Returns: {"success": true, "files_indexed": 42, "symbols_found": 256, ...}
```

### Symbol Search
```python
# Find symbols matching "user"
result = find_symbol("user", limit=10)
# Returns: {"total_matches": 5, "symbols": [...]}
```

### Impact Analysis (THE KILLER FEATURE)
```python
# What breaks if I change authenticate_user?
result = what_breaks("authenticate_user")
# Returns: {"total_impacts": 12, "impacts_by_file": {...}, "reasoning": [...]}
```

### Dependency Analysis
```python
# What does UserService depend on?
result = what_depends("UserService")  
# Returns: {"total_dependencies": 3, "dependencies": [...]}
```

### Location Queries
```python
# What symbol is at main.py:25?
result = get_info("main.py", 25)
# Returns: {"symbol": {"name": "process_request", "kind": "function", ...}}
```

## Architecture

```
FastMCP Server (mcp_server.py)
    ↓
Core Engine (src/xray/core/)
    ├── indexer.py      # Build symbol database
    ├── query.py        # Search symbols  
    ├── impact.py       # Impact analysis (BFS graph traversal)
    └── schema.py       # SQLite database management
    ↓
Symbol Extraction (src/xray/parsers/)
    ├── base.py         # Parser interface & language detection
    └── python.py       # Tree-sitter Python parser
    ↓
SQLite Database (.xray/xray.db)
    ├── symbols         # Functions, classes, methods
    └── edges           # Call graph, imports, dependencies
```

## Performance Characteristics

- **Indexing**: ~1000 files/second on modern hardware
- **Symbol search**: <5ms for substring matching  
- **Impact analysis**: <50ms for depth 5
- **Memory usage**: ~100MB for 100k symbols
- **Database size**: ~10MB for 100k symbols

## What Makes This Practical

1. **No external dependencies** - Just Python + Tree-sitter
2. **No configuration required** - Works out of the box
3. **Fast enough** - Sub-second indexing for most repos
4. **Simple codebase** - ~1000 lines of focused code
5. **Actually useful** - Answers the questions that matter

The **impact analysis** tool alone makes this invaluable for understanding code changes. Combined with fast symbol search and dependency tracking, XRAY provides exactly what AI assistants need to navigate and understand codebases effectively.

## Database Storage

The code intelligence database is stored in `.xray/xray.db` in your repository root. This directory is automatically added to `.gitignore` to avoid committing the database.

## Getting Started

1. **Install**: See [`getting_started.md`](getting_started.md)
2. **Index a repo**: Call the `build_index(".")` MCP tool
3. **Search symbols**: `find_symbol("UserService")`
4. **Impact analysis**: `what_breaks("authenticate_user")`
5. **Explore dependencies**: `what_depends("UserModel")`

This creates a powerful, practical code intelligence system that transforms how AI assistants understand and navigate codebases.
