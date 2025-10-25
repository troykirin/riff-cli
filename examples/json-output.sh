#!/usr/bin/env bash

# JSON Output Examples for Riff CLI
# Demonstrates JSON processing with jq

echo "=== JSON Output Examples ==="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Warning: jq is not installed. Install with:"
    echo "  - macOS: brew install jq"
    echo "  - Linux: sudo apt install jq"
    echo ""
    echo "Showing raw JSON output instead..."
    USE_JQ=false
else
    USE_JQ=true
fi

# Example 1: Basic JSON output
echo "1. Basic JSON output:"
if [ "$USE_JQ" = true ]; then
    riff "test" --json --limit 2 | jq '.'
else
    riff "test" --json --limit 2
fi
echo ""

# Example 2: Extract specific fields
if [ "$USE_JQ" = true ]; then
    echo "2. Extract UUIDs using jq:"
    riff "conversation" --json --limit 3 | jq -r '.[].uuid'
    echo ""

    echo "3. Extract conversation names:"
    riff "project" --json --limit 3 | jq -r '.[] | select(.type == "conversation") | .name'
    echo ""

    echo "4. Filter by type:"
    echo "   Conversations only:"
    riff "search" --json --limit 5 | jq '.[] | select(.type == "conversation") | {uuid, name}'
    echo ""

    echo "5. Count results by type:"
    riff "keyword" --json --limit 10 | jq 'group_by(.type) | map({type: .[0].type, count: length})'
    echo ""

    echo "6. Format as table:"
    riff "api" --json --limit 3 | jq -r '.[] | [.uuid, .type, .name // .summary] | @tsv'
    echo ""
fi

# Example 7: Combine with other tools (no jq required)
echo "7. Count total results:"
riff "test" --uuid-only --no-fzf | wc -l
echo ""

# Example 8: Save to file
echo "8. Save JSON to file:"
output_file="/tmp/riff-search-results.json"
riff "conversation" --json --limit 5 > "$output_file"
echo "   Saved to: $output_file"
echo "   Size: $(wc -c < "$output_file") bytes"
echo ""

echo "=== JSON Output Complete ==="
echo ""
if [ "$USE_JQ" = true ]; then
    echo "Try these jq patterns:"
    echo "  - riff 'term' --json | jq '.[] | .uuid'"
    echo "  - riff 'term' --json | jq 'group_by(.type)'"
    echo "  - riff 'term' --json | jq '.[] | select(.type == \"conversation\")'"
else
    echo "Install jq for advanced JSON processing:"
    echo "  - macOS: brew install jq"
    echo "  - Linux: sudo apt install jq"
fi
echo ""
