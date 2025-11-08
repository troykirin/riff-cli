# shellcheck shell=bash
# codexr: interactive Codex session picker + resume
# Lists ~/.codex/sessions/*/*/*/rollout-*.jsonl with timestamp, line count, bytes, and full path.
# If fzf is available: interactive picker with preview.
# Fallback: resume the Nth newest (default 1 = newest).

_codexr_list_sessions() {
  # Prints: "<YYYY-MM-DD HH:MM:SS> <LINES> lines <BYTES> bytes  <PATH>"
  # Sorted newest first. Implemented in Python for macOS/GNU portability.
  /opt/homebrew/bin/python3 <<'PY'
import os
import subprocess
import time
from pathlib import Path

sessions_root = Path.home() / '.codex' / 'sessions'
if not sessions_root.exists():
    raise SystemExit(0)

records = []
for path in sessions_root.rglob('rollout-*.jsonl'):
    try:
        stat = path.stat()
    except OSError:
        continue
    records.append((stat.st_mtime, path, stat.st_size))

records.sort(key=lambda item: item[0], reverse=True)

for mtime, path, size in records:
    try:
        completed = subprocess.run(
            ['wc', '-l', str(path)], check=True, capture_output=True, text=True
        )
        lines = int(completed.stdout.strip().split()[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        # Fall back to unknown line count if wc fails
        lines = -1
    stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
    if lines >= 0:
        print(f"{stamp} {lines:8d} lines {size:10d} bytes  {path}")
    else:
        print(f"{stamp}    unknown lines {size:10d} bytes  {path}")
PY
}

_codexr_resume() {
  local session_path="$1"

  # Extract session ID from filename: rollout-YYYY-MM-DDTHH-MM-SS-UUID.jsonl
  local session_id
  session_id=$(/usr/bin/basename "$session_path" .jsonl | /usr/bin/sed 's/^rollout-[0-9T-]*-//')

  if command -v codex >/dev/null 2>&1; then
    echo "Resuming session: $session_id"
    exec codex resume "$session_id"
  elif [ -x "/Users/tryk/.bun/bin/codex" ]; then
    echo "Resuming session: $session_id"
    exec /Users/tryk/.bun/bin/codex resume "$session_id"
  else
    echo "codex CLI not found in PATH."
    echo "Session file is at: $session_path"
    echo "Session ID would be: $session_id"
    return 1
  fi
}

codexr() {
  local nth="${1:-1}"
  local selection path

  if command -v fzf >/dev/null 2>&1; then
    selection=$(_codexr_list_sessions | fzf --ansi --no-sort --reverse --height=20 \
            --prompt="Select Codex session > " \
            --preview 'tail -n 60 "$(echo {} | /usr/bin/awk "{print \$NF}")"' \
            --preview-window=down:50%)
    [[ -z "$selection" ]] && { echo "No selection."; return 1; }
    path=$(/usr/bin/awk '{print $NF}' <<< "$selection")
  else
    path=$(_codexr_list_sessions | /usr/bin/sed -n "${nth}p" | /usr/bin/awk '{print $NF}')
    [[ -z "$path" ]] && { echo "No session found."; return 1; }
    echo "Resuming (#${nth}): $path"
  fi

  _codexr_resume "$path"
}
