# External Integrations

**Analysis Date:** 2026-02-07

## Overview

XRAY is a **stateless tool** with no persistent backend, databases, or authentication systems. All external integrations are **subprocess-based CLI tools** or read-only filesystem access. The design philosophy emphasizes progressive discovery with no persistent state beyond git-commit-keyed symbol caching.

## External Tools & Executables

### ast-grep

**Purpose:** Structural code analysis and symbol discovery via tree-sitter parsers

**Integration Points:**
- `src/xray/core/indexer.py` - `find_symbol()` method (line 506)
- subprocess call: `["ast-grep", "--pattern", pattern, "--json", str(self.root_path)]`

**Patterns Supported:**
- Python: `def $NAME($$$):`, `class $NAME($$$):`, `async def $NAME($$$):`
- JavaScript/TypeScript: `function $NAME($$$)`, `const $NAME = ($$$) =>`, `class $NAME`, `interface $NAME`, `type $NAME =`
- Go: `func $NAME($$$)`, `func ($$$) $NAME($$$)`, `type $NAME struct`, `type $NAME interface`

**Output Format:** JSON
- Parses metavariables and location data (file path, line numbers)
- Error handling: Gracefully continues if ast-grep fails

**Installation:** Bundled as `ast-grep-cli>=0.39.0` dependency in `pyproject.toml`

### ripgrep (rg) - Optional

**Purpose:** Fast multi-threaded text search for reverse dependency analysis

**Integration Points:**
- `src/xray/core/indexer.py` - `what_breaks()` method (line 601)
- subprocess call: `["rg", "-w", "--json", symbol_name, str(self.root_path)]`
- Fallback: Python implementation `_python_text_search()` if ripgrep unavailable

**Output Format:** JSON streaming (one JSON object per line)
- Each match includes: file path, line number, line text

**Availability:**
- External dependency (NOT in pyproject.toml)
- Must be installed separately: `brew install ripgrep` or system package manager
- FileNotFoundError handling triggers Python fallback

**Why Optional:**
- Performance improvement (3-10x faster on large codebases)
- Python fallback maintains functionality without it

### git

**Purpose:** Commit SHA extraction for cache key generation

**Integration Points:**
- `src/xray/core/indexer.py` - `_init_cache()` method (line 76)
- subprocess call: `["git", "rev-parse", "HEAD"]` in repository root

**Usage:**
- Extracts current commit SHA
- Creates cache directory: `/tmp/.xray_cache/{commit_sha}/`
- Enables symbol cache reuse across runs without file modification detection overhead

**Behavior:**
- Non-fatal if not in git repo: Sets `commit_sha = None`, disables caching
- Required for cache performance feature, not required for core functionality

## Data Storage

**Cache Storage:**
- Type: Local filesystem pickle
- Location: `/tmp/.xray_cache/{commit_sha}/symbols.pkl`
- Format: Python pickle (binary)
- Lifetime: Session-based (not cleaned up automatically)
- Keyed by: Git commit SHA

**Cache Contents:**
- Symbol extraction results indexed by file path
- Cache keys: `{file_path}:{mtime}:{size}` for invalidation
- File location: `src/xray/core/indexer.py` - `_get_cache_key()` (line 116)

**No Database:**
- No SQL/NoSQL database used
- No persistent index
- No network storage
- All analysis runs fresh per request

**Gitignore Patterns:**
- Read from `.gitignore` if present (respects project's version control)
- Patterns cached at runtime, not persisted

## File Storage

**Local Filesystem Only:**
- No cloud storage integration
- No S3, GCS, or similar
- Analysis works on local file paths only
- Supports absolute paths: `/Users/john/project` or `~/project` (expanded via `os.path.expanduser()`)

**Language Support:**
Language map defined in `src/xray/core/indexer.py` (line 51):
- `.py` → Python
- `.js`, `.jsx`, `.mjs` → JavaScript
- `.ts`, `.tsx` → TypeScript
- `.go` → Go

## Authentication & Identity

**None Implemented:**
- No user authentication
- No API keys or tokens
- No auth providers (OAuth, SAML, etc.)
- Stateless by design
- Suitable for local development or integrated into MCP platforms with their own auth

## Monitoring & Observability

**Error Tracking:**
- None (no external service integration)
- Errors returned as strings/dicts in tool responses
- Designed for MCP client (AI assistant) to handle errors gracefully

**Logging:**
- None (no logging framework)
- Output via tool return values only
- No log files or centralized logging
- Subprocess stderr captured but not logged

**Caching as Observability:**
- Git commit SHA used as cache key
- Cache hit/miss implicit (no metrics exposed)

## CI/CD & Deployment

**Hosting:**
- PyPI (Python Package Index)
- Not a web service (no server deployment needed)
- Installable via pip or uv

**CI Pipeline:**
- GitHub Actions (`.github/workflows/ci.yml`)
- Runs on: ubuntu-latest
- Python versions tested: 3.10, 3.11, 3.12
- Services: codecov for coverage reporting

**Publishing Pipeline:**
- GitHub Actions (`.github/workflows/auto-publish.yml`)
- Triggered: Push to main branch
- Auto-tagging: mathieudutour/github-tag-action@v6.2
- Build: `uv build` (creates wheel + sdist)
- Publish: `uv publish` (uploads to PyPI)
- Environment: PyPI with id-token authentication

## Webhooks & Callbacks

**None Implemented:**
- XRAY is pull-only (no push/webhook model)
- Clients call tools; tools don't callback
- MCP server is stateless request/response only

## Environment Configuration

**Required Environment Variables:**
- None for basic operation
- All configuration in `pyproject.toml` or command-line arguments

**Optional Environment Variables:**
- `XRAY_CACHE_DIR` - Not currently used (hardcoded to `/tmp/.xray_cache/`)
- Standard Python: `PYTHONPATH`, `PYTHONDONTWRITEBYTECODE`, etc.

**CI/CD Secrets:**
- `GITHUB_TOKEN` - For auto-tagging (provided by GitHub Actions)
- PyPI token (via environment secret) - For publishing to PyPI
- Codecov token (optional) - For coverage integration

**Secrets Storage:**
- None for runtime
- CI/CD secrets in GitHub repository settings (encrypted)
- No `.env` file used in this project

## API Integrations

**None:**
- XRAY does not call external APIs
- MCP clients call XRAY; XRAY doesn't call external services
- All analysis is local

## Subprocess Dependencies

**Management:**
- `ast-grep`: Installed as Python package dependency
- `ripgrep`: External tool (optional), not packaged
- `git`: System utility (expected to exist)

**Error Handling:**
- `subprocess.run()` used throughout
- `capture_output=True` for all calls
- Return code checking for success/failure
- JSON parsing with error handling (json.JSONDecodeError caught)

## Development Tool Integrations

**Formatters/Linters (Not Runtime):**
- Prettier 3.7.4+ (dev, for docs)
- Markdownlint-cli2 0.20.0+ (dev, for docs)
- Ruff (linting/formatting)
- MyPy (type checking)

**All development tools are specified in `pyproject.toml` or `package.json` and run only during CI/development.**

## Network & Remote Access

**None:**
- No network calls
- No HTTP requests
- No DNS lookups
- No remote file access
- Git integration is local-only (`.git/` directory)

## Performance Integrations

**Symbol Caching:**
- Per-commit caching in `/tmp/.xray_cache/` reduces redundant ast-grep calls
- Invalidation: Commit SHA mismatch or manual cache clear

**Text Search Optimization:**
- ripgrep integration for faster reference discovery
- Python fallback maintains 100% functionality

---

*Integration audit: 2026-02-07*
