# Technology Stack

**Analysis Date:** 2026-02-07

## Languages

**Primary:**
- Python 3.10+ - All core application logic, MCP server, and symbol indexing
  - Supported versions: 3.10, 3.11, 3.12

**Secondary:**
- JavaScript/TypeScript - Supported for code analysis (not primary language)
- Go - Supported for code analysis (not primary language)

## Runtime

**Environment:**
- Python (CPython)
- Minimum: Python 3.10

**Package Manager:**
- `uv` - Fast Python package manager and installer
  - Lockfile: `pyproject.toml` (no separate lock file, uv manages it)
  - Installation: `uv venv && source .venv/bin/activate` or `uv tool install .`
  - Local install for development: `uv pip install -e .`

## Frameworks

**Core:**
- FastMCP 0.1.0+ - MCP (Model Context Protocol) server framework
  - Purpose: Serves three code analysis tools via MCP protocol
  - Entry point: `src/xray/mcp_server.py:main()`
  - Server startup: `mcp.run()`

**Development/Build:**
- hatchling - Build backend
- hatch-vcs - Automatic version derivation from git tags
- No manual version in `pyproject.toml`; versioning is git-tag based

## Key Dependencies

**Critical:**
- `fastmcp` 0.1.0+ - MCP protocol server implementation
  - Why it matters: Enables AI assistants to call the three analysis tools (explore_repo, find_symbol, what_breaks)
  - Used in: `src/xray/mcp_server.py`

- `ast-grep-cli` 0.39.0+ - Tree-sitter powered structural code search
  - Why it matters: Core engine for finding symbols (functions, classes, interfaces, types) across Python, JavaScript, TypeScript, and Go
  - External subprocess: Invoked from `src/xray/core/indexer.py` for find_symbol operations
  - Patterns defined in `indexer.py` (e.g., "def $NAME($$$):", "class $NAME")

- `thefuzz` 0.20.0+ - Fuzzy string matching library
  - Why it matters: Enables fuzzy symbol search in find_symbol tool
  - Provides: `fuzz.partial_ratio()` for matching query against symbol names
  - Imported in: `src/xray/core/indexer.py`

**Development:**
- `ruff` 0.14.10+ - Python linter and formatter
  - Config: `pyproject.toml` [tool.ruff] section
  - Line length: 100
  - Lint rules: E, W, F, I, B, C4, UP
  - Commands: `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/`

- `mypy` 1.19.1+ - Static type checker
  - Config: `pyproject.toml` [tool.mypy] section
  - Python version: 3.10
  - Command: `uv run mypy src/`
  - Overrides for thefuzz and fastmcp (ignore missing imports)

- `pytest` 9.0.2+ - Test runner
  - Config: `pyproject.toml` [tool.pytest.ini_options]
  - Test paths: `tests/`
  - Test file pattern: `test_*.py`
  - Command: `uv run pytest tests/`
  - With coverage: `uv run pytest tests/` (default adds --cov=xray)

- `pytest-cov` 7.0.0+ - Code coverage plugin for pytest
  - Reports: terminal and XML format
  - Used in: CI coverage uploads

- `basedpyright` 1.37.1+ - Alternative Python type checker (dev)

## Configuration

**Environment:**
- `.python-version` - Specifies Python 3.12 as primary version
- `pyproject.toml` - Central configuration for all tools (ruff, mypy, pytest, hatch, build)
- `.prettierignore` - Files to exclude from Prettier formatting (dev/docs)
- `.markdownlint-cli2.jsonc` - Markdown linting rules
- `package.json` - Node.js dev dependencies (prettier, markdownlint-cli2) for documentation

**Build:**
- `pyproject.toml`:
  - Build system: hatchling + hatch-vcs
  - Package name: `git-project-xray-mcp`
  - Entry point: `git-project-xray-mcp = "xray.mcp_server:main"`
  - Build targets: sdist and wheel packages
  - Python requirement: >= 3.10
  - Keywords: mcp, code-intelligence, ai-assistant, code-analysis, ast-grep, structural-search

## Platform Requirements

**Development:**
- Python 3.10, 3.11, or 3.12 installed
- `uv` package manager
- `git` installed (for commit-based caching)
- `ast-grep` CLI (installed as dependency via pyproject.toml)
- Optional: `ripgrep` (rg) for faster text search; Python fallback available

**Production (MCP Server):**
- Python 3.10+
- `uv` or `pip` for installation
- `ast-grep-cli` (auto-installed as dependency)
- Optional: `ripgrep` for performance; works without it
- Git repository required (for commit-based symbol caching)

## Installation Methods

**Development:**
```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

**As uv tool:**
```bash
uv tool install .
```

**From PyPI (published):**
```bash
pipx install git-project-xray-mcp
# or
pip install git-project-xray-mcp
```

## CI/CD & Publishing

**CI Pipeline (GitHub Actions):**
- Workflow: `.github/workflows/ci.yml`
- Triggers: push to main/develop, pull requests to main/develop
- Matrix: Python 3.10, 3.11, 3.12
- Steps:
  - Checkout with actions/checkout@v6.0.1
  - Install uv with astral-sh/setup-uv@v7.2.0
  - Install Python version with `uv python install`
  - Sync dependencies with `uv sync`
  - Lint with `ruff check src/ tests/`
  - Format check with `ruff format --check src/ tests/`
  - Type check with `mypy src/`
  - Run tests with `pytest tests/`
  - Upload coverage to Codecov (Python 3.12 only)

**Publishing (GitHub Actions):**
- Workflow: `.github/workflows/auto-publish.yml`
- Triggers: push to main branch
- Steps:
  - Create git tag using mathieudutour/github-tag-action@v6.2
  - Fetch and checkout new tag (critical for hatch-vcs to read version)
  - Build with `uv build` (creates sdist and wheel)
  - Publish to PyPI with `uv publish`
  - Create GitHub Release with artifacts
  - Requires: PyPI environment secrets and id-token permissions

---

*Stack analysis: 2026-02-07*
