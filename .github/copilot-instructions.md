# GitHub Copilot Instructions for XRAY MCP

## Repository Overview

**XRAY** is a Model Context Protocol (MCP) server providing progressive code intelligence for AI assistants. It uses ast-grep (tree-sitter powered) for structural code analysis without requiring language servers or databases.

**Core Capabilities:**
- `explore_repo` - Progressive codebase exploration (directories → symbols)
- `find_symbol` - Fuzzy symbol search (functions, classes, methods)
- `what_breaks` - Reverse dependency analysis (find references)

**Repository Stats:**
- ~5MB source code (excluding .git and .venv)
- Primary language: Python 3.10+
- 4 Python source files in `src/xray/`
- ~900 lines of core code (mcp_server.py + indexer.py)
- Stateless design with git-commit-based caching

**Key Technologies:**
- **FastMCP** (≥0.1.0) - MCP server framework
- **ast-grep-cli** (≥0.39.0) - Structural code search
- **thefuzz** (≥0.20.0) - Fuzzy string matching
- **uv** - Fast Python package manager (recommended)

## Build & Installation Commands

### Prerequisites

**ALWAYS check these first:**
```bash
python --version  # Must be ≥3.10
uv --version      # If not installed: pip install uv
```

### Development Installation (RECOMMENDED)

**Use this sequence for local development:**
```bash
# 1. Create virtual environment (ALWAYS do this first)
uv venv

# 2. Install in editable mode (MUST be run from repo root)
uv pip install -e .

# 3. Verify installation
python -m xray.mcp_server --help
# Expected: FastMCP banner with "XRAY Code Intelligence" server name
```

**CRITICAL:** The server is an MCP server, NOT a CLI tool. It expects stdio communication from MCP clients. The `--help` output shows it's working but will wait for MCP protocol messages.

### Building the Package

```bash
# Clean build (ALWAYS clean before building for distribution)
rm -rf dist/ build/ *.egg-info/

# Build package (takes ~30 seconds)
uv build
# Expected output: 
#   Successfully built dist/git_project_xray_mcp-VERSION.tar.gz
#   Successfully built dist/git_project_xray_mcp-VERSION-py3-none-any.whl

# Verify artifacts
ls dist/
# Should show: .tar.gz and .whl files
```

**NOTE:** You may see a warning about shallow git clone - this is expected in CI environments and does not affect the build.

### Installation Methods for End Users

**From PyPI (for users):**
```bash
pip install git-project-xray-mcp
# Or faster with uv:
uv pip install git-project-xray-mcp
```

**As uv tool (recommended for regular use):**
```bash
uv tool install .
# Now available globally as: git-project-xray-mcp
```

**Quick test without installation:**
```bash
uvx --from . git-project-xray-mcp
```

### Configuration Generation

**Generate MCP config for AI assistants:**
```bash
# For Claude Desktop
uv run mcp-config-generator.py claude docker

# For Cursor
uv run mcp-config-generator.py cursor local_python

# For VS Code
uv run mcp-config-generator.py vscode source
```

## Testing

**Current Status:** No formal test suite exists. Testing is done manually via MCP Inspector.

**Testing the MCP Server:**
```bash
# ALWAYS test from repo root with MCP Inspector

# List available tools
npx @modelcontextprotocol/inspector \
  --cli uvx --from . git-project-xray-mcp \
  --method tools/list

# Test explore_repo tool
npx @modelcontextprotocol/inspector \
  --cli uvx --from . git-project-xray-mcp \
  --method tools/call \
  --tool-name explore_repo \
  --tool-arg 'root_path=/tmp' \
  --tool-arg 'max_depth=2'
```

**When tests are added, use:**
```bash
uv run pytest tests/test_file.py -xvs --no-cov
```

## Project Architecture

### Directory Structure

```
git-project-xray-mcp/
├── .github/
│   └── workflows/
│       └── auto-publish.yml    # Auto-publish to PyPI on push to main
├── src/xray/
│   ├── mcp_server.py          # FastMCP server, tool definitions, entry point
│   ├── core/
│   │   └── indexer.py         # XRayIndexer class, ast-grep orchestration
│   └── lsp_config.json        # Language server config (for reference)
├── tests/                      # Minimal test suite
├── test_samples/              # Sample files for testing
├── sessions/                   # cc-sessions framework files
├── install.sh                 # Automated installation script
├── uninstall.sh              # Uninstallation script
├── mcp-config-generator.py   # Generate MCP configs
├── pyproject.toml            # Project metadata, uses hatch-vcs
├── CLAUDE.md                 # Detailed dev guide for Claude Code
├── README.md                 # User-facing documentation
└── getting_started.md        # Installation guide
```

### Key Source Files

**`src/xray/mcp_server.py` (287 lines):**
- FastMCP server initialization
- Three MCP tools: `explore_repo`, `find_symbol`, `what_breaks`
- Path normalization and validation
- Indexer caching per repository path
- Entry point: `main()` function

**`src/xray/core/indexer.py` (625 lines):**
- `XRayIndexer` class - core analysis engine
- Git-based caching using commit SHA
- File tree generation with progressive symbol inclusion
- ast-grep subprocess management
- Fuzzy symbol matching via thefuzz
- Ripgrep integration with Python fallback

**Entry Point:**
```toml
[project.scripts]
git-project-xray-mcp = "xray.mcp_server:main"
```

### Data Flow

```
AI Assistant (via MCP Client)
    ↓
FastMCP Server (mcp_server.py)
    ↓
XRayIndexer (indexer.py)
    ↓
ast-grep subprocess (structural analysis)
 OR
ripgrep subprocess (reference search)
    ↓
Results formatted and returned
```

### Caching Strategy

- **Cache key:** Git commit SHA + file mtime + file size
- **Cache location:** `/tmp/.xray_cache/{commit_sha}/symbols.pkl`
- **Invalidation:** Automatic per git commit change
- **No database required:** Stateless design

### Language Support (via ast-grep)

```python
LANGUAGE_MAP = {
    ".py": "python",       # Functions, classes, methods, async
    ".js": "javascript",   # Functions, classes, arrows
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",   # All JS + interfaces, types
    ".tsx": "typescript",
    ".go": "go",           # Functions, structs, interfaces
}
```

## CI/CD Pipeline

### GitHub Actions Auto-Publish Workflow

**File:** `.github/workflows/auto-publish.yml`

**Trigger:** Every push to `main` branch

**Process:**
1. Creates annotated git tag (e.g., v0.2.4) via github-tag-action
2. **CRITICAL STEP:** Fetches tags and checks out new tag
   - Enables hatch-vcs to read version from git tag
   - Without this, build fails
3. Installs uv and Python
4. Builds package with `uv build`
5. Publishes to PyPI using Trusted Publishing (id-token:write)
6. Creates GitHub Release with artifacts

**Version Management:**
- Uses `hatch-vcs` to extract version from git tags
- NO manual version updates in pyproject.toml
- Version computed at build time from checked-out tag

**Key Implementation Detail:**
```yaml
- name: Fetch tags and checkout new tag
  run: |
    git fetch --tags
    git checkout ${{ steps.tag_version.outputs.new_tag }}
```

## Important Development Patterns

### Path Normalization (ALWAYS Required)

```python
# In mcp_server.py:57-66
path = os.path.expanduser(path)  # Expand ~
path = os.path.abspath(path)     # Make absolute
path = str(Path(path).resolve()) # Resolve symlinks
```

**Why:** MCP tools receive paths from AI assistants that may be relative or contain ~.

### String Parameter Handling (LLM Defense)

```python
# LLMs may pass strings for all parameters
if max_depth is not None and isinstance(max_depth, str):
    max_depth = int(max_depth)
if isinstance(include_symbols, str):
    include_symbols = include_symbols.lower() in ('true', '1', 'yes')
```

**Apply this pattern when adding new tool parameters.**

### Error Handling (Return, Don't Raise)

```python
try:
    # ... operation ...
except Exception as e:
    return f"Error exploring repository: {str(e)}"
```

**Why:** MCP tools should return user-friendly messages, not crash.

### Default Exclusions

```python
DEFAULT_EXCLUSIONS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git",
    "build", "dist", "target", ".idea", ".vscode", ".xray"
}
```

**Plus:** Respects .gitignore patterns

### Progressive Discovery Pattern

**Encourage this workflow in tools:**
1. Directories only (`include_symbols=False`)
2. Focus on specific dirs (`focus_dirs=["src"]`, `include_symbols=True`)
3. Find specific symbols (`find_symbol()`)
4. Analyze impact (`what_breaks()`)

## Making Changes

### When Editing Code

**ALWAYS:**
1. Test with MCP Inspector after changes
2. Verify path normalization for new parameters
3. Add defensive string-to-type conversions
4. Return error messages instead of raising exceptions
5. Update docstrings with examples

**NEVER:**
1. Add persistent state (stateless design principle)
2. Use regex for structural code analysis (use ast-grep)
3. Require external language servers
4. Break the progressive discovery pattern

### Build Validation Sequence

```bash
# 1. Clean environment
rm -rf dist/ build/ *.egg-info/ .venv/

# 2. Fresh install
uv venv
uv pip install -e .

# 3. Test server starts
python -m xray.mcp_server --help
# Should show FastMCP banner (then wait for MCP messages)

# 4. Test with MCP Inspector
npx @modelcontextprotocol/inspector \
  --cli uvx --from . git-project-xray-mcp \
  --method tools/list

# 5. Build package
uv build

# 6. Verify artifacts
ls dist/
```

### Adding New Dependencies

**CRITICAL:** Run security check FIRST:
```bash
# Check for vulnerabilities before adding
# (Use appropriate security scanning tool)
```

**Then update pyproject.toml:**
```toml
dependencies = [
    "fastmcp>=0.1.0",
    "ast-grep-cli>=0.39.0",
    "thefuzz>=0.20.0",
    "new-package>=version",  # Add here
]
```

## Common Pitfalls & Solutions

### Issue: Server hangs after starting
**Why:** MCP servers wait for stdio messages from clients
**Solution:** Use MCP Inspector or configure in AI assistant

### Issue: Build fails with version error
**Why:** hatch-vcs can't read git tag (shallow clone or not checked out)
**Solution:** Ensure `git fetch --tags` and checkout tag in CI

### Issue: ast-grep not found
**Why:** ast-grep-cli package installs Python bindings, not binary
**Solution:** The package includes ast-grep binary, no separate install needed

### Issue: Cache not working
**Why:** Not a git repository or uncommitted changes
**Solution:** Cache uses commit SHA, ensure git repo exists

## Trust These Instructions

**These instructions have been validated by:**
- Testing build commands in clean environment
- Verifying installation methods work
- Running the MCP server successfully
- Examining all source files and documentation
- Testing the CI/CD workflow configuration

**Only perform additional searches if:**
- Instructions are incomplete for your specific task
- Instructions are found to be incorrect
- You need details about areas not covered here

For detailed development patterns and architecture, see `CLAUDE.md`.
