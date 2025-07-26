# Getting Started with XRAY

XRAY is a powerful code intelligence system that enhances AI assistants' understanding of codebases. It provides fast symbol search, impact analysis, dependency tracking, and location-based queries.

## 🚀 Quick Start (30 seconds)

### Option 1: Docker (Recommended)

This is the easiest method as it bundles all dependencies into a single container.

**Prerequisites:** You must have Docker installed and running.

```bash
# Pull and run XRAY
docker run -d --name xray -p 8000:8000 -i xray
```

### Option 2: Python

This method installs XRAY directly into your Python environment.

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

### Option 3: One-Line Install Script (Automated Python Installation)

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
*   **Docker Installation:**
    ```json
    {
      "mcpServers": {
        "xray": {
          "command": "docker",
          "args": ["run", "--rm", "-i", "xray"]
        }
      }
    }
    ```
*   **Development Mode (from source):**
    ```json
    {
      "mcpServers": {
        "xray": {
          "command": "python",
          "args": ["run_server.py"],
          "cwd": "/path/to/your/cloned/xray/directory"
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
*   **Docker Installation:**
    ```json
    {
      "mcpServers": {
        "xray": {
          "command": "docker",
          "args": ["run", "--rm", "-i", "xray"]
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
*   **Docker Installation:**
    ```json
    {
      "mcp": {
        "servers": {
          "xray": {
            "type": "stdio",
            "command": "docker",
            "args": ["run", "--rm", "-i", "xray"]
          }
        }
      }
    }
    ```

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
*   **Docker not running:** Make sure your Docker Desktop application is running.
*   **Permission denied:** You might need to run commands with `sudo` or check file/directory permissions.
*   **Port conflicts:** XRAY uses standard input/output (stdio) by default, so port conflicts are generally not an issue unless you explicitly configure it to use a network port.
