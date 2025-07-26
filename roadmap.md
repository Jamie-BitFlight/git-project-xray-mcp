# XRAY Roadmap

This document outlines the future vision and implementation plan for XRAY, focusing on enhancing its capabilities as an LLM-optimized dependency tracking system.

## Vision: Complete Code Intelligence for LLM Software Engineers

LLMs need 100% accurate dependency tracking to safely modify code. Current issues stem from a fundamental symbol identity mismatch that causes missing dependencies.

## Core Architectural Changes

### 1. Unified Symbol Identity System

- **Canonical Symbol IDs**: Replace simple name storage with canonical IDs (e.g., `file:Class.method`).
  - Examples:
    - `src/xray/core/indexer.py:XRayIndexer.__init__`
    - `src/xray/parsers/python.py:PythonParser`
    - `src/xray/mcp_server.py:build_index`

### 2. Multi-Alias Resolution System

Store multiple aliases per symbol:

- **Canonical**: `src/xray/core/indexer.py:XRayIndexer.__init__`
- **Qualified**: `XRayIndexer.__init__`
- **Simple**: `__init__`
- **Import**: Track how a symbol appears in each file that imports it.

### 3. Enhanced Edge Creation

- Create edges using canonical IDs.
- Resolve dependencies through ALL aliases.
- Track edge provenance (why this dependency exists).

### 4. LLM-Optimized Query Interface

- `what_breaks('build_index')` → Complete impact tree with file locations.
- `find_symbol('Python')` → All matches: classes, imports, usages.
- `analyze_dependencies('User')` → Full import chain + usage patterns.

## Implementation Plan

### Phase 1: Schema Redesign

- Add `canonical_id` field to `symbols` table.
- Add `aliases` table for multi-name resolution.
- Add `edge_provenance` for dependency reasoning.

### Phase 2: Symbol Resolution Engine

- Implement canonical ID generation.
- Build alias mapping system.
- Create smart symbol lookup that searches all aliases.

### Phase 3: Accurate Edge Detection

- Fix `self.method()` call tracking.
- Implement proper import-to-usage edge creation.
- Add cross-file class instantiation tracking.

### Phase 4: LLM Query Optimization

- Return complete dependency trees (not just direct dependencies).
- Include full context in all responses.
- Add batch query capabilities for multi-symbol analysis.

### Phase 5: Advanced Features & Polish

#### 5.1 Enhanced Language Support

- Add Rust parser using Tree-sitter-rust:
  - Functions, structs, impl blocks
  - Traits and trait implementations
  - Module imports and use statements
  - Method calls and function calls

#### 5.2 Error Handling & Robustness

- Comprehensive error handling:
  - Graceful handling of parse errors.
  - Recovery from corrupted database.
  - Clear error messages for users.
  - Logging and debugging support.

#### 5.3 Performance Optimization

- Incremental indexing:
  - Track file modification times.
  - Only reparse changed files.
  - Efficient database updates.
- Memory optimization:
  - Streaming file processing for large repos.
  - Efficient data structures.
  - Garbage collection optimization.

#### 5.4 User Experience Improvements

- Progress indicators for large repositories.
- Better error messages and suggestions.
- Configuration options for ignore patterns.
- Detailed logging and debug modes.

### Phase 6: Testing & Documentation

#### 6.1 Comprehensive Testing

- Unit tests for all core components.
- Integration tests with real codebases.
- Performance tests on large repositories.
- Edge case testing (circular deps, malformed code).
- MCP tool tests.

#### 6.2 Documentation & Examples

- Complete `README.md` with:
  - Installation instructions.
  - Usage examples for each MCP tool.
  - Performance characteristics.
  - Comparison with other tools.
- Technical documentation:
  - Architecture overview.
  - Database schema documentation.
  - API reference for each MCP tool.
  - Troubleshooting guide.

#### 6.3 Performance Benchmarks

- Benchmark suite:
  - Indexing performance on repos of different sizes.
  - Query performance for different patterns.
  - Memory usage analysis.
  - Comparison with RepoAtlas and other tools.

## Expected Outcomes

- **Performance**: <1s indexing for 5k files, <50ms queries.
- **Accuracy**: >95% symbol extraction accuracy.
- **Functionality**: All 5 MCP tools working reliably.
- **Impact Analysis**: Correctly identifies transitive dependencies.
- **Reliability**: Handles large repos (50k+ files) without issues.
- **Usability**: Clear, helpful responses for AI assistants.

This transforms XRAY from a "mostly works" tool into a production-ready code intelligence system that LLMs can trust for safe code modifications.
