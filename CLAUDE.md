# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XRAY is an MCP (Model Context Protocol) server providing progressive code intelligence for AI assistants. It uses ast-grep (tree-sitter powered) for structural code analysis -- no database, no persistent index, all analysis runs fresh via ast-grep with smart caching per git commit.

Three tools: `explore_repo` (map codebase), `find_symbol` (fuzzy search), `what_breaks` (reverse dependency/reference search).

## Development Commands

```bash
# Setup (development)
uv venv && source .venv/bin/activate
uv pip install -e .

# Or install as uv tool from source
uv tool install .

# Lint
uv run ruff check src/ tests/
uv run ruff check --fix src/ tests/    # auto-fix

# Format
uv run ruff format src/ tests/
uv run ruff format --check src/ tests/  # check only

# Type check
uv run mypy src/

# Test
uv run pytest tests/
uv run pytest tests/test_file.py -xvs --no-cov          # single file
uv run pytest tests/test_file.py::TestClass::test_method -xvs --no-cov  # single test

# Build
uv build

# Test the MCP server manually (MCP Inspector)
npx @modelcontextprotocol/inspector --cli uvx --from . git-project-xray-mcp --method tools/list
```

CI runs ruff check, ruff format --check, mypy, and pytest across Python 3.10/3.11/3.12 on push/PR to main/develop.

## Architecture

Two source files contain all the logic (~960 lines total):

**`src/xray/mcp_server.py`** -- FastMCP server with three tool definitions (`explore_repo`, `find_symbol`, `what_breaks`). Handles path normalization, defensive string-to-type parameter conversion, and indexer caching per repository path. Entry point: `main()` → `mcp.run()`.

**`src/xray/core/indexer.py`** -- `XRayIndexer` class, the core engine. Orchestrates ast-grep subprocesses for structural code search, uses Python `ast` module for Python symbol extraction (regex-based for JS/TS/Go), integrates ripgrep for reference search (Python fallback if unavailable), and manages git-commit-based caching (`/tmp/.xray_cache/{commit_sha}/symbols.pkl`).

Data flow: MCP client request → FastMCP server → XRayIndexer → ast-grep/ripgrep subprocess → formatted results returned.

## Key Development Patterns

**LLM string parameter defense**: LLMs may pass strings for all parameters. Always convert defensively:
```python
if max_depth is not None and isinstance(max_depth, str):
    max_depth = int(max_depth)
if isinstance(include_symbols, str):
    include_symbols = include_symbols.lower() in ('true', '1', 'yes')
```
Apply this to any new tool parameter.

**Path normalization**: All paths go through `normalize_path()` which expands `~`, makes absolute, resolves symlinks, and validates existence.

**Error handling**: MCP tool functions return error strings/dicts instead of raising exceptions, so AI assistants always get useful output.

**Stateless design**: No persistent state beyond git-commit-keyed caching. Do not add databases or persistent indexes.

**Progressive discovery**: Tools are designed for incremental use -- directories first, then symbols in focused areas, then specific symbol search, then impact analysis.

## Version Management

Version is automatically derived from git tags via `hatch-vcs`. No manual version in pyproject.toml. The CI auto-publish workflow (`auto-publish.yml`) creates a git tag on push to main, then critically fetches and checks out that tag before building so hatch-vcs can read it.

## Language Support

Defined in `LANGUAGE_MAP` in indexer.py. Supported: Python (.py), JavaScript (.js/.jsx/.mjs), TypeScript (.ts/.tsx), Go (.go). Python uses the `ast` module for accurate parsing; JS/TS/Go use regex-based extraction.

## Claude Code Sessions Integration

This repository uses the cc-sessions framework. See `sessions/CLAUDE.sessions.md` for collaboration workflows and DAIC mode protocols.
