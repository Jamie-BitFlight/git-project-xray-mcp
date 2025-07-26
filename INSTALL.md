# XRAY-Lite MCP - Fast Code Intelligence for AI Assistants

[![Docker](https://img.shields.io/badge/Docker-Available-blue)](https://hub.docker.com) [![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)

## ✨ What is XRAY-Lite?

XRAY-Lite provides AI assistants with **fast code intelligence** they actually need:

- 🔍 **Fast Symbol Search** - Find functions, classes instantly  
- 💥 **Impact Analysis** - "What breaks if I change this?" (THE KILLER FEATURE)
- 🔗 **Dependency Tracking** - What does this symbol depend on?
- 📍 **Location Queries** - What symbol is at file:line?

Just add `use XRAY tools` to your prompt and get intelligent code analysis.

## 🚀 Quick Start (30 seconds)

### Option 1: Docker (Recommended)

```bash
# Pull and run XRAY-Lite
docker run -d --name xray-lite -p 8000:8000 xray-lite

# Add to your MCP config
```

### Option 2: Python

```bash
# Install XRAY-Lite
pip install xray-lite

# Run server
xray-mcp
```

## 🛠️ Installation

### Requirements

- Python 3.11+ OR Docker
- Cursor, Claude Desktop, or another MCP Client

---

## 📱 Cursor

<details>
<summary><b>Install in Cursor (Click to expand)</b></summary>

Go to: `Settings` → `Cursor Settings` → `MCP` → `Add new global MCP server`

### Local Python Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "python",
      "args": ["-m", "xray.mcp_server"]
    }
  }
}
```

### Docker Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "xray-lite"]
    }
  }
}
```

### Development Mode (from source)

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "python",
      "args": ["run_server.py"],
      "cwd": "/path/to/xray-lite"
    }
  }
}
```

</details>

---

## 🖥️ Claude Desktop

<details>
<summary><b>Install in Claude Desktop (Click to expand)</b></summary>

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Local Python Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "python",
      "args": ["-m", "xray.mcp_server"]
    }
  }
}
```

### Docker Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "xray-lite"]
    }
  }
}
```

</details>

---

## 🌊 Windsurf

<details>
<summary><b>Install in Windsurf (Click to expand)</b></summary>

Add to your Windsurf MCP config file. See [Windsurf MCP docs](https://docs.windsurf.com/windsurf/mcp) for more info.

### Local Python Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "python",
      "args": ["-m", "xray.mcp_server"]
    }
  }
}
```

### Docker Installation

```json
{
  "mcpServers": {
    "xray-lite": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "xray-lite"]
    }
  }
}
```

</details>

---

## 📝 VS Code

<details>
<summary><b>Install in VS Code (Click to expand)</b></summary>

Add to your VS Code MCP config file. See [VS Code MCP docs](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) for more info.

### Local Python Installation

```json
{
  "mcp": {
    "servers": {
      "xray-lite": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "xray.mcp_server"]
      }
    }
  }
}
```

### Docker Installation

```json
{
  "mcp": {
    "servers": {
      "xray-lite": {
        "type": "stdio", 
        "command": "docker",
        "args": ["run", "--rm", "-i", "xray-lite"]
      }
    }
  }
}
```

</details>

---

## 🔧 Manual Installation

### From Source

```bash
# Clone repository
git clone https://github.com/your-username/xray-lite.git
cd xray-lite

# Install dependencies
pip install -e .

# Run server
python src/xray/mcp_server.py
```

### Docker Build

```bash
# Clone and build
git clone https://github.com/your-username/xray-lite.git
cd xray-lite
docker build -t xray-lite .

# Run
docker run --rm -i xray-lite
```

---

## 🎯 Usage

Once installed, use XRAY-Lite in your prompts:

```txt
Analyze the UserService class and show me what would break if I change the authenticate method. use XRAY tools
```

```txt
Find all functions that call `validate_user` and show their dependencies. use XRAY tools  
```

```txt
What symbol is defined at line 42 in auth.py? use XRAY tools
```

### Available Tools

- **`build_index`** - Index your codebase for analysis
- **`find_symbol`** - Search for functions/classes by name
- **`what_breaks`** - Impact analysis (what depends on this symbol)
- **`what_depends`** - Dependency analysis (what this symbol uses)
- **`get_info`** - Get symbol at specific file:line location

---

## 🔍 Example Workflow

1. **Index your codebase**:
   ```txt
   Index this repository for code analysis. use XRAY tools
   ```

2. **Find symbols**:
   ```txt
   Find all functions related to authentication. use XRAY tools
   ```

3. **Analyze impact**:
   ```txt
   What would break if I modify the login function? use XRAY tools
   ```

4. **Check dependencies**:
   ```txt
   What does the UserController depend on? use XRAY tools
   ```

---

## 🆘 Troubleshooting

### Common Issues

**Python not found**: Make sure Python 3.11+ is installed and in PATH
**Docker not running**: Start Docker Desktop
**Permission denied**: Try running with `sudo` or check file permissions
**Port conflicts**: XRAY-Lite uses stdio by default (no ports needed)

### Debug Mode

```bash
# Run with debug output
PYTHONPATH=src python debug_treesitter.py

# Test indexing
PYTHONPATH=src python test_xray.py
```

---

## 🚀 Performance

- **Indexing**: ~1000 files/second
- **Symbol Search**: <5ms
- **Impact Analysis**: <50ms  
- **Memory**: ~100MB for 100k symbols
- **Storage**: ~10MB database for 100k symbols

---

## 🤝 Contributing

XRAY-Lite is open source! Contributions welcome.

1. Fork the repository
2. Create your feature branch
3. Add tests for new functionality  
4. Submit a pull request

---

## 📄 License

MIT License - see LICENSE file for details.