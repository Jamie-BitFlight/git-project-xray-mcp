#!/usr/bin/env python3
"""
XRAY-Lite MCP Configuration Generator
Generates MCP config for different tools and installation methods.
"""

import json
import sys
import os
from pathlib import Path

CONFIGS = {
    "cursor": {
        "local_python": {
            "mcpServers": {
                "xray-lite": {
                    "command": "python",
                    "args": ["-m", "xray.mcp_server"]
                }
            }
        },
        "docker": {
            "mcpServers": {
                "xray-lite": {
                    "command": "docker", 
                    "args": ["run", "--rm", "-i", "xray-lite"]
                }
            }
        },
        "source": {
            "mcpServers": {
                "xray-lite": {
                    "command": "python",
                    "args": ["run_server.py"],
                    "cwd": str(Path.cwd())
                }
            }
        }
    },
    "claude": {
        "local_python": {
            "mcpServers": {
                "xray-lite": {
                    "command": "python",
                    "args": ["-m", "xray.mcp_server"]
                }
            }
        },
        "docker": {
            "mcpServers": {
                "xray-lite": {
                    "command": "docker",
                    "args": ["run", "--rm", "-i", "xray-lite"]
                }
            }
        }
    },
    "vscode": {
        "local_python": {
            "mcp": {
                "servers": {
                    "xray-lite": {
                        "type": "stdio",
                        "command": "python",
                        "args": ["-m", "xray.mcp_server"]
                    }
                }
            }
        },
        "docker": {
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
    }
}

def print_config(tool, method):
    """Print MCP configuration for specified tool and method."""
    if tool not in CONFIGS:
        print(f"❌ Unknown tool: {tool}")
        print(f"Available tools: {', '.join(CONFIGS.keys())}")
        return False
    
    if method not in CONFIGS[tool]:
        print(f"❌ Unknown method: {method}")
        print(f"Available methods for {tool}: {', '.join(CONFIGS[tool].keys())}")
        return False
    
    config = CONFIGS[tool][method]
    print(f"🔧 {tool.title()} configuration ({method.replace('_', ' ')}):")
    print()
    print(json.dumps(config, indent=2))
    print()
    
    # Add helpful instructions
    if tool == "cursor":
        print("📝 Add this to your Cursor ~/.cursor/mcp.json file")
    elif tool == "claude":
        print("📝 Add this to your Claude desktop config:")
        print("   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json")
        print("   Windows: %APPDATA%\\Claude\\claude_desktop_config.json")
    elif tool == "vscode":
        print("📝 Add this to your VS Code settings.json file")
    
    return True

def main():
    if len(sys.argv) != 3:
        print("XRAY-Lite MCP Configuration Generator")
        print()
        print("Usage: python mcp-config-generator.py <tool> <method>")
        print()
        print("Available tools:")
        for tool in CONFIGS:
            methods = ", ".join(CONFIGS[tool].keys())
            print(f"  {tool}: {methods}")
        print()
        print("Examples:")
        print("  python mcp-config-generator.py cursor local_python")
        print("  python mcp-config-generator.py claude docker")
        print("  python mcp-config-generator.py vscode source")
        return 1
    
    tool = sys.argv[1].lower()
    method = sys.argv[2].lower()
    
    if print_config(tool, method):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())