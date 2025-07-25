# XRAY-Lite: Complete Specification & Implementation Guide

## The Original Problem

RepoAtlas was created to help AI assistants navigate codebases efficiently. However, it has fundamental limitations:

1. **Token Bloat**: RepoAtlas.json format with special characters wastes tokens (500k+ tokens for large repos)
2. **Shallow Analysis**: Regex-based parsing misses semantic relationships
3. **No Impact Analysis**: Can't answer "what breaks if I change this function?"
4. **Limited Query Capabilities**: Only basic substring matching
5. **JSON Storage Limitations**: Poor performance at scale, no real relationships

The core insight: **AI assistants need to understand code relationships and impact, not just find symbol names.**

## The XRAY Vision

XRAY was conceived as a complete code intelligence system with:
- **Semantic Analysis**: Real AST-based parsing vs regex
- **Dependency Graphs**: Who calls what, who imports what
- **Impact Analysis**: Static change-impact analysis via graph traversal  
- **Fast Queries**: SQLite-based storage with proper indexing
- **Multiple Languages**: Pluggable parsers for polyglot repos

But the original XRAY design was **overengineered** with SCIP/LSIF indexers, complex edge types, gRPC/REST APIs, and distributed systems complexity.

## XRAY-Lite: The Practical Solution

XRAY-Lite strips away all overengineering and focuses on what AI assistants actually need:

### Core Capabilities
1. **Fast symbol search** - Find functions, classes, methods instantly
2. **Impact analysis** - "What breaks if I change this?" (THE KILLER FEATURE)
3. **Dependency tracking** - What does this symbol depend on?
4. **Location-based queries** - What symbol is at file:line?
5. **Rapid indexing** - Sub-second rebuilds for most repos

### Technical Approach
- **Storage**: SQLite (fast, reliable, 10MB for 100k symbols)
- **Parsing**: Tree-sitter (precise AST parsing, no regex)
- **Interface**: MCP server (5 essential tools)
- **Languages**: Python, JavaScript/TypeScript, Go, Rust
- **Performance**: <1s indexing for 5k files, <50ms queries

## Architecture Overview

```
MCP Server (xray_mcp_server.py)
    ↓
Core Engine (src/xray/core/)
    ├── indexer.py      # Build symbol database
    ├── query.py        # Search symbols  
    └── impact.py       # Impact analysis (BFS graph traversal)
    ↓
Symbol Extraction (src/xray/parsers/)
    ├── python.py       # Tree-sitter Python parser
    ├── javascript.py   # Tree-sitter JS/TS parser  
    └── go.py           # Tree-sitter Go parser
    ↓
SQLite Database (.xray/xray.db)
    ├── symbols         # Functions, classes, methods
    └── edges           # Call graph, imports, dependencies
```

## Database Schema

```sql
-- Core symbols table
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,      -- function, method, class, variable, import
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    column INTEGER DEFAULT 0,
    end_line INTEGER DEFAULT 0,
    signature TEXT,          -- Full signature for context
    parent_id INTEGER,       -- For nested symbols (methods in classes)
    FOREIGN KEY(parent_id) REFERENCES symbols(id)
);

-- Dependency graph edges
CREATE TABLE edges (
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    PRIMARY KEY (from_id, to_id),
    FOREIGN KEY(from_id) REFERENCES symbols(id) ON DELETE CASCADE,
    FOREIGN KEY(to_id) REFERENCES symbols(id) ON DELETE CASCADE
);

-- Essential indexes for performance
CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_symbols_file ON symbols(file);
CREATE INDEX idx_symbols_kind ON symbols(kind);
CREATE INDEX idx_edges_from ON edges(from_id);
CREATE INDEX idx_edges_to ON edges(to_id);
```

## The 5 Essential MCP Tools

### 1. build_index(path: str = ".") → BuildResult
**Purpose**: Rebuild the code intelligence database
- Walk directory tree (skip common ignore patterns)  
- Parse files with Tree-sitter extractors
- Extract symbols and build call graph edges
- Bulk insert into SQLite with transactions
- Return comprehensive build statistics

### 2. find_symbol(query: str, limit: int = 50) → List[Symbol]
**Purpose**: Search for symbols by name substring
- Case-insensitive substring matching
- Ranking: exact match > prefix match > substring match
- Return symbol details with file locations
- Fast queries using SQLite indexes

### 3. what_breaks(symbol_name: str, max_depth: int = 5) → ImpactAnalysis
**Purpose**: Find what depends on this symbol (THE KILLER FEATURE)
- BFS traversal over edges table to find transitive dependents
- Show impact depth and affected files
- Group results by file for readability
- Essential for understanding change impact

### 4. what_depends(symbol_name: str) → DependencyGraph  
**Purpose**: Find what this symbol depends on
- Query edges table for direct dependencies
- Show imports, function calls, type references
- Help understand symbol requirements

### 5. get_info(file: str, line: int) → Symbol
**Purpose**: Get symbol at specific file location
- Find symbol definition or reference at exact location
- Handle both definitions and usages
- Essential for "what is this?" queries

## Tree-sitter Integration

### Language Support
- **Python**: Functions, classes, methods, imports, function calls
- **JavaScript/TypeScript**: Functions, classes, methods, imports, calls  
- **Go**: Functions, structs, methods, imports, calls
- **Rust**: Functions, structs, impl blocks, imports, calls

### Symbol Extraction Process
1. Parse file with appropriate Tree-sitter grammar
2. Use Tree-sitter queries to extract symbols:
   ```python
   query = Language.get_language('python').query("""
       (function_definition name: (identifier) @func)
       (class_definition name: (identifier) @class)  
       (call expression: (identifier) @call)
   """)
   ```
3. Build symbol records with precise location info
4. Extract call graph edges by linking calls to definitions
5. Handle nested symbols (methods inside classes)

## Impact Analysis Algorithm

The core innovation of XRAY-Lite:

```python
def analyze_impact(symbol_id: int, max_depth: int = 10) -> List[Dict]:
    """Find all symbols that depend on the given symbol"""
    visited = set()
    queue = [(symbol_id, 0)]
    impacts = []
    
    while queue:
        current_id, depth = queue.pop(0)
        if current_id in visited or depth > max_depth:
            continue
            
        visited.add(current_id)
        
        # Find all symbols that use this one
        dependents = db.execute("""
            SELECT s.*, e.from_id 
            FROM edges e
            JOIN symbols s ON s.id = e.from_id
            WHERE e.to_id = ?
        """, (current_id,))
        
        for dependent in dependents:
            impacts.append({
                'name': dependent['name'],
                'file': dependent['file'], 
                'line': dependent['line'],
                'depth': depth + 1
            })
            queue.append((dependent['id'], depth + 1))
    
    return sorted(impacts, key=lambda x: (x['depth'], x['file']))
```

## Performance Characteristics

- **Indexing**: ~1000 files/second on modern hardware
- **Symbol search**: <5ms for substring matching  
- **Impact analysis**: <50ms for depth 5
- **Memory usage**: ~100MB for 100k symbols
- **Database size**: ~10MB for 100k symbols

## Complete Implementation Plan

### Phase 1: Foundation & Setup (Week 1)

#### 1.1 Project Structure Setup
- [ ] Create new repo: `xray-lite`
- [ ] Initialize Python project with `pyproject.toml`:
  ```toml
  [project]
  name = "xray-lite"
  version = "0.1.0"
  dependencies = [
      "fastmcp",
      "tree-sitter", 
      "pydantic",
      "sqlite3"
  ]
  ```
- [ ] Create directory structure:
  ```
  xray-lite/
  ├── README.md
  ├── pyproject.toml
  ├── xray_mcp_server.py      # Main MCP server entry point
  ├── src/xray/
  │   ├── __init__.py
  │   ├── core/
  │   │   ├── __init__.py
  │   │   ├── schema.py       # SQLite schema & migrations  
  │   │   ├── indexer.py      # Core indexing engine
  │   │   ├── query.py        # Query engine
  │   │   └── impact.py       # Impact analysis engine
  │   └── parsers/
  │       ├── __init__.py
  │       ├── base.py         # Base extractor interface
  │       ├── python.py       # Python Tree-sitter extractor
  │       ├── javascript.py   # JS/TS extractor  
  │       └── go.py           # Go extractor
  └── tests/
      ├── __init__.py
      ├── test_indexer.py
      ├── test_query.py
      └── test_impact.py
  ```

#### 1.2 SQLite Schema Implementation  
- [ ] Create `src/xray/core/schema.py`:
  - Implement complete schema with symbols and edges tables
  - Add all essential indexes for performance
  - Create database initialization function
  - Add schema migration support for future changes
- [ ] Implement `.xray/` directory management:
  - Auto-create `.xray/` directory (like `.git/`)
  - Handle database file creation and permissions
  - Add `.xray/` to `.gitignore` automatically

#### 1.3 Tree-sitter Language Setup
- [ ] Install Tree-sitter language grammars:
  ```bash
  mkdir vendor
  cd vendor
  git clone https://github.com/tree-sitter/tree-sitter-python
  git clone https://github.com/tree-sitter/tree-sitter-javascript  
  git clone https://github.com/tree-sitter/tree-sitter-typescript
  git clone https://github.com/tree-sitter/tree-sitter-go
  git clone https://github.com/tree-sitter/tree-sitter-rust
  ```
- [ ] Create `src/xray/parsers/base.py`:
  - Build language libraries with `Language.build_library()`
  - Initialize parsers for each language
  - Test basic Tree-sitter parsing works
- [ ] Verify Tree-sitter installation with simple test files

### Phase 2: Symbol Extraction Engine (Week 2)

#### 2.1 Core Extraction Framework
- [ ] Implement `src/xray/core/indexer.py`:
  - `SymbolExtractor` class with SQLite integration
  - File walking with ignore patterns (node_modules, .git, etc.)
  - Language detection by file extension
  - Bulk insert optimization with transactions

#### 2.2 Python Parser Implementation  
- [ ] Create `src/xray/parsers/python.py`:
  - Extract functions: `(function_definition name: (identifier) @func)`
  - Extract classes: `(class_definition name: (identifier) @class)`
  - Extract methods within classes with parent relationships
  - Extract imports: `(import_statement)`, `(import_from_statement)`
  - Extract function calls: `(call expression: (identifier) @call)`
  - Build precise location info (line, column, end_line)
  - Generate function signatures from AST

#### 2.3 JavaScript/TypeScript Parser
- [ ] Create `src/xray/parsers/javascript.py`:
  - Handle both .js and .ts files
  - Extract functions, arrow functions, methods
  - Extract classes and class methods  
  - Extract imports (ES6 imports, CommonJS requires)
  - Extract function calls and method calls
  - Handle TypeScript-specific constructs (interfaces, types)

#### 2.4 Go Parser Implementation
- [ ] Create `src/xray/parsers/go.py`:
  - Extract functions: `(function_declaration)`
  - Extract structs and struct methods
  - Extract interfaces
  - Extract imports from import blocks
  - Extract function calls and method calls
  - Handle Go-specific patterns (receivers, packages)

#### 2.5 Edge Resolution System
- [ ] Implement call graph edge building:
  - During parsing, collect raw edges (string references)
  - After symbol insertion, resolve string references to symbol IDs
  - Build edges table with proper foreign key relationships
  - Handle edge cases: undefined references, circular dependencies

### Phase 3: Core MCP Tools Implementation (Week 3)

#### 3.1 FastMCP Server Setup
- [ ] Create `xray_mcp_server.py`:
  ```python
  from fastmcp import FastMCP
  from src.xray.core.indexer import XRayIndexer
  from src.xray.core.query import XRayQuery  
  from src.xray.core.impact import XRayImpact

  mcp = FastMCP("XRAY-Lite Code Intelligence")
  
  # Initialize core components
  indexer = XRayIndexer()
  query = XRayQuery()
  impact = XRayImpact()
  ```

#### 3.2 Build Index Tool
- [ ] Implement `@mcp.tool() build_index(path: str = ".") -> dict`:
  - Clear existing database (full rebuild)
  - Walk directory tree with ignore patterns
  - Parse files with appropriate extractors
  - Insert symbols and edges in bulk transactions
  - Return comprehensive statistics:
    ```python
    return {
        "success": True,
        "files_indexed": files_count,
        "symbols_found": symbols_count, 
        "edges_created": edges_count,
        "duration_seconds": duration,
        "database_size_kb": db_size
    }
    ```

#### 3.3 Symbol Search Tool
- [ ] Implement `@mcp.tool() find_symbol(query: str, limit: int = 50) -> List[dict]`:
  - Case-insensitive substring matching
  - Smart ranking algorithm:
    ```sql
    ORDER BY 
        CASE 
            WHEN name = ? THEN 0          -- Exact match
            WHEN name LIKE ? THEN 1       -- Prefix match  
            ELSE 2                        -- Substring match
        END, name
    ```
  - Return symbol details with file locations
  - Include signature and context information

#### 3.4 Location Info Tool
- [ ] Implement `@mcp.tool() get_info(file: str, line: int) -> dict`:
  - Find symbol at specific file:line location
  - Handle both exact matches and enclosing symbols
  - Return symbol details with context
  - Essential for "what is this?" queries

#### 3.5 Dependency Analysis Tools
- [ ] Implement `@mcp.tool() what_depends(symbol_name: str) -> dict`:
  - Find direct dependencies (what this symbol uses)
  - Query edges table efficiently
  - Group results by file for readability
  
- [ ] Implement `@mcp.tool() what_breaks(symbol_name: str, max_depth: int = 5) -> dict`:
  - **THE KILLER FEATURE**: Transitive dependency analysis
  - BFS traversal over edges table
  - Track impact depth and reasoning
  - Group by file with depth information
  - Essential for understanding change impact

### Phase 4: Impact Analysis Engine (Week 4)

#### 4.1 Graph Traversal Implementation
- [ ] Create `src/xray/core/impact.py`:
  - Implement BFS algorithm for dependency traversal
  - Handle cycles gracefully with visited set
  - Configurable max depth to prevent infinite loops
  - Track path/reasoning for each impact

#### 4.2 Advanced Impact Features  
- [ ] Impact categorization:
  - Immediate vs transitive impacts
  - Impact by relationship type (calls vs imports)
  - Risk assessment based on depth and usage patterns
- [ ] Performance optimization:
  - Efficient SQL queries with proper joins
  - Batch operations for large graphs
  - Memory-efficient traversal algorithms

#### 4.3 Query Optimization
- [ ] Implement `QueryCache` class:
  - LRU cache for frequent symbol lookups
  - Cache impact analysis results
  - Configurable cache size and TTL
- [ ] Database query optimization:
  - Analyze query plans for bottlenecks
  - Add additional indexes if needed
  - Optimize join patterns for large repositories

### Phase 5: Advanced Features & Polish (Week 5)

#### 5.1 Enhanced Language Support
- [ ] Add Rust parser using Tree-sitter-rust:
  - Functions, structs, impl blocks
  - Traits and trait implementations
  - Module imports and use statements
  - Method calls and function calls

#### 5.2 Error Handling & Robustness
- [ ] Comprehensive error handling:
  - Graceful handling of parse errors
  - Recovery from corrupted database
  - Clear error messages for users
  - Logging and debugging support

#### 5.3 Performance Optimization
- [ ] Incremental indexing:
  - Track file modification times
  - Only reparse changed files
  - Efficient database updates
- [ ] Memory optimization:
  - Streaming file processing for large repos
  - Efficient data structures
  - Garbage collection optimization

#### 5.4 User Experience Improvements
- [ ] Progress indicators for large repositories
- [ ] Better error messages and suggestions
- [ ] Configuration options for ignore patterns
- [ ] Detailed logging and debug modes

### Phase 6: Testing & Documentation (Week 6)

#### 6.1 Comprehensive Testing
- [ ] Unit tests for all core components:
  - `tests/test_indexer.py`: Test symbol extraction
  - `tests/test_query.py`: Test search functionality
  - `tests/test_impact.py`: Test impact analysis
- [ ] Integration tests:
  - Test with real codebases of different sizes
  - Performance tests on large repositories
  - Edge case testing (circular deps, malformed code)
- [ ] MCP tool tests:
  - Test each MCP tool with FastMCP test framework
  - Verify response formats and error handling

#### 6.2 Documentation & Examples
- [ ] Complete README.md with:
  - Installation instructions
  - Usage examples for each MCP tool
  - Performance characteristics
  - Comparison with other tools
- [ ] Technical documentation:
  - Architecture overview
  - Database schema documentation
  - API reference for each MCP tool
  - Troubleshooting guide

#### 6.3 Performance Benchmarks
- [ ] Benchmark suite:
  - Indexing performance on repos of different sizes
  - Query performance for different patterns
  - Memory usage analysis
  - Comparison with RepoAtlas and other tools

## Key Implementation Guidelines

### 1. Start Simple, Iterate Fast
- Begin with Python-only parsing to prove the concept
- Get basic functionality working before adding complexity
- Test with real codebases throughout development

### 2. Performance First  
- SQLite with proper indexes = fast queries
- Bulk operations with transactions
- Efficient data structures and algorithms
- Memory-conscious implementation

### 3. Practical Focus
- Focus on the 5 essential MCP tools
- Skip overengineered features (SCIP/LSIF, complex config)
- Build what AI assistants actually need

### 4. Quality Implementation
- Comprehensive error handling
- Good test coverage
- Clear documentation
- Clean, maintainable code

## Success Metrics

- **Performance**: <1s indexing for 5k files, <50ms queries
- **Accuracy**: >95% symbol extraction accuracy  
- **Functionality**: All 5 MCP tools working reliably
- **Impact Analysis**: Correctly identifies transitive dependencies
- **Reliability**: Handles large repos (50k+ files) without issues
- **Usability**: Clear, helpful responses for AI assistants

## What Makes This Practical

1. **No external dependencies** - Just Python + Tree-sitter
2. **No configuration required** - Works out of the box
3. **Fast enough** - Sub-second indexing for most repos
4. **Simple codebase** - ~1000 lines of focused code
5. **Actually useful** - Answers the questions that matter

The `what_breaks` impact analysis tool alone makes this invaluable for understanding code changes. Combined with fast symbol search and dependency tracking, XRAY-Lite provides exactly what AI assistants need to navigate and understand codebases effectively.

## Getting Started

Once this specification is implemented:

1. **Installation**: `pip install -e .`
2. **Index a repo**: MCP tool call to `build_index(".")`  
3. **Search symbols**: `find_symbol("UserService")`
4. **Impact analysis**: `what_breaks("authenticate_user")`
5. **Explore dependencies**: `what_depends("UserModel")`

This creates a powerful, practical code intelligence system that transforms how AI assistants understand and navigate codebases.