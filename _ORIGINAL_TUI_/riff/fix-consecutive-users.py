#!/usr/bin/env python3
"""
Fix Claude JSONL sessions with consecutive user messages (missing assistant responses).

This tool repairs corrupted Claude session files where multiple user messages
appear consecutively without intervening assistant responses.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
import shutil


def find_consecutive_users(filepath):
    """Find locations of consecutive user messages."""
    consecutive_groups = []
    current_group = []

    with open(filepath, 'r') as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue

            msg = json.loads(line)
            msg_type = msg.get('type')

            if msg_type == 'user':
                current_group.append(i)
            else:
                if len(current_group) >= 3:
                    consecutive_groups.append(current_group.copy())
                current_group = []

    # Check if file ends with consecutive users
    if len(current_group) >= 3:
        consecutive_groups.append(current_group.copy())

    return consecutive_groups


def repair_consecutive_users(filepath, dry_run=False, verbose=False):
    """Insert placeholder assistant responses between consecutive user messages."""
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"Error: File {filepath} does not exist")
        return False

    # Find problematic sections
    groups = find_consecutive_users(filepath)

    if not groups:
        print("No consecutive user messages found - session appears valid")
        return True

    print(f"Found {len(groups)} groups of consecutive user messages:")
    for group in groups:
        print(f"  - Lines {group[0]}-{group[-1]} ({len(group)} consecutive user messages)")

    if dry_run:
        print("\n[DRY RUN] Would insert assistant responses after these user messages")
        return True

    # Create backup
    backup_path = filepath.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl')
    shutil.copy2(filepath, backup_path)
    print(f"\nCreated backup: {backup_path}")

    # Read all messages
    messages = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))

    # Insert assistant responses
    insertions = []
    for group in groups:
        # Skip the first user message in each group, insert after the others
        for line_num in group[1:]:
            # Line numbers are 1-based, array is 0-based
            insert_after = line_num - 1
            insertions.append(insert_after)

    # Sort insertions in reverse to maintain indices
    insertions.sort(reverse=True)

    for idx in insertions:
        # Create a placeholder assistant response
        assistant_msg = {
            "type": "assistant",
            "userType": "external",
            "subtype": None,
            "content": None,  # Minimal placeholder
            "sessionId": messages[idx].get("sessionId"),
            "timestamp": messages[idx].get("timestamp"),
            "isMeta": False,
            "level": messages[idx].get("level"),
            "cwd": messages[idx].get("cwd"),
            "gitBranch": messages[idx].get("gitBranch"),
            "version": messages[idx].get("version"),
            "uuid": f"repair-{idx}",
            "parentUuid": messages[idx].get("uuid")
        }

        if verbose:
            print(f"Inserting assistant response after line {idx + 1}")

        messages.insert(idx + 1, assistant_msg)

    # Write repaired session
    with open(filepath, 'w') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')

    print(f"\n✓ Repaired session written to: {filepath}")
    print(f"  Inserted {len(insertions)} assistant placeholder messages")

    # Verify repair
    remaining_groups = find_consecutive_users(filepath)
    if remaining_groups:
        print(f"\nWarning: Still {len(remaining_groups)} groups of consecutive users after repair")
        return False

    print("\n✓ Session successfully repaired - no more consecutive user messages!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Fix Claude JSONL sessions with consecutive user messages')
    parser.add_argument('session_file', help='Path to the Claude session JSONL file')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    success = repair_consecutive_users(args.session_file, args.dry_run, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()