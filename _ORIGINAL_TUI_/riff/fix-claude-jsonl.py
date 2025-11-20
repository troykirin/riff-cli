#!/usr/bin/env python3
"""
Fix Claude JSONL sessions with missing tool_result blocks.

This tool repairs corrupted Claude session files where tool_use blocks
are missing their corresponding tool_result responses.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
import re


def validate_jsonl(filepath):
    """Validate that file is valid JSONL format."""
    try:
        with open(filepath, 'r') as f:
            for i, line in enumerate(f, 1):
                if line.strip():
                    json.loads(line)
        return True, None
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON at line {i}: {e}"
    except Exception as e:
        return False, str(e)


def find_missing_tool_results(messages):
    """Find tool_use blocks without corresponding tool_results."""
    missing = []
    tool_uses = {}
    tool_results = set()

    for i, msg in enumerate(messages):
        if msg.get('role') == 'assistant' and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'tool_use':
                        tool_id = item.get('id')
                        if tool_id:
                            tool_uses[tool_id] = (i, item)

        elif msg.get('role') == 'user' and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'tool_result':
                        tool_id = item.get('tool_use_id')
                        if tool_id:
                            tool_results.add(tool_id)

    # Find tool_uses without results
    for tool_id, (msg_idx, tool_use) in tool_uses.items():
        if tool_id not in tool_results:
            missing.append({
                'tool_id': tool_id,
                'message_index': msg_idx,
                'tool_name': tool_use.get('name', 'unknown'),
                'tool_use': tool_use
            })

    return missing


def create_tool_result(tool_use, error_msg="Tool result was missing - added during repair"):
    """Create a synthetic tool_result for a missing response."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use['id'],
        "content": error_msg
    }


def insert_missing_tool_results(messages, missing_results):
    """Insert synthetic tool_results after their tool_use blocks."""
    # Sort missing results by message index in reverse order
    # so we can insert from the end without affecting indices
    missing_sorted = sorted(missing_results, key=lambda x: x['message_index'], reverse=True)

    for missing in missing_sorted:
        msg_idx = missing['message_index']
        tool_use = missing['tool_use']

        # Create synthetic tool_result message
        tool_result_msg = {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use['id'],
                "content": f"[Repair: Missing result for {tool_use.get('name', 'unknown')} - session continued without this result]"
            }]
        }

        # Insert after the assistant message containing the tool_use
        messages.insert(msg_idx + 1, tool_result_msg)

    return messages


def repair_session(filepath, verbose=False):
    """Repair a Claude session file with missing tool_results."""
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"Error: File {filepath} does not exist")
        return False

    # Validate JSONL
    valid, error = validate_jsonl(filepath)
    if not valid:
        print(f"Error: Invalid JSONL file - {error}")
        return False

    # Read session (JSONL format - last line is the session)
    with open(filepath, 'r') as f:
        lines = f.readlines()
        # The actual session is typically the last non-empty line
        session = None
        for line in reversed(lines):
            if line.strip():
                session = json.loads(line)
                break

        if session is None:
            print("Error: No valid JSON found in file")
            return False

    if 'messages' not in session:
        print("Error: No messages found in session")
        return False

    messages = session['messages']

    # Find missing tool_results
    missing = find_missing_tool_results(messages)

    if not missing:
        print("No missing tool_results found - session appears valid")
        return True

    print(f"Found {len(missing)} missing tool_result(s):")
    for m in missing:
        print(f"  - Message {m['message_index']}: {m['tool_name']} (ID: {m['tool_id']})")

    # Create backup
    backup_path = filepath.with_suffix(f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl')
    import shutil
    shutil.copy2(filepath, backup_path)
    print(f"Created backup: {backup_path}")

    # Insert missing tool_results
    repaired_messages = insert_missing_tool_results(messages.copy(), missing)
    session['messages'] = repaired_messages

    # Write repaired session (preserve JSONL format)
    with open(filepath, 'w') as f:
        # Write each line from original file except the last
        with open(backup_path, 'r') as fb:
            lines = fb.readlines()
            for line in lines[:-1]:
                if line.strip():
                    f.write(line)
        # Write the repaired session as the last line
        f.write(json.dumps(session) + '\n')

    print(f"Repaired session written to: {filepath}")

    # Validate repaired file
    valid, error = validate_jsonl(filepath)
    if not valid:
        print(f"Warning: Repaired file validation failed - {error}")
        print(f"Restoring from backup...")
        backup_path.rename(filepath)
        return False

    # Verify no more missing results
    missing_after = find_missing_tool_results(session['messages'])
    if missing_after:
        print(f"Warning: Still {len(missing_after)} missing tool_results after repair")
        return False

    print("✓ Session successfully repaired!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Fix Claude JSONL sessions with missing tool_results')
    parser.add_argument('session_file', help='Path to the Claude session JSONL file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    success = repair_session(args.session_file, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()