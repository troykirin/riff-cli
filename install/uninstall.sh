#!/bin/bash

# Riff CLI Uninstallation Script
# This script removes Riff CLI tools and shell integration

set -e

INSTALL_DIR="$HOME/.local/bin"

echo "🗑️  Uninstalling Riff CLI..."

# Remove installed scripts
echo "📦 Removing scripts..."

for cmd in riff riff-enhanced riff-simple; do
    if [[ -f "$INSTALL_DIR/$cmd" ]]; then
        rm "$INSTALL_DIR/$cmd"
        echo "   ✅ Removed $cmd"
    else
        echo "   ℹ️  $cmd not found, skipping"
    fi
done

# Remove shared Nushell modules
LIB_DIR="$INSTALL_DIR/lib"
if [[ -d "$LIB_DIR" ]]; then
    if [[ -f "$LIB_DIR/riff-core.nu" ]]; then
        rm "$LIB_DIR/riff-core.nu"
        echo "   ✅ Removed shared module riff-core.nu"
    fi
    # Clean up lib directory if empty
    if [[ -z "$(ls -A "$LIB_DIR")" ]]; then
        rmdir "$LIB_DIR"
        echo "   ✅ Removed empty lib directory"
    fi
fi

# Remove shell aliases from .zshrc
echo "🔗 Removing shell integration..."

if [[ -f "$HOME/.zshrc" ]] && grep -q "# Riff CLI aliases" "$HOME/.zshrc"; then
    # Create a temporary file without the Riff CLI section
    awk '
        /^# Riff CLI aliases$/ { skip = 1; next }
        /^# [^R]/ && skip { skip = 0 }
        /^[^#]/ && skip { skip = 0 }
        !skip { print }
    ' "$HOME/.zshrc" > "$HOME/.zshrc.tmp"
    
    mv "$HOME/.zshrc.tmp" "$HOME/.zshrc"
    echo "   ✅ Removed aliases from .zshrc"
else
    echo "   ℹ️  No aliases found in .zshrc"
fi

echo ""
echo "✅ Uninstallation complete!"
echo ""
echo "💡 To fully remove the aliases from your current session:"
echo "   - Restart your terminal"
echo "   - Or run: source ~/.zshrc"