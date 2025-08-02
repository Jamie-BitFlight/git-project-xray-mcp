# Getting Started with XRAY - Modern Installation with uv

XRAY is a zero-dependency code intelligence system that enhances AI assistants' understanding of codebases. This guide shows how to install and use XRAY with the modern `uv` package manager.

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Installing uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

## Installation Options

### Option 1: Quick Try with uvx (Recommended for Testing)

Run XRAY directly without installation using `uvx`:

```bash
# Clone the repository
git clone https://github.com/srijanshukla18/xray.git
cd xray

# Run XRAY directly with uvx
uvx --from . xray-mcp
```

### Option 2: Install as a Tool (Recommended for Regular Use)

Install XRAY as a persistent tool:

```bash
# Clone and install
git clone https://github.com/srijanshukla18/xray.git
cd xray

# Install with uv
uv tool install .

# Now you can run xray-mcp from anywhere
xray-mcp
```

### Option 3: Development Installation

For contributing or modifying XRAY:

```bash
# Clone the repository
git clone https://github.com/srijanshukla18/xray.git
cd xray

# Create and activate virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
uv pip install -e .

# Run the server
python -m xray.mcp_server
```

### Option 4: Direct from GitHub (Coming Soon)

Once published to PyPI:

```bash
# Install directly
uv tool install xray

# Or run without installation
uvx xray
```

## Configure Your AI Assistant

After installation, configure your AI assistant to use XRAY:

### Claude CLI (Claude Code)

For Claude CLI users, simply run:

```bash
claude mcp add xray xray-mcp -s local
```

Then verify it's connected:

```bash
claude mcp list | grep xray
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "xray": {
      "command": "uvx",
      "args": ["--from", "/path/to/xray", "xray-mcp"]
    }
  }
}
```

Or if installed as a tool:

```json
{
  "mcpServers": {
    "xray": {
      "command": "xray-mcp"
    }
  }
}
```

### Cursor

Settings → Cursor Settings → MCP → Add new global MCP server:

```json
{
  "mcpServers": {
    "xray": {
      "command": "xray-mcp"
    }
  }
}
```

## No External Dependencies Required!

One of XRAY's best features is that it requires **zero external dependencies**. You don't need to install any language servers, binaries, or tools. XRAY uses:

- **Python**: Built-in `ast` module for 100% accurate parsing
- **JavaScript/TypeScript/Go**: Intelligent pattern matching

This means you can start using XRAY immediately after installation with no additional setup!

## Verify Installation

### 1. Check XRAY is accessible

```bash
# If installed as tool
xray-mcp --version

# If using uvx
uvx --from /path/to/xray xray-mcp --version
```

### 2. Test basic functionality

Create a test file `test_xray.py`:

```python
def hello_world():
    print("Hello from XRAY test!")

def calculate_sum(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
```

### 3. In your AI assistant, test these commands:

```
Build the index for the current directory. use XRAY tools
```

Expected: Success message with files indexed

```
Find all functions containing "hello". use XRAY tools
```

Expected: Should find `hello_world` function

```
What would break if I change the multiply method? use XRAY tools
```

Expected: Impact analysis showing any dependencies

## Usage Examples

Once configured, use XRAY by adding "use XRAY tools" to your prompts:

```
# Index a codebase
"Index the src/ directory for analysis. use XRAY tools"

# Find symbols
"Find all classes that contain 'User' in their name. use XRAY tools"

# Impact analysis
"What breaks if I change the authenticate method in UserService? use XRAY tools"

# Dependency tracking
"What does the PaymentProcessor class depend on? use XRAY tools"

# Location queries
"What function is defined at line 125 in main.py? use XRAY tools"
```

## Troubleshooting

### uv not found

Make sure uv is in your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.cargo/bin:$PATH"
```

### Permission denied

On macOS/Linux, you might need to make the script executable:

```bash
chmod +x ~/.local/bin/xray-mcp
```

### Python version issues

XRAY requires Python 3.10+. Check your version:

```bash
python --version

# If needed, install Python 3.10+ with uv
uv python install 3.10
```

### MCP connection issues

1. Check XRAY is running: `xray-mcp --test`
2. Verify your MCP config JSON is valid
3. Restart your AI assistant after config changes

## Advanced Configuration

### Custom Database Location

Set the `XRAY_DB_PATH` environment variable:

```bash
export XRAY_DB_PATH="$HOME/.xray/databases"
```

### Debug Mode

Enable debug logging:

```bash
export XRAY_DEBUG=1
```

## What's Next?

1. **Index your first repository**: In your AI assistant, ask it to "Build the index for my project. use XRAY tools"

2. **Explore the tools**:
   - `build_index` - Visual file tree of your repository
   - `find_symbol` - Fuzzy search for functions, classes, and methods
   - `what_breaks` - Find what code depends on a symbol (reverse dependencies)
   - `what_depends` - Find what a symbol depends on (calls and imports)
   
   Note: Results may include matches from comments or strings. The AI assistant will intelligently filter based on context.

3. **Read the documentation**: Check out the [README](README.md) for detailed examples and API reference

## Why XRAY Uses Pure Python

XRAY v0.3.0+ uses a pure Python implementation that requires zero external dependencies:

- **No binaries to install** - No Semgrep, tree-sitter, or language servers needed
- **Works immediately** - Just `pip install` and go
- **Cross-platform** - Works on any system with Python 3.10+
- **High recall approach** - Finds all potential symbols, lets AI filter intelligently
- **Pluggable architecture** - Can optionally add better parsers later if needed

## Benefits of Using uv

- **10-100x faster** than pip for installations
- **No virtual environment hassles** - uv manages everything
- **Reproducible installs** - uv.lock ensures consistency
- **Built-in Python management** - install any Python version
- **Global tool management** - like pipx but faster

Happy coding with XRAY! 🚀