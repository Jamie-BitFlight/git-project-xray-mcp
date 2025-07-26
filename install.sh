#!/bin/bash

# XRAY-Lite MCP Server Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/your-username/xray-lite/main/install.sh | bash

set -e

echo "🚀 Installing XRAY-Lite MCP Server..."

# Check if Python 3.11+ is available
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo "Found Python $PYTHON_VERSION"
else
    echo "❌ Python 3.11+ is required but not found."
    echo "Please install Python 3.11+ and try again."
    exit 1
fi

# Create installation directory
INSTALL_DIR="$HOME/.xray-lite"
mkdir -p "$INSTALL_DIR"

# Download XRAY-Lite
echo "📥 Downloading XRAY-Lite..."
if command -v git &> /dev/null; then
    git clone https://github.com/your-username/xray-lite.git "$INSTALL_DIR" 2>/dev/null || {
        cd "$INSTALL_DIR"
        git pull origin main
    }
else
    echo "❌ Git is required for installation."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
cd "$INSTALL_DIR"
python3 -m venv xray-venv
source xray-venv/bin/activate
pip install -e .

# Create wrapper script
echo "🔧 Creating wrapper script..."
cat > "$HOME/.local/bin/xray-mcp" << 'EOF'
#!/bin/bash
source "$HOME/.xray-lite/xray-venv/bin/activate"
cd "$HOME/.xray-lite"
PYTHONPATH=src python src/xray/mcp_server.py "$@"
EOF

chmod +x "$HOME/.local/bin/xray-mcp"

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ XRAY-Lite installed successfully!"
echo ""
echo "🎯 Quick Start:"
echo "1. Add this to your MCP config:"
echo '   {"mcpServers": {"xray-lite": {"command": "xray-mcp"}}}'
echo ""
echo "2. Use in prompts:"
echo '   "Analyze this codebase for dependencies. use XRAY tools"'
echo ""
echo "📚 Full documentation:"
echo "   https://github.com/your-username/xray-lite/blob/main/INSTALL.md"