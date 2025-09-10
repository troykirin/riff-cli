# Riff CLI Usage Guide

Comprehensive guide to using the Riff CLI tools for JSONL UUID extraction and fuzzy searching.

## Basic Commands

### Interactive Mode (Default)

```bash
riff data.jsonl
```

This opens an interactive fuzzy search interface where you can:
- Type to filter UUIDs
- Use arrow keys to navigate
- Press Enter to select and copy UUID to clipboard
- Press Esc to exit without selection

### UUID-Only Output

```bash
riff-uuid data.jsonl
# or
riff data.jsonl --uuid-only
```

Extracts and lists all UUIDs from the file, one per line.

### JSON Output

```bash
riff-json data.jsonl
# or
riff data.jsonl --json
```

Outputs structured JSON with UUIDs and associated metadata.

## Advanced Usage

### Content-Based Search

```bash
# Search for entries containing "error"
riff data.jsonl --search "error"

# Case-insensitive search
riff data.jsonl --search "ERROR" --ignore-case
```

### Performance Options

```bash
# Limit number of entries processed
riff data.jsonl --limit 1000

# Use streaming for very large files
riff data.jsonl --stream
```

### Enhanced Version Features

The `riff-enhanced` command includes additional features:

```bash
# Progress indicators for large files
riff-enhanced large-dataset.jsonl

# Enhanced error reporting
riff-enhanced data.jsonl --verbose
```

## File Format Requirements

Riff CLI expects JSONL (JSON Lines) format where each line contains a valid JSON object with a UUID field. Example:

```jsonl
{"id": "123e4567-e89b-12d3-a456-426614174000", "data": "some content"}
{"id": "987fcdeb-51a2-43d1-b789-123456789abc", "data": "more content"}
```

Supported UUID field names:
- `id`
- `uuid` 
- `identifier`
- `guid`

## Shell Integration

The installation script sets up convenient aliases:

```bash
alias riff='~/.local/bin/riff'
alias riff-enhanced='~/.local/bin/riff-enhanced'  
alias riff-simple='~/.local/bin/riff-simple'
alias riff-uuid='riff --uuid-only'
alias riff-json='riff --json'
alias riff-help='riff help'
alias riff-find='riff'
alias riff-search='riff --search'
```

## Common Workflows

### Extract UUIDs for Processing

```bash
# Get all UUIDs and process with xargs
riff-uuid data.jsonl | xargs -I {} echo "Processing: {}"

# Pipe to other commands
riff-uuid data.jsonl | head -5
```

### Interactive Selection

```bash
# Select UUID interactively and use in variable
UUID=$(riff data.jsonl)
echo "Selected: $UUID"

# Use selected UUID in API call
curl -X GET "https://api.example.com/items/$(riff data.jsonl)"
```

### Debugging and Analysis

```bash
# Use simple version for debugging
riff-simple data.jsonl

# Check JSON structure
riff-json data.jsonl | jq '.[0]'

# Count unique UUIDs
riff-uuid data.jsonl | sort | uniq | wc -l
```

## Error Handling

Common issues and solutions:

### File Not Found
```bash
$ riff nonexistent.jsonl
Error: File 'nonexistent.jsonl' not found
```

### Invalid JSON
```bash
$ riff invalid.jsonl
Warning: Skipping invalid JSON on line 5
Error: No valid UUIDs found
```

### Missing Dependencies
```bash
$ riff data.jsonl
Error: fzf not found. Please install fzf first.
```

## Performance Tips

1. **Use limits for exploration**: `riff data.jsonl --limit 100`
2. **Stream large files**: `riff data.jsonl --stream`
3. **Use simple version for scripting**: `riff-simple data.jsonl`
4. **Search before processing**: `riff data.jsonl --search "keyword" --uuid-only`

## Integration Examples

### With Git

```bash
# Find UUIDs in git log
git log --oneline | grep -o '[0-9a-f\-]\{36\}' > uuids.txt
riff uuids.jsonl
```

### With Databases

```bash
# Export database UUIDs to JSONL
psql -d mydb -c "SELECT jsonb_build_object('id', uuid, 'data', description) FROM items" -t | riff /dev/stdin
```

### With APIs

```bash
# Process API responses
curl -s https://api.example.com/items | jq -c '.[]' > response.jsonl
riff response.jsonl
```