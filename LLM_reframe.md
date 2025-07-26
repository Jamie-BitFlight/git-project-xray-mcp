XRAY-Lite: LLM-Optimized Dependency Tracking System                                                         │ │
│ │                                                                                                             │ │
│ │ Vision: Complete Code Intelligence for LLM Software Engineers                                               │ │
│ │                                                                                                             │ │
│ │ LLMs need 100% accurate dependency tracking to safely modify code. Current issues stem from a fundamental   │ │
│ │ symbol identity mismatch that causes missing dependencies.                                                  │ │
│ │                                                                                                             │ │
│ │ Core Architecture Change: Unified Symbol Identity System                                                    │ │
│ │                                                                                                             │ │
│ │ 1. Canonical Symbol IDs                                                                                     │ │
│ │                                                                                                             │ │
│ │ - Replace simple name storage with canonical IDs: file:Class.method                                         │ │
│ │ - Examples:                                                                                                 │ │
│ │   - src/xray/core/indexer.py:XRayIndexer.__init__                                                           │ │
│ │   - src/xray/parsers/python.py:PythonParser                                                                 │ │
│ │   - src/xray/mcp_server.py:build_index                                                                      │ │
│ │                                                                                                             │ │
│ │ 2. Multi-Alias Resolution System                                                                            │ │
│ │                                                                                                             │ │
│ │ Store multiple aliases per symbol:                                                                          │ │
│ │ - Canonical: src/xray/core/indexer.py:XRayIndexer.__init__                                                  │ │
│ │ - Qualified: XRayIndexer.__init__                                                                           │ │
│ │ - Simple: __init__                                                                                          │ │
│ │ - Import: Track how symbol appears in each file that imports it                                             │ │
│ │                                                                                                             │ │
│ │ 3. Enhanced Edge Creation                                                                                   │ │
│ │                                                                                                             │ │
│ │ - Create edges using canonical IDs                                                                          │ │
│ │ - Resolve dependencies through ALL aliases                                                                  │ │
│ │ - Track edge provenance (why this dependency exists)                                                        │ │
│ │                                                                                                             │ │
│ │ 4. LLM-Optimized Query Interface                                                                            │ │
│ │                                                                                                             │ │
│ │ - what_breaks('build_index') → Complete impact tree with file locations                                     │ │
│ │ - find_symbol('Python') → All matches: classes, imports, usages                                             │ │
│ │ - analyze_dependencies('User') → Full import chain + usage patterns                                         │ │
│ │                                                                                                             │ │
│ │ Implementation Plan                                                                                         │ │
│ │                                                                                                             │ │
│ │ Phase 1: Schema Redesign                                                                                    │ │
│ │                                                                                                             │ │
│ │ - Add canonical_id field to symbols table                                                                   │ │
│ │ - Add aliases table for multi-name resolution                                                               │ │
│ │ - Add edge_provenance for dependency reasoning                                                              │ │
│ │                                                                                                             │ │
│ │ Phase 2: Symbol Resolution Engine                                                                           │ │
│ │                                                                                                             │ │
│ │ - Implement canonical ID generation                                                                         │ │
│ │ - Build alias mapping system                                                                                │ │
│ │ - Create smart symbol lookup that searches all aliases                                                      │ │
│ │                                                                                                             │ │
│ │ Phase 3: Accurate Edge Detection                                                                            │ │
│ │                                                                                                             │ │
│ │ - Fix self.method() call tracking                                                                           │ │
│ │ - Implement proper import-to-usage edge creation                                                            │ │
│ │ - Add cross-file class instantiation tracking                                                               │ │
│ │                                                                                                             │ │
│ │ Phase 4: LLM Query Optimization                                                                             │ │
│ │                                                                                                             │ │
│ │ - Return complete dependency trees (not just direct dependencies)                                           │ │
│ │ - Include full context in all responses                                                                     │ │
│ │ - Add batch query capabilities for multi-symbol analysis                                                    │ │
│ │                                                                                                             │ │
│ │ Expected Outcomes                                                                                           │ │
│ │                                                                                                             │ │
│ │ ✅ what_breaks('build_index') shows MCP functions that depend on it✅ what_breaks('PythonParser') shows       │ │
│ │ indexer.py usage✅ what_breaks('__init__') shows all constructor call sites✅ LLMs can safely refactor        │ │
│ │ knowing complete impact scope                                                                               │ │
│ │                                                                                                             │ │
│ │ This transforms XRAY-Lite from a "mostly works" tool into a production-ready code intelligence system that  │ │
│ │ LLMs can trust for safe code modifications.
