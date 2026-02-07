# XRAY Backlog

Items identified from [codebase mapping](.planning/codebase/) analysis on 2026-02-07. Ungrouped — ready for grooming.

---

## New Capabilities

### Add `show_definition` tool (4th MCP tool)
Return full source code of a found symbol between its start and end lines. Completes the explore → find → read → impact workflow.
- **Why:** AI assistants find symbols but can't read the source — the biggest workflow gap
- **Refs:** [ARCHITECTURE.md](codebase/ARCHITECTURE.md), [INTEGRATIONS.md](codebase/INTEGRATIONS.md)

### Use ast-grep for JS/TS/Go symbol extraction
Replace regex-based extraction (`indexer.py:404-473`) with ast-grep patterns. ast-grep is already a dependency and supports all three languages.
- **Why:** Regex misses multiline signatures, generics, decorators, pointer receivers, complex arrow functions
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#regex-based-symbol-extraction-brittle-parsing), [STACK.md](codebase/STACK.md)

### Add more language support
Extend `LANGUAGE_MAP` with Rust, Java, C#, Ruby, C/C++. Each needs ast-grep patterns and a `LANGUAGE_MAP` entry.
- **Why:** Only 4 languages today; ast-grep/tree-sitter supports many more
- **Refs:** [ARCHITECTURE.md](codebase/ARCHITECTURE.md), [STACK.md](codebase/STACK.md)

---

## Reliability

### Add subprocess timeouts
Add `timeout=30` to all `subprocess.run()` calls (`indexer.py:76-78, 507-509, 601-609`). Handle `subprocess.TimeoutExpired` gracefully.
- **Why:** Stuck ast-grep or ripgrep hangs the MCP server indefinitely
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#subprocess-input-validation)

### Replace pickle cache with JSON
Switch `/tmp/.xray_cache/{sha}/symbols.pkl` from pickle to JSON. Move cache to `~/.cache/xray/` with `0o700` permissions.
- **Why:** Pickle in world-readable `/tmp` is a code execution risk on deserialize
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#pickle-based-caching-security-risk)

### Bound the indexer cache (LRU)
`_indexer_cache` in `mcp_server.py:54` grows unbounded. Add LRU eviction at 10-20 entries.
- **Why:** Long-running servers analyzing many repos leak memory
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#global-indexer-cache-unbounded-memory-growth)

### Add result limits to ripgrep output
Add `--max-count` to ripgrep subprocess in `what_breaks()`. Common symbol names on large codebases can return millions of lines.
- **Why:** Unbounded output can exhaust memory
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#unbounded-subprocess-output)

---

## Observability

### Add structured logging
Add `logging.getLogger(__name__)` with DEBUG/WARNING/ERROR at key points: cache hit/miss, subprocess calls, extraction failures, fallback triggers.
- **Why:** Zero logging today; silent failures are impossible to diagnose
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#no-logging-or-debugging-output)

### Narrow exception handlers
Replace bare `except Exception:` with specific types (`PermissionError`, `UnicodeDecodeError`, `json.JSONDecodeError`) and log context.
- **Why:** 11+ bare exception handlers silently swallow errors
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#broad-exception-handling-silent-failures)

---

## Testing

### Test Python text search fallback
Add dedicated tests for `_python_text_search()` with ripgrep mocked as unavailable.
- **Why:** Fallback is critical path for systems without ripgrep, currently untested
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#what_breaks-without-ripgrep), [TESTING.md](codebase/TESTING.md)

### Test cache corruption recovery
Test behavior when pickle/JSON cache file is corrupted or from a different Python version.
- **Why:** Silent recovery with no indication of cache rebuild
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#cache-corruptiondeserialization-failures), [TESTING.md](codebase/TESTING.md)

### Test LLM parameter edge cases
Test `max_depth="abc"`, missing `path` key in symbol dict, non-existent `root_path`.
- **Why:** LLMs send malformed parameters; defensive conversion code has no test coverage
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#error-scenarios-in-mcp-tool-functions), [TESTING.md](codebase/TESTING.md)

### Test large file handling
Test symbol extraction on very large files (>100MB) for timeout/memory behavior.
- **Why:** No size guard; ast.parse() or regex on huge files can hang
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#large-file-handling), [TESTING.md](codebase/TESTING.md)

---

## Minor / Low Priority

### Fix gitignore parsing
Replace substring matching with `pathspec` library or document limitations. Current impl doesn't handle negation, `**` globs, or root-anchored patterns correctly.
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#simplified-gitignore-parsing)

### Accept `root_path` in `what_breaks()`
Currently infers git root by walking up from symbol file path. Explicit parameter avoids misidentification in nested repo structures.
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#git-root-finding-logic-may-start-wrong-location)

### Validate symbol dict schema in `what_breaks()`
Check for required keys (`name`, `path`) at function entry instead of relying on generic exception handler.
- **Refs:** [CONCERNS.md](codebase/CONCERNS.md#missing-keyerror-handling-in-what_breaks)

---

*Generated from [codebase mapping](codebase/) — 2026-02-07*
