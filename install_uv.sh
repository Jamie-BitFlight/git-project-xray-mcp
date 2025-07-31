#!/bin/bash

# XRAY MCP Server Installation Script (uv version)
# Usage: curl -fsSL https://raw.githubusercontent.com/srijanshukla18/xray/main/install_uv.sh | bash

set -e

echo "🚀 Installing XRAY MCP Server with uv..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3.11+ is available
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"
    else
        echo -e "${YELLOW}⚠${NC} Python $PYTHON_VERSION found, but 3.11+ is recommended"
    fi
else
    echo -e "${RED}❌${NC} Python 3.11+ is required but not found."
    echo "Please install Python 3.11+ and try again."
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
        export PATH="$HOME/.cargo/bin:$PATH"
        
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

# Create installation directory
INSTALL_DIR="$HOME/.xray"
mkdir -p "$INSTALL_DIR"

# Clone or update XRAY
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
if python test_installation.py; then
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