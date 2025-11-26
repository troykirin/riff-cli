#!/bin/bash
# Install auto-sync LaunchAgent for Qdrant index
# Prevents stale index by syncing macOS sessions to GPU Qdrant
# Reads schedule from ~/.config/nabi/riff.toml [sync] section

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_DEST="$HOME/Library/LaunchAgents/com.nabi.riff.sync-index.plist"
SYNC_SCRIPT="$SCRIPT_DIR/sync-index.sh"
CONFIG_FILE="$HOME/.config/nabi/riff.toml"

echo "🔧 Installing Riff Auto-Sync LaunchAgent"
echo ""

# Read config values (use Python to parse TOML)
INTERVAL_HOURS=$(cd "$SCRIPT_DIR/.." && uv run python -c "
import sys; sys.path.insert(0, 'src')
from riff.config import get_config
print(get_config().sync_interval_hours)
" 2>/dev/null || echo "6")

echo "📋 Configuration:"
echo "   Config: $CONFIG_FILE"
echo "   Interval: Every $INTERVAL_HOURS hour(s)"
echo ""

# Ensure LaunchAgents directory exists
mkdir -p "$HOME/Library/LaunchAgents"

# Make sync script executable
chmod +x "$SYNC_SCRIPT"
echo "✓ Made sync-index.sh executable"

# Generate plist with schedule based on interval
echo "✓ Generating LaunchAgent plist with $INTERVAL_HOURS hour interval..."

# Calculate schedule intervals
SCHEDULE_HOURS=""
case $INTERVAL_HOURS in
    1)  SCHEDULE_HOURS="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23" ;;
    3)  SCHEDULE_HOURS="0 3 6 9 12 15 18 21" ;;
    6)  SCHEDULE_HOURS="0 6 12 18" ;;
    12) SCHEDULE_HOURS="0 12" ;;
    24) SCHEDULE_HOURS="0" ;;
    *)  SCHEDULE_HOURS="0 6 12 18" ;; # Default to 6 hours
esac

# Generate plist
cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nabi.riff.sync-index</string>

    <key>ProgramArguments</key>
    <array>
        <string>$SYNC_SCRIPT</string>
    </array>

    <key>RunAtLoad</key>
    <false/>

EOF

# Add schedule entries for each hour
for HOUR in $SCHEDULE_HOURS; do
    cat >> "$PLIST_DEST" << EOF
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$HOUR</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

EOF
done

# Add remaining plist config
cat >> "$PLIST_DEST" << EOF
    <key>StandardOutPath</key>
    <string>$HOME/.local/state/nabi/riff/sync-index-launchd.log</string>

    <key>StandardErrorPath</key>
    <string>$HOME/.local/state/nabi/riff/sync-index-launchd.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin</string>
        <key>QDRANT_URL</key>
        <string>http://wsl.tail4f3a5b.ts.net:6333</string>
    </dict>

    <key>ThrottleInterval</key>
    <integer>$((INTERVAL_HOURS * 3600))</integer>

    <key>Nice</key>
    <integer>10</integer>
</dict>
</plist>
EOF

echo "✓ Generated LaunchAgent plist"

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
    echo "Schedule: Every $INTERVAL_HOURS hour(s) at: $(echo $SCHEDULE_HOURS | sed 's/ /:00, /g'):00"
    echo "Log: ~/.local/state/nabi/riff/sync-index.log"
    echo ""
    echo "Commands:"
    echo "  Test run:    $SYNC_SCRIPT"
    echo "  Uninstall:   launchctl unload $PLIST_DEST && rm $PLIST_DEST"
    echo "  Check logs:  tail -f ~/.local/state/nabi/riff/sync-index.log"
    echo ""
    echo "Configuration:"
    echo "  Edit $CONFIG_FILE and change [sync] interval_hours"
    echo "  Valid values: 1, 3, 6, 12, 24 (default: 6)"
    echo "  Then re-run this installer to update the schedule"
else
    echo ""
    echo "❌ Failed to load LaunchAgent"
    echo "Check: launchctl list | grep riff"
    exit 1
fi
