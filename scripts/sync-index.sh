#!/bin/bash
# Incremental Qdrant Index Sync
# Keeps remote GPU Qdrant in sync with local sessions
# Can be run manually or via cron/LaunchAgent

set -e

# Configuration
QDRANT_URL="${QDRANT_URL:-$(cd "$(dirname "$0")/.." && uv run python -c "from src.riff.search.router import get_best_qdrant_url; print(get_best_qdrant_url())" 2>/dev/null || echo "http://localhost:6333")}"
SESSIONS_DIR="${SESSIONS_DIR:-$HOME/.claude/projects}"
STATE_FILE="$HOME/.local/state/nabi/riff/last-sync.json"
LOG_FILE="$HOME/.local/state/nabi/riff/sync-index.log"

# Ensure state directory exists
mkdir -p "$(dirname "$STATE_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

# Log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting incremental index sync..."
log "Qdrant URL: $QDRANT_URL"
log "Sessions dir: $SESSIONS_DIR"

# Count sessions
TOTAL_SESSIONS=$(find "$SESSIONS_DIR" -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
log "Found $TOTAL_SESSIONS session files"

# Check if this is first sync
if [ ! -f "$STATE_FILE" ]; then
    log "First sync - running full index..."
    LAST_SYNC_TIME=0
else
    LAST_SYNC_TIME=$(jq -r '.last_sync_epoch // 0' "$STATE_FILE" 2>/dev/null || echo "0")
    LAST_SYNC_DATE=$(date -r "$LAST_SYNC_TIME" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
    log "Last sync: $LAST_SYNC_DATE"

    # Find sessions modified since last sync
    NEW_SESSIONS=$(find "$SESSIONS_DIR" -name "*.jsonl" -newermt "@$LAST_SYNC_TIME" 2>/dev/null | wc -l | tr -d ' ')
    log "Sessions modified since last sync: $NEW_SESSIONS"

    if [ "$NEW_SESSIONS" -eq 0 ]; then
        log "No new sessions - skipping sync"
        exit 0
    fi
fi

# Run indexer
log "Running indexer..."
cd "$(dirname "$0")/.."

if uv run python scripts/improved_indexer.py --qdrant-url "$QDRANT_URL" --sessions-dir "$SESSIONS_DIR" >> "$LOG_FILE" 2>&1; then
    # Update state file
    CURRENT_TIME=$(date +%s)
    jq -n \
        --arg url "$QDRANT_URL" \
        --arg dir "$SESSIONS_DIR" \
        --argjson epoch "$CURRENT_TIME" \
        --arg date "$(date -Iseconds)" \
        --argjson total "$TOTAL_SESSIONS" \
        '{
            last_sync_epoch: $epoch,
            last_sync_date: $date,
            qdrant_url: $url,
            sessions_dir: $dir,
            total_sessions: $total
        }' > "$STATE_FILE"

    log "✓ Sync completed successfully"
    log "Indexed $TOTAL_SESSIONS sessions to $QDRANT_URL"
else
    log "✗ Sync failed - check log for details"
    exit 1
fi
