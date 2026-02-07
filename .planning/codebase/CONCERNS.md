# Codebase Concerns

**Analysis Date:** 2026-02-07

## Tech Debt

### Broad Exception Handling (Silent Failures)

**Issue:** Multiple bare `except Exception:` clauses throughout the codebase silently swallow errors, making debugging and troubleshooting extremely difficult. Errors are either logged nothing or reduced to generic strings.

**Files:**
- `src/xray/core/indexer.py` lines 87, 101, 113, 121, 179, 332, 400, 668
- `src/xray/mcp_server.py` lines 153, 204, 278

**Impact:**
- Silent failures in cache loading/saving mean stale or corrupted cache is used without warning
- Symbol extraction failures return empty lists with no indication why
- File read failures in text search are silently skipped, potentially missing relevant references
- Debugging production issues is impossible without proper error context

**Fix approach:**
Replace bare `except Exception:` with specific exception types and proper logging. Use structured logging (e.g., `logging` module) to record errors with context. At minimum:
```python
except PermissionError:
    logger.warning(f"Permission denied reading {file_path}")
except UnicodeDecodeError:
    logger.debug(f"Could not decode {file_path} as UTF-8")
except Exception as e:
    logger.error(f"Unexpected error in cache_load: {type(e).__name__}: {e}")
```

### Pickle-Based Caching (Security Risk)

**Issue:** Symbol cache uses Python's `pickle` module for serialization in `src/xray/core/indexer.py` lines 100, 112. Pickle can deserialize arbitrary Python objects, creating a potential security vulnerability if cache files are tampered with or created from untrusted sources.

**Files:**
- `src/xray/core/indexer.py` lines 96-102 (load), 109-114 (save)

**Impact:**
- Malicious cache file could execute arbitrary code during deserialization
- Cache files in `/tmp/.xray_cache/` are world-readable on many systems
- No integrity verification (hash/signature) of cached data

**Fix approach:**
- Replace pickle with JSON (safer, human-readable) for symbol metadata
- Use `json.dumps()` / `json.loads()` instead of pickle
- Add integrity check (HMAC or hash) if rebuilding caching is too large
- Store cache in user-specific directory (e.g., `~/.cache/xray/`) instead of shared `/tmp`

## Known Bugs

### Git Root Finding Logic May Start Wrong Location

**Issue:** In `src/xray/mcp_server.py` lines 264-274, the `what_breaks()` function attempts to find a git repository by walking up from the symbol's file directory. However, it starts from `symbol_path.parent` (the file's directory), not the actual repository root. If a symbol file is in a nested directory, searching could begin mid-repository.

**Files:**
- `src/xray/mcp_server.py` lines 264-274

**Trigger:** Call `what_breaks()` with a symbol from a nested directory in a project with multiple git repos or complex directory structure

**Workaround:** Pass full absolute path as symbol's 'path' field; ensure it's from the original `explore_repo()` call

**Better fix:** Accept `root_path` as explicit parameter to `what_breaks()` rather than inferring it

### Missing KeyError Handling in what_breaks()

**Issue:** `src/xray/mcp_server.py` line 264 accesses `exact_symbol["path"]` without checking if the key exists. If a malformed symbol object is passed, it raises KeyError, caught by the generic `except Exception` handler.

**Files:**
- `src/xray/mcp_server.py` lines 209-279

**Trigger:** Call `what_breaks()` with dict missing 'path' key

**Current mitigation:** Generic exception handler returns error dict

**Recommendations:**
- Validate `exact_symbol` schema at function entry:
```python
required_keys = {"name", "path"}
if not all(k in exact_symbol for k in required_keys):
    return {"error": "Invalid symbol object: missing 'name' or 'path'"}
```

## Security Considerations

### Subprocess Input Validation

**Risk:** While `src/xray/core/indexer.py` uses safe subprocess patterns (fixed argument lists instead of shell=True), there's no timeout handling on subprocess calls. A stuck `ast-grep` or `ripgrep` process could hang indefinitely.

**Files:**
- `src/xray/core/indexer.py` lines 76-78, 507-509, 601-609

**Current mitigation:** Using fixed argument lists prevents shell injection; capture_output=True prevents stderr spam

**Recommendations:**
- Add `timeout=30` parameter to all subprocess.run() calls
- Implement cleanup/cancellation on timeout:
```python
try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
except subprocess.TimeoutExpired:
    logger.warning(f"Command timed out: {cmd}")
    return []
```

### Unbounded Subprocess Output

**Risk:** `what_breaks()` in `src/xray/core/indexer.py` (lines 601-627) fetches all ripgrep results without size limit. A large codebase with a common symbol name could return millions of lines, exhausting memory.

**Files:**
- `src/xray/core/indexer.py` lines 601-627

**Current mitigation:** No explicit limit; relies on ripgrep's performance

**Recommendations:**
- Limit results: `cmd += ["--max-count", "10000"]` to ripgrep
- Implement pagination for large result sets
- Document expected performance with result count in docstring

## Performance Bottlenecks

### Python Fallback Text Search (Slow on Large Codebases)

**Problem:** `_python_text_search()` in `src/xray/core/indexer.py` (lines 641-671) reads entire files and applies regex to each line sequentially. On large codebases (10k+ files), this is significantly slower than ripgrep.

**Files:**
- `src/xray/core/indexer.py` lines 641-671

**Cause:**
- No parallel processing
- Reads entire file into memory
- Regex compilation happens per-line in loop
- No early termination

**Improvement path:**
```python
# Pre-compile regex once
pattern = re.compile(r"\b" + re.escape(symbol_name) + r"\b")

# Compile in directory traversal to skip more aggressively
# Use ThreadPoolExecutor for parallel file reads
# Break after finding N results
```

## Fragile Areas

### Regex-Based Symbol Extraction (Brittle Parsing)

**Files:**
- `src/xray/core/indexer.py` lines 404-473 (JS/TS/Go patterns)

**Why fragile:**
- Regex patterns in lines 410-463 don't handle multiline function definitions
- Doesn't account for decorators (e.g., `@decorator def foo():`)
- Comments on same line as definition break extraction (pattern assumes comment-newline-definition)
- Arrow functions with complex types not handled: `const fn = (a: Type<Generic>) => {}`
- Go methods with pointer receivers: `func (r *Receiver) Method()` may not match
- Class definitions with generics not handled: `class Foo<T> extends Bar`

**Safe modification:**
- Only modify test cases first; add test for each regex pattern edge case
- Consider switching to `ast-grep` patterns for JS/TS/Go instead of regex (requires ast-grep support for those languages)
- Test coverage: `tests/test_indexer.py` lacks parameterized tests for symbol extraction edge cases

**Test coverage gaps:** No tests for:
- Multiline function signatures
- Decorated functions
- Comments before function definitions
- Complex generic types
- Methods in classes

### Simplified Gitignore Parsing

**Files:**
- `src/xray/core/indexer.py` lines 167-182, 197-203

**Why fragile:**
- Line 199: substring matching `if pattern in str(path.relative_to(...))`  doesn't handle patterns correctly
- No support for negation patterns (e.g., `!important.log`)
- No support for `**` glob patterns
- Comments and blank lines handled, but edge cases (whitespace, empty patterns) not validated

**Potential misses:**
- Pattern `src/` won't properly exclude `src/` directory at any level
- Pattern `/build/` (leading slash for root-only) treated same as `build/`

**Safe modification:**
- Use `pathspec` library (lightweight, standard gitignore spec)
- Alternative: stick with simple patterns but document limitations
- Test with real .gitignore files from popular projects

## Scaling Limits

### Global Indexer Cache (Unbounded Memory Growth)

**Issue:** `_indexer_cache` in `src/xray/mcp_server.py` line 54 is a global dict that grows indefinitely. In long-running MCP servers (days/weeks), this accumulates indexer instances, one per unique root path.

**Current capacity:**
- Each XRayIndexer holds `_cache` dict (symbol cache, typically < 1MB for projects < 100k lines)
- Typical: 1-5 indexers (most projects analyze one repo)
- Risk scenario: Service analyzing 1000+ repos sequentially = unbounded growth

**Scaling path:**
- Implement LRU cache: `from functools import lru_cache` or `cachetools.LRUCache`
- Set max size: keep only 10-20 most recent indexers
- Add cache statistics endpoint to monitor growth:
```python
_indexer_cache = {}
_max_indexers = 20

def get_indexer(path: str) -> XRayIndexer:
    # ... existing normalize_path logic
    if len(_indexer_cache) >= _max_indexers:
        # Remove oldest entry
        oldest = next(iter(_indexer_cache))
        del _indexer_cache[oldest]
    # ... rest of function
```

### Hard-Coded /tmp Cache Directory

**Issue:** `src/xray/core/indexer.py` line 81 uses `/tmp/.xray_cache/` which may not exist or be writable on all systems.

**Limit:**
- On some systems `/tmp` is cleaned on reboot
- On containerized environments, `/tmp` may have limited space or permissions
- Shared `/tmp` means cache is world-readable (user isolation issue)

**Scaling path:**
- Use XDG Base Directory spec: `$XDG_CACHE_HOME/xray/` or `~/.cache/xray/`
- Fallback to `~/.xray_cache` if XDG not available
- Create directory with user-only permissions (mode 0o700)
- Handle permission errors gracefully (disable caching, don't fail)

## Test Coverage Gaps

### what_breaks() Without Ripgrep

**What's not tested:** The Python fallback in `_python_text_search()` is only tested when ripgrep is unavailable. Currently only one test (`test_find_symbol_basic`) skips if ast-grep missing, but there's no explicit test for the ripgrep fallback path.

**Files:**
- `src/xray/core/indexer.py` lines 641-671 (fallback implementation)
- `tests/test_indexer.py` - no dedicated test

**Risk:** Fallback code could have bugs that aren't caught because ripgrep is usually available in test environments

**Priority:** HIGH - fallback is critical path for systems without ripgrep

**Recommended tests:**
```python
def test_what_breaks_uses_python_fallback(temp_repo, monkeypatch):
    """Test what_breaks() uses Python fallback when ripgrep unavailable."""
    # Mock subprocess.run to raise FileNotFoundError for ripgrep
    # Verify _python_text_search() is called
    # Verify results are correct

def test_python_text_search_performance(large_repo):
    """Benchmark Python fallback on realistic codebase."""
```

### Cache Corruption/Deserialization Failures

**What's not tested:** What happens when cached pickle file is corrupted or from a different Python version?

**Files:**
- `src/xray/core/indexer.py` lines 91-102 (load path)
- `tests/test_indexer.py` - no error case

**Risk:** Silently fails and regenerates cache without warning

**Recommended test:**
```python
def test_corrupted_cache_gracefully_recovers(temp_repo, monkeypatch):
    """Test that corrupted cache doesn't crash the system."""
    # Create corrupted pickle file
    # Call explore_repo() with include_symbols=True
    # Verify it recovers and re-generates cache
```

### Large File Handling

**What's not tested:** How system handles very large files (> 100MB source files)

**Files:**
- `src/xray/core/indexer.py` line 319 (file read into memory)
- `tests/test_indexer.py` - no large file test

**Risk:**
- Out of memory errors on large single files
- Regex parsing becomes very slow
- ast.parse() or subprocess on huge files hangs

**Recommended test:**
```python
def test_large_file_extraction(tmp_path):
    """Test symbol extraction on 100MB file."""
    # Create a large synthetic file
    # Verify timeout or memory limit is respected
    # Verify partial results or graceful failure
```

### Error Scenarios in MCP Tool Functions

**What's not tested:**
- What happens when explore_repo() gets invalid max_depth string ("abc" instead of "5")
- Parameter conversion in mcp_server.py lines 138-143 (defensive string-to-type conversion)
- Non-existent root_path passed to any tool

**Files:**
- `src/xray/mcp_server.py` lines 78-154 (explore_repo)
- `tests/test_mcp_server.py` - no parameter validation tests

**Risk:** LLMs may send malformed parameters; system should handle gracefully

**Recommended tests:**
```python
def test_explore_repo_invalid_max_depth():
    """Test max_depth="not-a-number" handling."""

def test_explore_repo_nonexistent_path():
    """Test with non-existent directory."""
```

## Reliability Issues

### No Logging or Debugging Output

**Issue:** No structured logging in codebase. Errors are caught and converted to strings, but there's no log trail for troubleshooting production issues.

**Files:**
- All files - no `logging` module usage

**Impact:**
- Cannot debug why symbol extraction fails on specific repos
- Cannot monitor cache hit/miss rates
- Cannot identify performance bottlenecks in production
- MCP clients receive only final error message, not execution trace

**Recommendations:**
```python
import logging
logger = logging.getLogger(__name__)

# In _init_cache():
try:
    result = subprocess.run(...)
    logger.debug(f"Git commit: {self.commit_sha}")
except Exception as e:
    logger.warning(f"Could not initialize cache: {e}")
```

---

*Concerns audit: 2026-02-07*
