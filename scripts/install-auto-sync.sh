#!/bin/bash
# Install auto-sync LaunchAgent for Qdrant index
# Prevents stale index by syncing macOS sessions to GPU Qdrant every 6 hours

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.nabi.riff.sync-index.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.nabi.riff.sync-index.plist"
SYNC_SCRIPT="$SCRIPT_DIR/sync-index.sh"

echo "🔧 Installing Riff Auto-Sync LaunchAgent"
echo ""

# Ensure LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Make sync script executable
chmod +x "$SYNC_SCRIPT"
echo "✓ Made sync-index.sh executable"

# Copy plist
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✓ Copied LaunchAgent plist to $PLIST_DEST"

# Unload if already loaded
if launchctl list | grep -q com.nabi.riff.sync-index; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✓ Unloaded existing LaunchAgent"
fi

# Load the LaunchAgent
launchctl load "$PLIST_DEST"
echo "✓ Loaded LaunchAgent"

# Verify
if launchctl list | grep -q com.nabi.riff.sync-index; then
    echo ""
    echo "✅ Auto-sync installed successfully!"
    echo ""
    echo "Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00)"
    echo "Log: ~/.local/state/nabi/riff/sync-index.log"
    echo ""
    echo "Commands:"
    echo "  Test run:    $SYNC_SCRIPT"
    echo "  Uninstall:   launchctl unload $PLIST_DEST"
    echo "  Check logs:  tail -f ~/.local/state/nabi/riff/sync-index.log"
else
    echo ""
    echo "❌ Failed to load LaunchAgent"
    echo "Check: launchctl list | grep riff"
    exit 1
fi
