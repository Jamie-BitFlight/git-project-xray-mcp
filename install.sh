#!/bin/bash

# XRAY MCP Server Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/srijanshukla18/xray/main/install.sh | bash

set -e

echo "🚀 Installing XRAY MCP Server..."

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
INSTALL_DIR="$HOME/.xray"
mkdir -p "$INSTALL_DIR"

# Download XRAY
echo "📥 Downloading XRAY..."
if command -v git &> /dev/null; then
    git clone https://github.com/srijanshukla18/xray.git "$INSTALL_DIR" 2>/dev/null || {
        cd "$INSTALL_DIR"
        git pull origin main
    }
else
    echo "❌ Git is required for installation."
    exit 1
fi

# Check for uv and install if not found
if ! command -v uv &> /dev/null; then
    echo "Installing uv (a fast Python package installer and resolver)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for current session
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "uv installed."
else
    echo "uv is already installed."
fi

# Install dependencies using uv
echo "📦 Installing dependencies with uv..."
cd "$INSTALL_DIR"
uv venv xray-venv
source xray-venv/bin/activate
uv pip install -e .

# Create wrapper script
echo "🔧 Creating wrapper script..."
cat > "$HOME/.local/bin/xray-mcp" << 'EOF'
#!/bin/bash
source "$HOME/.xray/xray-venv/bin/activate"
cd "$HOME/.xray"
PYTHONPATH=src python src/xray/mcp_server.py "$@"
EOF

chmod +x "$HOME/.local/bin/xray-mcp"

# Add to PATH if needed
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ XRAY installed successfully!"
echo ""
echo "🎯 Quick Start:"
echo "1. Add this to your MCP config:"
echo '   {"mcpServers": {"xray": {"command": "xray-mcp"}}}'
echo ""
echo "2. Use in prompts:"
echo '   "Analyze this codebase for dependencies. use XRAY tools"'
echo ""
echo "📚 Full documentation:"
echo "   https://github.com/srijanshukla18/xray/blob/main/getting_started.md