# Getting Started with XRAY - Modern Installation with uv

XRAY is a minimal-dependency code intelligence system that enhances AI assistants' understanding of codebases. This guide shows how to install and use XRAY with the modern `uv` package manager.

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

### Option 1: Automated Install (Easiest)

For the quickest setup, use the one-line installer from the `README.md`. This will handle everything for you.

```bash
curl -fsSL https://raw.githubusercontent.com/Jamie-BitFlight/git-project-xray-mcp/main/install.sh | bash
```

### Option 2: Quick Try with uvx (Recommended for Testing)

Run XRAY directly without installation using `uvx`:

```bash
# Clone the repository
git clone https://github.com/Jamie-BitFlight/git-project-xray-mcp.git
cd xray

# Run XRAY directly with uvx
uvx --from . git-project-xray-mcp
```

### Option 3: Install as a Tool (Recommended for Regular Use)

Install XRAY as a persistent tool:

```bash
# Clone and install
git clone https://github.com/Jamie-BitFlight/git-project-xray-mcp.git
cd xray

# Install with uv
uv tool install .

# Now you can run git-project-xray-mcp from anywhere
git-project-xray-mcp
```

### Option 4: Development Installation

For contributing or modifying XRAY:

```bash
# Clone the repository
git clone https://github.com/Jamie-BitFlight/git-project-xray-mcp.git
cd xray

# Create and activate virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
uv pip install -e .

# Test with MCP Inspector - list available tools
npx @modelcontextprotocol/inspector --cli uvx --from . git-project-xray-mcp --method tools/list

# Test with MCP Inspector - call a tool
npx @modelcontextprotocol/inspector --cli uvx --from . git-project-xray-mcp \
  --method tools/call \
  --tool-name explore_repo \
  --tool-arg 'root_path=/tmp' \
  --tool-arg 'max_depth=2'

# Or configure your AI assistant to use the local installation
```

## Configure Your AI Assistant

After installation, configure your AI assistant to use XRAY:

### Using the MCP Config Generator (Recommended)

For easier configuration, use the `mcp-config-generator.py` script located in the XRAY repository. This script can generate the correct JSON configuration for various AI assistants and installation methods.

To use it:

1.  Navigate to the XRAY repository root:
    ```bash
    cd /path/to/xray
    ```
2.  Run the script with your desired tool and installation method. For example, to get the configuration for Claude Desktop with an installed `git-project-xray-mcp` script:
    ```bash
    uv run mcp-config-generator.py claude installed_script
    ```
    Or for VS Code with a local Python installation:
    ```bash
    uv run mcp-config-generator.py vscode local_python
    ```
    The script will print the JSON configuration and instructions on where to add it.

    Available tools: `cursor`, `claude`, `vscode`
    Available methods: `local_python`, `docker`, `source`, `installed_script` (method availability varies by tool)

### Manual Configuration (Advanced)

If you prefer to configure manually, here are examples for common AI assistants:

#### Claude CLI (Claude Code)

For Claude CLI users, simply run:

```bash
claude mcp add xray git-project-xray-mcp -s local
```

Then verify it's connected:

```bash
claude mcp list | grep xray
```

#### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "xray": {
      "command": "uvx",
      "args": ["--from", "/path/to/xray", "git-project-xray-mcp"]
    }
  }
}
```

Or if installed as a tool:

```json
{
  "mcpServers": {
    "xray": {
      "command": "git-project-xray-mcp"
    }
  }
}
```

#### Cursor

Settings → Cursor Settings → MCP → Add new global MCP server:

```json
{
  "mcpServers": {
    "xray": {
      "command": "git-project-xray-mcp"
    }
  }
}
```

## Minimal Dependencies

One of XRAY's best features is its minimal dependency profile. You don't need to install a suite of language servers. XRAY uses:

- **ast-grep**: A single, fast binary for structural code analysis.
- **Python**: For the server and core logic.

This means you can start using XRAY immediately after installation with no complex setup!

## Verify Installation

### 1. Check XRAY is accessible

```bash
# If installed as tool
git-project-xray-mcp --version

# If using uvx
uvx --from /path/to/xray git-project-xray-mcp --version
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
chmod +x ~/.local/bin/git-project-xray-mcp
```

### Python version issues

XRAY requires Python 3.10+. Check your version:

```bash
python --version

# If needed, install Python 3.10+ with uv
uv python install 3.10
```

### MCP connection issues

1. Check XRAY is running: `git-project-xray-mcp --test`
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

## Why XRAY Uses a Minimal Dependency Approach

XRAY is designed for simplicity and ease of use. It relies on:

- **ast-grep**: A powerful and fast single-binary tool for code analysis.
- **Python**: For its robust standard library and ease of scripting.

This approach avoids the complexity of setting up and managing multiple language servers, while still providing accurate, structural code intelligence.

## Benefits of Using uv

- **10-100x faster** than pip for installations
- **No virtual environment hassles** - uv manages everything
- **Reproducible installs** - uv.lock ensures consistency
- **Built-in Python management** - install any Python version
- **Global tool management** - like pipx but faster

Happy coding with XRAY! 🚀