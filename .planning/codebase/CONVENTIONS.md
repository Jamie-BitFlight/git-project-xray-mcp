# Coding Conventions

**Analysis Date:** 2026-02-07

## Naming Patterns

**Files:**
- All lowercase with underscores: `mcp_server.py`, `indexer.py`
- Test files prefixed with `test_`: `test_indexer.py`, `test_mcp_server.py`
- Core modules organized by function: `src/xray/` (main), `src/xray/core/` (engine)

**Functions/Methods:**
- snake_case for function and method names: `normalize_path()`, `get_indexer()`, `_extract_python_symbols_enhanced()`
- Private/internal methods prefixed with underscore: `_init_cache()`, `_parse_gitignore()`, `_should_exclude()`
- Public API functions (MCP tools) in lowercase: `explore_repo()`, `find_symbol()`, `what_breaks()`

**Variables:**
- snake_case throughout: `root_path`, `gitignore_patterns`, `tree_lines`, `cache_dir`
- Single letters avoided except in loops: `for i, child in enumerate(children):`
- Descriptive names with context: `symbol_name` not `sname`, `max_symbols_per_file` not `max_sym`

**Types/Classes:**
- PascalCase for classes: `XRayIndexer`, `TestXRayIndexer`, `TestMCPServer`
- Exception messages use lowercase with context: `f"Path '{path}' does not exist"`

**Constants:**
- UPPER_SNAKE_CASE for module-level constants: `DEFAULT_EXCLUSIONS`, `LANGUAGE_MAP`
- Defined at module top level (`src/xray/core/indexer.py` lines 14-59)

## Code Style

**Formatting:**
- Tool: Ruff (formatter and linter)
- Line length: 100 characters (see `pyproject.toml` line 72)
- Quote style: Double quotes only (`"` not `'`)
- Indent style: Space, 4 spaces per level
- Format check: `uv run ruff format --check src/ tests/`

**Linting:**
- Tool: Ruff with strict rules
- Rules enabled: E (errors), W (warnings), F (pyflakes), I (isort), B (bugbear), C4 (comprehensions), UP (pyupgrade)
- Rules ignored: E501 (line length - handled by formatter), B008, B904
- Check: `uv run ruff check src/ tests/`

**Type Checking:**
- Tool: mypy and basedpyright
- Configuration: `python_version = "3.10"` minimum
- Strict settings: `check_untyped_defs = true`, `warn_return_any = true`, `no_implicit_optional = true`
- Check: `uv run mypy src/`

## Import Organization

**Order (strict):**
1. Python standard library: `import os`, `import sys`, `from pathlib import Path`, `from typing import Any`
2. External third-party: `from fastmcp import FastMCP`, `from thefuzz import fuzz`
3. Local project imports: `from xray.core.indexer import XRayIndexer`

**Pattern in mcp_server.py:**
```python
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from xray.core.indexer import XRayIndexer
```

**Pattern in indexer.py:**
```python
import ast
import fnmatch
import json
import pickle
import re
import subprocess
from pathlib import Path
from typing import Any

from thefuzz import fuzz
```

**Path Aliases:**
- No path aliases configured - uses direct imports from package root
- Absolute imports only: `from xray.core.indexer import XRayIndexer`

## Error Handling

**Strategy:** Try-except with silent failures for non-critical operations

**Patterns:**

1. **Critical path errors - raise exceptions:**
```python
# src/xray/mcp_server.py:57-66
def normalize_path(path: str) -> str:
    """Normalize a path to absolute form."""
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    path = str(Path(path).resolve())
    if not os.path.exists(path):
        raise ValueError(f"Path '{path}' does not exist")
    if not os.path.isdir(path):
        raise ValueError(f"Path '{path}' is not a directory")
    return path
```

2. **MCP tool wrapper - catch and return errors as dicts:**
```python
# src/xray/mcp_server.py:136-154
@mcp.tool
def explore_repo(...) -> str:
    try:
        # ... implementation
        return tree
    except Exception as e:
        return f"Error exploring repository: {str(e)}"
```

3. **Silent failures for optional operations:**
```python
# src/xray/core/indexer.py:72-89
def _init_cache(self):
    try:
        result = subprocess.run(...)
        if result.returncode == 0:
            self.commit_sha = result.stdout.strip()
            # ...
    except Exception:
        self.commit_sha = None
        self.cache_dir = None
```

4. **Selective exception handling:**
```python
# src/xray/core/indexer.py:631-633
except FileNotFoundError:
    # ripgrep not installed, use Python fallback
    references = self._python_text_search(symbol_name)
```

**Error Messages:**
- Include context: `f"Path '{path}' does not exist"` not just `"Invalid path"`
- Return descriptive messages to callers: `f"Error exploring repository: {str(e)}"`
- For reference searches, include caveats: `f"Found {len(references)} potential references..."`

## Logging

**Framework:** None - uses print/string returns for MCP responses

**Pattern:**
- MCP tools return formatted strings for human consumption
- Error messages included in return values as strings or error dicts
- No logging library used (console output unsuitable for MCP)
- Example: `return f"Error exploring repository: {str(e)}"`

## Comments

**When to Comment:**
- Explain non-obvious logic, especially regex patterns:
```python
# Check gitignore patterns (simplified)
for pattern in gitignore_patterns:
    if pattern in str(path.relative_to(self.root_path)):
        return True
```

- Mark fallback behavior and alternatives:
```python
# Fallback to regex extraction
name = self._extract_symbol_name(text)
```

- Document complex data transformations:
```python
# Deduplicate symbols (same name and location)
seen = set()
```

**Avoid:**
- Comments restating code: `i = 0  # Set i to 0` (bad)
- Over-commenting simple logic

**JSDoc/TSDoc:**
- Not used - project is Python-only
- Python uses standard docstrings instead

## Function Design

**Size:**
- Small and focused - most methods 30-50 lines
- Recursive methods acceptable if clear: `_build_tree_recursive_enhanced()` is 77 lines but tightly scoped
- Helper methods extract complex logic: `_should_exclude()`, `_extract_symbol_name()`

**Parameters:**
- Type hints required on all functions: `def get_indexer(path: str) -> XRayIndexer:`
- Union types use `|` syntax: `max_depth: int | None = None`
- Optional parameters use defaults: `limit: int = 10`
- Multiple similar string parameters converted for LLM safety (see mcp_server.py:138-143):
```python
if max_depth is not None and isinstance(max_depth, str):
    max_depth = int(max_depth)
if isinstance(include_symbols, str):
    include_symbols = include_symbols.lower() in ("true", "1", "yes")
```

**Return Values:**
- Always typed: `-> str:`, `-> list[dict[str, Any]]:`
- Consistent return types (dict with "error" key on failure): `{"error": "message"}`
- None used explicitly: `-> str | None:`

## Module Design

**Exports:**
- No `__all__` defined - all public functions accessible
- Private functions prefixed with `_`
- MCP tools decorated with `@mcp.tool` (public contract)

**Barrel Files:**
- Not used - `src/xray/__init__.py` minimal (version only)
- Import directly from modules: `from xray.core.indexer import XRayIndexer`

**Class Design:**
- Single main class `XRayIndexer` encapsulates all indexing logic
- Private methods for implementation details
- Caching as instance state (not global)
- Clear responsibility separation: indexer handles logic, mcp_server handles API

---

*Convention analysis: 2026-02-07*
