#!/bin/bash

# XRAY MCP Server Installation Script (uv version)
# Usage: curl -fsSL https://raw.githubusercontent.com/srijanshukla18/xray/main/install.sh | bash

set -e

# Check if XRAY is already installed and on the PATH
if command -v xray-mcp &>/dev/null; then
    echo -e "${GREEN}✓${NC} XRAY is already installed."
    # Optionally, ask to reinstall
    read -p "Do you want to reinstall? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "🚀 Installing XRAY MCP Server with uv..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3.10+ is available
if command -v python3.11 &>/dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}❌${NC} Python 3 is not installed."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
    echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"
else
    echo -e "${RED}❌${NC} Python $PYTHON_VERSION found, but 3.10+ is required"
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦${NC} Installing uv..."
    
    # Detect OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        echo "Please install uv on Windows using:"
        echo "  powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\""
        exit 1
    else
        # macOS and Linux
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Add to PATH for current session
        export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
        
        # Verify installation
        if command -v uv &> /dev/null; then
            echo -e "${GREEN}✓${NC} uv installed successfully"
        else
            echo -e "${RED}❌${NC} Failed to install uv"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✓${NC} uv is already installed"
fi

# Determine installation directory
if git rev-parse --is-inside-work-tree &> /dev/null; then
    INSTALL_DIR=$(pwd)
    echo -e "${GREEN}✓${NC} Installing from current Git repository: $INSTALL_DIR"
    SKIP_CLONE=true
else
    INSTALL_DIR="$HOME/.xray"
    echo -e "${YELLOW}📦${NC} Installing to default directory: $INSTALL_DIR"
    SKIP_CLONE=false
fi
mkdir -p "$INSTALL_DIR"

# Clone or update XRAY (only if not installing from current repo)
if [ "$SKIP_CLONE" = false ]; then
    echo -e "${YELLOW}📥${NC} Downloading XRAY..."
    if [ -d "$INSTALL_DIR/.git" ]; then
        cd "$INSTALL_DIR"
        echo -e "${YELLOW}🔄${NC} Updating existing installation..."
        if ! git pull origin main; then
            echo -e "${YELLOW}⚠${NC} Git pull failed. Performing clean installation..."
            cd "$HOME"
            rm -rf "$INSTALL_DIR"
            git clone https://github.com/srijanshukla18/xray.git "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        fi
    elif [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠${NC} Directory exists but is not a git repository. Cleaning up..."
        rm -rf "$INSTALL_DIR"
        git clone https://github.com/srijanshukla18/xray.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    else
        git clone https://github.com/srijanshukla18/xray.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
else
    # If installing from current repo, just change to it for uv tool install
    cd "$INSTALL_DIR"
    # Clean uv cache to ensure local changes are picked up
    echo -e "${YELLOW}🧹${NC} Cleaning uv cache..."
    uv clean
fi

# Install XRAY as a uv tool
echo -e "${YELLOW}🔧${NC} Installing XRAY with uv..."
uv tool install . --force

# Verify installation
if command -v xray-mcp &> /dev/null; then
    echo -e "${GREEN}✓${NC} XRAY installed successfully!"
else
    echo -e "${RED}❌${NC} Installation failed"
    exit 1
fi

# Run verification test
echo -e "${YELLOW}🧪${NC} Running installation test..."
cd "$INSTALL_DIR"
if $PYTHON_CMD test_installation.py; then
    echo -e "${GREEN}✓${NC} All tests passed!"
else
    echo -e "${YELLOW}⚠${NC} Some tests failed, but installation completed"
fi

# Show next steps
echo ""
echo -e "${GREEN}✅ XRAY installed successfully!${NC}"
echo ""
echo "🎯 Quick Start:"
echo "1. Add this to your MCP config:"
echo '   {"mcpServers": {"xray": {"command": "xray-mcp"}}}'
echo ""
echo "2. Use in prompts:"
echo '   "Analyze this codebase for dependencies. use XRAY tools"'
echo ""
echo "📚 Full documentation:"
echo "   https://github.com/srijanshukla18/xray"
echo ""
echo "💡 Tip: You can also run XRAY without installation using:"
echo "   uvx --from $INSTALL_DIR xray-mcp"
