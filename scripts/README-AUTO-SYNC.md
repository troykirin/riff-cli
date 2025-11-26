# Qdrant Auto-Sync: Preventing Stale Indexes

## The Problem

When using a remote Qdrant instance (like WSL GPU), the index can become stale because:

1. **New sessions created** on macOS (`~/.claude/projects`)
2. **Sessions deleted** or modified
3. **Remote Qdrant** doesn't know about these changes
4. **Search returns wrong/missing results** with outdated UUIDs

## The Solution

**Automatic incremental sync** every 6 hours:

```
macOS Sessions → Detect Changes → Index to GPU Qdrant → Track State
```

## Installation

```bash
# Install auto-sync LaunchAgent
cd ~/nabia/tools/riff-cli/scripts
./install-auto-sync.sh
```

This will:
- ✅ Make `sync-index.sh` executable
- ✅ Install LaunchAgent plist to `~/Library/LaunchAgents/`
- ✅ Load the agent (runs every 6 hours)

## How It Works

### 1. State Tracking
Maintains `~/.local/state/nabi/riff/last-sync.json`:
```json
{
  "last_sync_epoch": 1732579200,
  "last_sync_date": "2025-11-25T18:00:00",
  "qdrant_url": "http://wsl.tail4f3a5b.ts.net:6333",
  "sessions_dir": "/Users/tryk/.claude/projects",
  "total_sessions": 4736
}
```

### 2. Incremental Indexing
- **First run**: Indexes all sessions
- **Subsequent runs**: Only indexes sessions modified since last sync
- **Smart detection**: Uses filesystem modification time

### 3. Automatic Schedule
Runs at: **00:00, 06:00, 12:00, 18:00** daily

## Manual Usage

```bash
# Run sync manually
~/nabia/tools/riff-cli/scripts/sync-index.sh

# Check sync status
cat ~/.local/state/nabi/riff/last-sync.json | jq

# View logs
tail -f ~/.local/state/nabi/riff/sync-index.log

# Check LaunchAgent status
launchctl list | grep riff
```

## Configuration

Edit `sync-index.sh` to customize:

```bash
# Use different Qdrant URL
QDRANT_URL="http://other-server:6333" ./sync-index.sh

# Index different directory
SESSIONS_DIR="~/other-sessions" ./sync-index.sh
```

## Uninstallation

```bash
# Stop auto-sync
launchctl unload ~/Library/LaunchAgents/com.nabi.riff.sync-index.plist

# Remove LaunchAgent
rm ~/Library/LaunchAgents/com.nabi.riff.sync-index.plist
```

## Monitoring

### Check Last Sync
```bash
jq -r '"Last sync: \(.last_sync_date) | Total: \(.total_sessions) sessions"' \
    ~/.local/state/nabi/riff/last-sync.json
```

### Watch Live Progress
```bash
tail -f ~/.local/state/nabi/riff/sync-index.log
```

### Verify Qdrant Count
```bash
curl -s http://wsl.tail4f3a5b.ts.net:6333/collections/claude_sessions \
    | jq '.result.points_count'
```

## Troubleshooting

### Sync Not Running
```bash
# Check if LaunchAgent is loaded
launchctl list | grep com.nabi.riff.sync-index

# Check logs for errors
tail -50 ~/.local/state/nabi/riff/sync-index-launchd.log
```

### Force Full Reindex
```bash
# Remove state file to trigger full reindex
rm ~/.local/state/nabi/riff/last-sync.json

# Run sync
~/nabia/tools/riff-cli/scripts/sync-index.sh
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  LaunchAgent (every 6 hours)                │
└────────────────┬────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  sync-index.sh │
        └────────┬───────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
  ┌──────────┐     ┌────────────┐
  │ State    │     │  Indexer   │
  │ Tracker  │     │  (Python)  │
  └──────────┘     └──────┬─────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ GPU Qdrant   │
                   │ (WSL/Remote) │
                   └──────────────┘
```

## Benefits

✅ **No stale indexes** - Sessions automatically stay in sync
✅ **Incremental** - Only indexes new/changed sessions (fast)
✅ **Automatic** - No manual intervention needed
✅ **Monitored** - Logs all activity for debugging
✅ **Configurable** - Easy to customize schedule/targets
✅ **Resilient** - Handles failures gracefully

## See Also

- `improved_indexer.py` - The underlying indexer
- `riff-qdrant-routing.toml` - Endpoint configuration
- `QdrantRouter` - Health-aware endpoint selection
