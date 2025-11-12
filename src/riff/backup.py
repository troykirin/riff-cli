# Copyright 2024 NabiaTech
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Safe backup system for conversation files using XDG directories

This module provides automated backup functionality that:
  - Stores backups in ~/.local/share/nabi/riff/backups/ (XDG data directory)
  - Creates timestamped backup files with session UUIDs
  - Maintains a hot-reloadable index in ~/.local/state/nabi/riff/
  - Prevents data loss by backing up before modifications
  - Allows users to restore previous versions easily
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import json
import shutil
import os


def get_backup_metadata_path(config) -> Path:
    """Get path to hot-reloadable backup metadata index"""
    state_dir = config.paths.get("state", Path.home() / ".local/state/nabi/riff")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "backups-index.json"


def load_backup_index(config) -> Dict[str, Any]:
    """Load the backup index (creates if missing)"""
    index_path = get_backup_metadata_path(config)
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"backups": [], "last_updated": None}
    return {"backups": [], "last_updated": None}


def save_backup_index(config, index: Dict[str, Any]) -> None:
    """Save the backup index (hot-reloadable)"""
    index["last_updated"] = datetime.now().isoformat()
    index_path = get_backup_metadata_path(config)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def create_backup(
    original_file: Path,
    config,
    reason: str = "fix"
) -> Optional[Path]:
    """Create a timestamped backup of a conversation file

    Args:
        original_file: Path to the file to back up
        config: RiffConfig instance
        reason: Reason for backup (e.g., "fix", "scan", "manual")

    Returns:
        Path to the backup file, or None if backup failed

    Creates backups in:
        ~/.local/share/nabi/riff/backups/
        with naming pattern: YYYYMMDDTHHMMSS-{uuid}-{reason}.jsonl
    """
    if not original_file.exists():
        print(f"[yellow]Warning: File not found, skipping backup: {original_file}[/yellow]")
        return None

    # Get backup directory from config
    backups_dir = config.paths.get("backups", Path.home() / ".local/share/nabi/riff/backups")
    backups_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    session_uuid = original_file.stem  # Filename without extension
    backup_filename = f"{timestamp}-{session_uuid}-{reason}.jsonl"
    backup_path = backups_dir / backup_filename

    try:
        # Copy file to backup location
        shutil.copy2(original_file, backup_path)

        # Update backup index (hot-reloadable in state directory)
        index = load_backup_index(config)
        index["backups"].append({
            "filename": backup_filename,
            "original_path": str(original_file),
            "created_at": timestamp,
            "reason": reason,
            "session_uuid": session_uuid,
            "size_bytes": backup_path.stat().st_size
        })
        save_backup_index(config, index)

        print(f"[green]✓[/green] Backed up to: {backup_path.relative_to(Path.home())}")
        return backup_path

    except Exception as e:
        print(f"[red]Error: Failed to create backup: {e}[/red]")
        return None


def list_backups(config) -> Dict[str, list]:
    """List all available backups grouped by session UUID"""
    index = load_backup_index(config)
    backups_by_session = {}

    for backup in index.get("backups", []):
        uuid = backup.get("session_uuid", "unknown")
        if uuid not in backups_by_session:
            backups_by_session[uuid] = []
        backups_by_session[uuid].append(backup)

    # Sort each session's backups by creation time (newest first)
    for uuid in backups_by_session:
        backups_by_session[uuid].sort(
            key=lambda b: b.get("created_at", ""),
            reverse=True
        )

    return backups_by_session


def get_backup_path(config, backup_filename: str) -> Optional[Path]:
    """Get full path to a specific backup file"""
    backups_dir = config.paths.get("backups", Path.home() / ".local/share/nabi/riff/backups")
    backup_path = backups_dir / backup_filename

    if backup_path.exists() and backup_path.is_file():
        return backup_path
    return None


def restore_backup(config, backup_filename: str, restore_path: Optional[Path] = None) -> Optional[Path]:
    """Restore a backup to its original location or specified path

    Args:
        config: RiffConfig instance
        backup_filename: Filename of backup to restore
        restore_path: Optional custom path to restore to

    Returns:
        Path where file was restored, or None if restore failed
    """
    backup_path = get_backup_path(config, backup_filename)

    if not backup_path:
        print(f"[red]Error: Backup not found: {backup_filename}[/red]")
        return None

    # Determine restore location
    if restore_path is None:
        # Find original path from index
        index = load_backup_index(config)
        backup_info = None
        for b in index.get("backups", []):
            if b.get("filename") == backup_filename:
                backup_info = b
                break

        if backup_info and "original_path" in backup_info:
            restore_path = Path(backup_info["original_path"])
        else:
            print(f"[yellow]Warning: Original path unknown, specify restore_path[/yellow]")
            return None

    restore_path = Path(restore_path).expanduser()

    try:
        # Backup the current file before overwriting (safety net)
        if restore_path.exists():
            safety_backup_path = restore_path.with_suffix(restore_path.suffix + ".safety-backup")
            shutil.copy2(restore_path, safety_backup_path)
            print(f"[dim]Safety backup created: {safety_backup_path.relative_to(Path.home())}[/dim]")

        # Restore from backup
        shutil.copy2(backup_path, restore_path)
        print(f"[green]✓[/green] Restored from backup to: {restore_path.relative_to(Path.home())}")
        return restore_path

    except Exception as e:
        print(f"[red]Error: Failed to restore backup: {e}[/red]")
        return None


def cleanup_old_backups(config, keep_count: int = 10, session_uuid: Optional[str] = None) -> int:
    """Clean up old backups, keeping only the most recent N per session

    Args:
        config: RiffConfig instance
        keep_count: Number of recent backups to keep per session
        session_uuid: Optional - only clean backups for specific session

    Returns:
        Number of backups deleted
    """
    index = load_backup_index(config)
    backups_by_session = {}

    # Group backups by session
    for backup in index.get("backups", []):
        uuid = backup.get("session_uuid", "unknown")
        if session_uuid is None or uuid == session_uuid:
            if uuid not in backups_by_session:
                backups_by_session[uuid] = []
            backups_by_session[uuid].append(backup)

    # Sort by creation time and mark old ones for deletion
    deleted_count = 0
    backups_dir = config.paths.get("backups", Path.home() / ".local/share/nabi/riff/backups")
    backups_to_keep = []

    for uuid, backups in backups_by_session.items():
        backups.sort(key=lambda b: b.get("created_at", ""), reverse=True)

        for i, backup in enumerate(backups):
            if i < keep_count:
                # Keep this one
                backups_to_keep.append(backup)
            else:
                # Delete this one
                backup_path = backups_dir / backup.get("filename", "")
                if backup_path.exists():
                    try:
                        backup_path.unlink()
                        deleted_count += 1
                        print(f"[dim]Deleted old backup: {backup.get('filename')}[/dim]")
                    except Exception as e:
                        print(f"[yellow]Warning: Could not delete {backup.get('filename')}: {e}[/yellow]")

    # Update index with only kept backups
    index["backups"] = backups_to_keep
    save_backup_index(config, index)

    return deleted_count
