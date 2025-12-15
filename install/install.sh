#!/bin/bash

# Riff CLI Installation Script
# This script installs the Riff CLI tools and sets up shell integration

set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_ROOT/src"
VENV_DIR="$HOME/.cache/nabi/venvs/riff-cli"

echo "🚀 Installing Riff CLI..."

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Check dependencies
echo "📋 Checking dependencies..."

if ! command -v nu >/dev/null 2>&1; then
    echo "❌ Error: nushell (nu) is not installed."
    echo "   Please install nushell first: https://www.nushell.sh/book/installation.html"
    exit 1
fi

if ! command -v fzf >/dev/null 2>&1; then
    echo "❌ Error: fzf is not installed."
    echo "   Please install fzf first: https://github.com/junegunn/fzf#installation"
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "❌ Error: uv is not installed."
    echo "   Please install uv first: https://github.com/astral-sh/uv"
    exit 1
fi

echo "✅ Dependencies found: nushell, fzf, and uv"

# Set up Python virtual environment with uv
echo "🐍 Setting up Python virtual environment..."
if [[ -d "$VENV_DIR" ]]; then
    echo "   ℹ️  Using existing venv at $VENV_DIR"
else
    echo "   📦 Creating venv at $VENV_DIR"
    mkdir -p "$(dirname "$VENV_DIR")"
    uv venv "$VENV_DIR"
fi

# Install Python package into venv
echo "📦 Installing Python package..."
cd "$PROJECT_ROOT"
uv pip install --python "$VENV_DIR/bin/python" -e .
echo "   ✅ Python package installed"

# Copy scripts to install directory
echo "📦 Installing scripts..."

for script in riff.nu riff-enhanced.nu riff-simple.nu; do
    if [[ -f "$SRC_DIR/$script" ]]; then
        cp "$SRC_DIR/$script" "$INSTALL_DIR/${script%.nu}"
        chmod +x "$INSTALL_DIR/${script%.nu}"
        echo "   ✅ Installed $script as ${script%.nu}"
    else
        echo "   ⚠️  Warning: $script not found, skipping"
    fi
done

# Install shared Nushell modules
echo "📚 Installing shared Nushell modules..."
LIB_DIR="$INSTALL_DIR/lib"
mkdir -p "$LIB_DIR"
if [[ -f "$SRC_DIR/lib/riff-core.nu" ]]; then
    cp "$SRC_DIR/lib/riff-core.nu" "$LIB_DIR/"
    echo "   ✅ riff-core.nu installed to $LIB_DIR"
else
    echo "   ⚠️  Warning: riff-core.nu not found, shared module not installed"
fi

# Set up shell aliases
echo "🔗 Setting up shell integration..."

if [[ -f "$SCRIPT_DIR/zsh-aliases.sh" ]]; then
    # Check if aliases are already in .zshrc
    if grep -q "# Riff CLI aliases" "$HOME/.zshrc" 2>/dev/null; then
        echo "   ℹ️  Aliases already present in .zshrc"
    else
        echo "" >> "$HOME/.zshrc"
        echo "# Riff CLI aliases" >> "$HOME/.zshrc"
        cat "$SCRIPT_DIR/zsh-aliases.sh" >> "$HOME/.zshrc"
        echo "   ✅ Added aliases to .zshrc"
    fi
else
    echo "   ⚠️  Warning: zsh-aliases.sh not found, skipping shell integration"
fi

# Verify installation
echo "🔍 Verifying installation..."

for cmd in riff riff-enhanced riff-simple; do
    if [[ -f "$INSTALL_DIR/$cmd" ]]; then
        echo "   ✅ $cmd installed successfully"
    else
        echo "   ❌ $cmd installation failed"
    fi
done

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📖 Usage:"
echo "   riff                    # Interactive JSONL UUID extraction"
echo "   riff-enhanced           # Enhanced version with progress indicators"
echo "   riff-simple             # Simple version for testing"
echo ""
echo "💡 Shell aliases available:"
echo "   riff-uuid               # Extract UUIDs only"
echo "   riff-json               # Output in JSON format"
echo "   riff-help               # Show help"
echo ""
echo "🔄 To use the new aliases, either:"
echo "   - Restart your terminal"
echo "   - Run: source ~/.zshrc"