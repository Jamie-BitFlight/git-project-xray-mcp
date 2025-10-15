#!/bin/bash

# XRAY MCP Server Uninstallation Script
# Usage: bash uninstall.sh

set -e

echo "🗑️ Uninstalling XRAY MCP Server..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if uv is installed
if ! command -v uv &>/dev/null; then
	echo -e "${RED}❌${NC} uv is not installed. Uninstallation requires uv."
	echo "Please install uv (https://github.com/astral-sh/uv) and try again."
	exit 1
fi

# Uninstall the git-project-xray-mcp tool
echo -e "${YELLOW}🔧${NC} Uninstalling git-project-xray-mcp tool..."
if uv tool uninstall git-project-xray-mcp; then
	echo -e "${GREEN}✓${NC} git-project-xray-mcp tool uninstalled successfully."
else
	echo -e "${YELLOW}⚠${NC} Could not uninstall git-project-xray-mcp tool. It might not be installed."
fi

# Remove the installation directory
INSTALL_DIR="$HOME/.xray"
if [ -d "$INSTALL_DIR" ]; then
	echo -e "${YELLOW}🗑️${NC} Removing installation directory: $INSTALL_DIR"
	rm -rf "$INSTALL_DIR"
	echo -e "${GREEN}✓${NC} Installation directory removed."
fi

# Verify uninstallation
if ! command -v git-project-xray-mcp &>/dev/null; then
	echo -e "${GREEN}✅ Uninstallation complete!${NC}"
else
	echo -e "${RED}❌ Uninstallation failed.${NC} git-project-xray-mcp is still on the PATH."
	echo "This might be due to your shell caching the command. Please restart your shell."
fi
