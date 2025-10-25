# Usage Guide

Comprehensive usage examples for Riff CLI.

## Basic Concepts

Riff CLI searches through Claude conversation exports and JSONL files. It automatically detects the format and provides:
- **Claude Export Format**: Searches `conversations.json`, `projects.json`, `users.json`
- **JSONL Format**: Searches traditional line-delimited JSON files

## Command Syntax

```bash
riff [SEARCH_TERM] [OPTIONS]
```

## Quick Examples

### Basic Search

```bash
# Search for conversations about "authentication"
riff "authentication"

# Search with multiple words
riff "error handling"

# Case-insensitive search
riff "API"  # matches "api", "Api", "API"
```

### Intent-Driven Search

Enable keyword expansion for better results:

```bash
# Expand "claude" to include: assistant, conversation, chat, ai, llm, dialogue
riff "claude discussions" --intent

# Deep recursive expansion (depth 1-5)
riff "find project work" --intent --recursive 5
```

### Output Formats

```bash
# Interactive fuzzy search (default)
riff "search term"

# Direct output (no fzf)
riff "search term" --no-fzf

# UUID only (for scripting)
riff "search term" --uuid-only

# JSON output
riff "search term" --json

# Combined: JSON + UUID only
riff "search term" --json --uuid-only
```

### Custom Search Paths

```bash
# Search specific directory
riff "keyword" --path ~/claude-exports

# Search archived conversations
riff "keyword" --path ~/archive/2024
```

### Format Control

```bash
# Force Claude export format
riff "keyword" --format claude

# Force JSONL format
riff "keyword" --format jsonl

# Auto-detect (default)
riff "keyword" --format auto
```

## Advanced Usage

### Progress Indicators

For large datasets, show progress:

```bash
riff "keyword" --progress
```

Output:
```
⏳ Processing 15/100 files... ⠸
```

### Verbose Mode

Debug and understand what's happening:

```bash
riff "keyword" --verbose
```

Output includes:
- Files found and formats detected
- Keyword expansion results
- Search progress
- Result breakdown by type

### Limiting Results

Control the number of results:

```bash
# Limit to 50 results
riff "keyword" --limit 50

# Combine with other options
riff "keyword" --limit 10 --json
```

## Real-World Examples

### Find Recent Conversations

```bash
# Search for conversations about a specific topic
riff "api integration" --intent

# Find project discussions
riff "linear project" --format claude
```

### Extract UUIDs for Scripting

```bash
# Get all conversation UUIDs matching a term
riff "deployment" --uuid-only --no-fzf > deployment-conversations.txt

# Process UUIDs in a loop
for uuid in $(riff "error" --uuid-only --no-fzf); do
    echo "Processing: $uuid"
    # Your processing logic here
done
```

### Batch Processing

```bash
# Search multiple terms
for term in "api" "database" "frontend"; do
    echo "Results for: $term"
    riff "$term" --json --limit 5
done
```

### Search Specific Types

```bash
# Search only conversations (Claude export)
riff "keyword" --format claude --path ~/.claude/projects

# Search JSONL logs
riff "error" --format jsonl --path ~/logs
```

## Interactive Mode (fzf)

When fzf is available and enabled (default):

**Navigation:**
- **Arrow keys**: Move up/down
- **Enter**: Select and exit
- **Tab**: Select multiple items
- **Ctrl+C**: Cancel

**Preview:**
- Shows context for each result
- Displays UUID, directory, summary, and snippet

**Example:**
```bash
riff "api"
# Opens fzf interface with results
# Use arrow keys to navigate
# Press Enter to select
```

## Environment Variables

### RIFF_SEARCH_PATH

Set default search path:

```bash
export RIFF_SEARCH_PATH="$HOME/.claude/projects"
riff "keyword"  # Searches default path
```

### RIFF_INTENT_SCRIPT

Set custom intent enhancer location:

```bash
export RIFF_INTENT_SCRIPT="$HOME/custom/path/intent_enhancer_simple.py"
riff "keyword" --intent
```

### RIFF_DEBUG

Enable debug output:

```bash
export RIFF_DEBUG=true
riff "keyword"
```

## Output Format Details

### Default (Interactive)

```
UUID: abc123... | DIR: my-project | SUMMARY: API integration work | SNIPPET: Implementing REST...
UUID: def456... | DIR: frontend | SUMMARY: UI components | SNIPPET: Building reusable...
```

### JSON Output

```json
[
  {
    "type": "conversation",
    "uuid": "abc123...",
    "name": "API Integration",
    "created_at": "2024-01-15T10:30:00Z",
    "file": "conversations.json",
    "context": "Working on API integration...",
    "match_text": "API integration REST endpoints..."
  }
]
```

### UUID Only

```
abc123-def456-789...
def456-abc789-123...
```

## Tips & Tricks

### 1. Combine Options for Power

```bash
# Verbose + progress for debugging large searches
riff "keyword" --verbose --progress

# Intent + JSON for automated processing
riff "find issues" --intent --json --limit 20
```

### 2. Use Shell Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
alias riffs='riff --no-fzf'  # Quick search without fzf
alias riffu='riff --uuid-only --no-fzf'  # UUIDs only
alias riffv='riff --verbose'  # Verbose search
```

### 3. Search Patterns

```bash
# Technical terms
riff "GraphQL schema" --intent

# Error investigation
riff "TypeError" --format jsonl

# Project work
riff "implement feature" --intent --recursive 5
```

### 4. Integration with Other Tools

```bash
# Count matches
riff "keyword" --uuid-only --no-fzf | wc -l

# Filter with grep
riff "keyword" --no-fzf | grep "specific-project"

# Process with jq
riff "keyword" --json | jq '.[] | select(.type == "conversation")'
```

## Common Patterns

### Daily Development Workflow

```bash
# Morning: Review yesterday's conversations
riff "yesterday" --intent

# During: Find related discussions
riff "current feature name" --intent

# Evening: Export work summary
riff "today" --json > daily-summary.json
```

### Debugging

```bash
# Find error discussions
riff "error" --format jsonl --verbose

# Get all error UUIDs
riff "exception" --uuid-only --no-fzf
```

### Documentation

```bash
# Find documentation discussions
riff "documentation" --intent

# Export to file
riff "docs" --json > documentation-conversations.json
```

## Troubleshooting

### No results found

1. Check your search path:
   ```bash
   riff "keyword" --verbose
   ```

2. Try different formats:
   ```bash
   riff "keyword" --format claude
   riff "keyword" --format jsonl
   ```

3. Use intent mode:
   ```bash
   riff "keyword" --intent
   ```

### Too many results

```bash
# Limit results
riff "keyword" --limit 10

# Be more specific
riff "specific keyword phrase"
```

### fzf not working

```bash
# Use direct output
riff "keyword" --no-fzf
```

## Next Steps

- Check [INSTALLATION.md](INSTALLATION.md) for setup details
- See [examples/](../examples/) for script examples
- Explore intent-driven search with `--intent` flag
- Integrate with NabiOS (see [integration/NABIÓS.md](integration/NABIÓS.md))

## Command Reference

```
Usage: riff [SEARCH_TERM] [OPTIONS]

Options:
  -p, --path PATH        Search path (default: env or ~/.claude/projects)
  -f, --format FORMAT    Format: jsonl, claude, auto (default: auto)
  -i, --intent          Enable intent-driven search
  -r, --recursive NUM   Recursive enhancement depth (1-5, default: 3)
  -n, --no-fzf         Skip fzf and output directly
  -u, --uuid-only      Output only UUIDs
  -j, --json           Output as JSON
  -v, --verbose        Verbose output with debug info
  -l, --limit NUM      Limit results (default: 1000)
  --progress           Show progress indicators
  -h, --help           Show help message
```
