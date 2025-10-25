#!/usr/bin/env bash

# Basic Search Examples for Riff CLI
# Demonstrates common search patterns

echo "=== Basic Riff CLI Search Examples ==="
echo ""

# Example 1: Simple search
echo "1. Simple search for 'API':"
echo "   $ riff 'API'"
riff 'API' --no-fzf --limit 3
echo ""

# Example 2: Multi-word search
echo "2. Multi-word search for 'error handling':"
echo "   $ riff 'error handling'"
riff 'error handling' --no-fzf --limit 3
echo ""

# Example 3: Intent-driven search
echo "3. Intent-driven search (keyword expansion):"
echo "   $ riff 'find project work' --intent"
riff 'find project work' --intent --no-fzf --limit 3
echo ""

# Example 4: UUID only output
echo "4. UUID only output for scripting:"
echo "   $ riff 'conversation' --uuid-only --no-fzf"
riff 'conversation' --uuid-only --no-fzf --limit 3
echo ""

# Example 5: JSON output
echo "5. JSON output for processing:"
echo "   $ riff 'search' --json --limit 2"
riff 'search' --json --limit 2
echo ""

# Example 6: Custom path
echo "6. Search custom path:"
echo "   $ riff 'keyword' --path ~/.claude/projects"
echo "   (Not executed - requires custom path)"
echo ""

# Example 7: Verbose mode
echo "7. Verbose mode for debugging:"
echo "   $ riff 'test' --verbose --limit 1"
riff 'test' --verbose --limit 1
echo ""

echo "=== Examples Complete ==="
echo ""
echo "Try these yourself:"
echo "  - riff 'your search term'"
echo "  - riff 'keyword' --intent"
echo "  - riff 'term' --json"
echo ""
