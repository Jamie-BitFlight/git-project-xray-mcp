# Getting Started with XRAY

XRAY is a powerful code intelligence system that enhances AI assistants' understanding of codebases. It provides fast symbol search, impact analysis, dependency tracking, and location-based queries.

## 🚀 Quick Start (30 seconds)

### Option 1: Python (Recommended for Local Development)

This method installs XRAY directly into your Python environment and provides direct access to your local filesystem for analyzing codebases.

**Prerequisites:**
*   Python 3.11+
*   Git

```bash
# Clone repository
git clone https://github.com/srijanshukla18/xray.git
cd xray

# Install dependencies (using a virtual environment is recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -e .

# Run server
python run_server.py
```

### Option 2: One-Line Install Script (Automated Python Installation)

For a quick setup, an automated script is available. Use this if you are comfortable running shell scripts directly from the internet.

```bash
curl -fsSL https://raw.githubusercontent.com/srijanshukla18/xray/main/install.sh | bash
```

## 🔌 MCP Client Integration

After installing XRAY, you need to configure your AI assistant (MCP Client) to communicate with the XRAY server. You will typically add a JSON configuration snippet to your client's settings.

You can use the `mcp-config-generator.py` script to help create the correct configuration for your setup:

```bash
# Example: Generate config for Cursor using local Python installation
python mcp-config-generator.py cursor local_python
```

Here are example configuration snippets for common clients:

### Cursor

Go to: `Settings` → `Cursor Settings` → `MCP` → `Add new global MCP server`

*   **Local Python Installation:**
    ```json
    {
      "mcpServers": {
        "xray": {
          "command": "python",
          "args": ["-m", "xray.mcp_server"]
        }
      }
    }
    ```

### Claude Desktop

Add to your Claude Desktop config file (e.g., `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS).

*   **Local Python Installation:**
    ```json
    {
      "mcpServers": {
        "xray": {
          "command": "python",
          "args": ["-m", "xray.mcp_server"]
        }
      }
    }
    ```

### VS Code

Add to your VS Code MCP config file.

*   **Local Python Installation:**
    ```json
    {
      "mcp": {
        "servers": {
          "xray": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "xray.mcp_server"]
          }
        }
      }
    }
    ```

## 🎯 Specifying Target Repository

XRAY tools accept a `path` parameter to specify which repository to analyze. By default, they analyze the current working directory.

```bash
# Examples when using XRAY tools:
build_index(path="/path/to/your/project")
find_symbol(query="UserService", path="/path/to/your/project")
what_breaks(symbol_name="authenticate", path="/path/to/your/project")
```

If you don't specify a path, XRAY will analyze the current directory. When XRAY detects it's analyzing its own codebase, it will show a warning.

## 📁 Database Storage

XRAY stores its databases in your home directory at `~/.xray/databases/`. Each repository gets its own database based on a hash of its path, allowing multiple repositories to be analyzed simultaneously without conflicts.

## 🎯 Usage

Once installed and configured, use XRAY's code intelligence tools by adding `use XRAY tools` to your prompts within your AI assistant.

**Example Prompts:**

*   `Analyze the UserService class and show me what would break if I change the authenticate method. use XRAY tools`
*   `Find all functions that call validate_user and show their dependencies. use XRAY tools`
*   `What symbol is defined at line 42 in auth.py? use XRAY tools`

### Available Tools

*   **`build_index`**: Index your codebase for analysis.
*   **`find_symbol`**: Search for functions/classes by name.
*   **`what_breaks`**: Impact analysis (shows what depends on a symbol).
*   **`what_depends`**: Dependency analysis (shows what a symbol uses).
*   **`get_info`**: Get the symbol at a specific file and line number.

## 🆘 Troubleshooting

*   **Python not found:** Make sure Python 3.11+ is installed and correctly added to your system's PATH.
*   **Docker not running:** This option has been removed. Please use the Python installation method.
*   **Permission denied:** You might need to run commands with `sudo` or check file/directory permissions.
*   **Port conflicts:** XRAY uses standard input/output (stdio) by default, so port conflicts are generally not an issue unless you explicitly configure it to use a network port.