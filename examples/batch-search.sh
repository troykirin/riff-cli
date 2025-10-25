#!/usr/bin/env bash

# Batch Search Examples for Riff CLI
# Demonstrates processing multiple searches

echo "=== Batch Search Examples ==="
echo ""

# Example 1: Search multiple terms
echo "1. Search multiple terms:"
echo ""
for term in "API" "database" "frontend"; do
    echo "Results for: $term"
    riff "$term" --uuid-only --no-fzf --limit 2
    echo ""
done

# Example 2: Aggregate results
echo "2. Aggregate UUID counts:"
echo ""
for term in "error" "success" "warning"; do
    count=$(riff "$term" --uuid-only --no-fzf | wc -l)
    echo "$term: $count results"
done
echo ""

# Example 3: Export to files
echo "3. Export results to files:"
echo ""
for term in "api" "docs"; do
    output_file="/tmp/riff-${term}-results.json"
    riff "$term" --json --limit 5 > "$output_file"
    echo "Exported: $output_file ($(wc -l < "$output_file") lines)"
done
echo ""

# Example 4: Process UUIDs
echo "4. Process UUIDs in a loop:"
echo ""
echo "Getting first 3 UUIDs for 'conversation'..."
count=0
for uuid in $(riff "conversation" --uuid-only --no-fzf --limit 3); do
    count=$((count + 1))
    echo "  [$count] UUID: $uuid"
done
echo ""

# Example 5: Conditional search
echo "5. Conditional search based on results:"
echo ""
result_count=$(riff "test" --uuid-only --no-fzf | wc -l)
if [ "$result_count" -gt 0 ]; then
    echo "Found $result_count results for 'test'"
    echo "Running detailed search..."
    riff "test" --verbose --no-fzf --limit 2
else
    echo "No results found for 'test'"
fi
echo ""

echo "=== Batch Search Complete ==="
echo ""
echo "Use these patterns for:"
echo "  - Automated reporting"
echo "  - Data aggregation"
echo "  - Batch exports"
echo "  - Conditional workflows"
echo ""
