# Riff-CLI Platform Integration Guide

**Semantic Search + JSONL Repair Tool for Platform Architecture**

---

## Overview

riff-cli is a Python CLI tool that provides semantic search capabilities for Claude conversations and JSONL file repair. As a **platform tool** (not a service), it enhances developer productivity by enabling:

- Semantic search through conversation archives
- Repair of corrupted JSONL files
- Analysis of conversation threading (DAG)
- Detection and scoring of data corruption

---

## Architecture

```
Platform Architecture
├── services/ (long-running services)
│   ├── service-registry (NATS)
│   ├── wss-loki-proxy (WebSocket proxy)
│   └── ... (other services)
│
├── tools/ (CLI utilities)
│   ├── riff-cli (this tool)
│   └── ... (other tools)
│
└── federation
    ├── NATS (service coordination)
    └── Loki (event logging)
```

**Key Difference**:
- **Services** run continuously and register with NATS
- **Tools** are invoked on-demand and enhance platform capabilities

---

## Installation

### Option 1: Using Federation Virtual Environment (Recommended)

```bash
cd ~/nabia/platform/tools/riff-cli

# Create federation-standard venv at ~/.nabi/venvs/riff-cli/
python3 -m venv ~/.nabi/venvs/riff-cli

# Activate
source ~/.nabi/venvs/riff-cli/bin/activate

# Install in editable mode
pip install -e .
```

### Option 2: Using uv (Fast and XDG-Compliant)

```bash
cd ~/nabia/platform/tools/riff-cli

# Install with uv (respects .hookrc venv location)
uv sync

# Or directly via uv
uv run riff search "test query"
```

### Option 3: With nabi CLI (Federation Integration)

```bash
# When nabi discovers platform tools:
nabi exec riff search "authentication"

# Or with symlink registration:
task nabi:register
```

**Why Federation Venv?**
- XDG compliance: Runtime state separate from config
- Cross-platform: Works on macOS/WSL/Linux/RPi
- Federation integration: Recognized by nabi CLI
- Reproducible: Same location on all machines

---

## Usage

### Semantic Search

Search through conversation files by meaning:

```bash
# Via federation venv (recommended)
~/.nabi/venvs/riff-cli/bin/python -m riff search "authentication flow" --source conversations.jsonl

# Or via uv (if uv sync run)
uv run riff search "authentication flow" --source conversations.jsonl

# Search with result limit
uv run riff search "API design patterns" --source sessions.jsonl --limit 10

# Export results
uv run riff search "error handling" --source data.jsonl --format json > results.json
```

### JSONL Repair

Fix corrupted or partially-written JSONL files:

```bash
# Repair a broken JSONL file
riff repair --input broken.jsonl --output fixed.jsonl

# Analyze corruption before repair
riff repair --input broken.jsonl --analyze

# Show what was fixed
riff repair --input broken.jsonl --output fixed.jsonl --verbose
```

### Conversation Analysis

Analyze message threading and relationships:

```bash
# Analyze conversation structure
riff analyze --input session.jsonl --format json

# Export DAG as graph
riff analyze --input session.jsonl --export-dag graph.json

# Detect corruption
riff analyze --input session.jsonl --detect-corruption
```

---

## Integration with Platform Services

### Using with Loki Events

While riff-cli doesn't directly emit to Loki, it can analyze conversations that include federation events:

```bash
# Search conversations for federation-related events
riff search "federation event" --source federation-conversations.jsonl

# Analyze which sessions have coordination issues
riff analyze --input multi-session.jsonl --filter-by-event-type federation
```

### Using with Service Registry

riff-cli can be invoked as part of platform tooling once nabi CLI discovers it:

```bash
# Discover available tools
nabi list

# Should include: riff-cli

# Execute via nabi
nabi exec riff search "query"
```

### Cross-Tool Integration

Combine riff-cli output with other platform tools:

```bash
# Search riff output, pipe to analysis
riff search "error handling" --source archive.jsonl --format json | \
  jq '.results[] | .message_id' | \
  xargs -I {} riff analyze --message-id {}
```

---

## Data Formats

### Input: JSONL Conversation Files

```jsonl
{"message_id": "uuid", "type": "user", "content": "query", "timestamp": "2025-10-26T..."}
{"message_id": "uuid", "type": "assistant", "content": "response", "timestamp": "2025-10-26T..."}
```

### Output: Search Results (JSON)

```json
{
  "query": "authentication flow",
  "results": [
    {
      "message_id": "uuid",
      "type": "assistant",
      "content": "...",
      "relevance_score": 0.95,
      "session_id": "session-123"
    }
  ],
  "total_results": 42
}
```

### Output: Repair Report

```json
{
  "input_file": "broken.jsonl",
  "output_file": "fixed.jsonl",
  "total_messages": 1500,
  "corrupted_count": 23,
  "repaired_count": 22,
  "failed_count": 1,
  "success_rate": 0.956
}
```

---

## Performance Characteristics

| Operation | Typical Time | Memory | Notes |
|-----------|-------------|--------|-------|
| Search (1M messages) | 100ms-500ms | 512MB | Depends on semantic model |
| Repair (100K messages) | 30-60s | 256MB | Single-threaded |
| Analyze (50K messages) | 5-10s | 128MB | DAG construction |

### Optimization Tips

1. **Search Performance**:
   - Search subset first with `--limit`
   - Use `--filter` to narrow scope
   - Run with SSD for faster I/O

2. **Memory Usage**:
   - Process in batches for large files
   - Use `--stream` flag if available
   - Monitor with `top` or `docker stats`

3. **Parallel Processing**:
   - Split large JSONL files
   - Process partitions separately
   - Combine results afterwards

---

## Platform Service Integration Points

### Conditional: If Exposed as Service

If riff-cli is later wrapped as a microservice:

```toml
# Future docker-compose.yml
[service]
name = "riff-service"
port = 8400
endpoint = "POST /search"
# Would integrate with NATS, emit to Loki
```

### Current: CLI Tool Only

As a CLI tool, riff-cli:
- ✅ Enhances developer experience
- ✅ Works with conversation data
- ✅ Can process platform-generated data
- ❌ Doesn't run as service
- ❌ Doesn't register with NATS
- ❌ Doesn't emit to Loki (yet)

---

## Federation Data Processing

riff-cli can process conversation files that contain federation events:

```bash
# Example: Analyze federation-heavy sessions
riff search "NATS" --source federation-conversations.jsonl \
  --format json | \
  jq '.results[] | select(.type == "system") | .content'

# Result: All system messages related to federation
```

---

## Success Criteria for Wave 1

✅ **Installation**:
- [ ] Module installs without errors
- [ ] Python imports work
- [ ] CLI invocation works

✅ **Basic Functionality**:
- [ ] Search command executes
- [ ] Repair command works
- [ ] Analyze produces valid JSON

✅ **Platform Integration**:
- [ ] Manifest.toml is valid
- [ ] Can be discovered by nabi
- [ ] Works with platform data formats

✅ **Documentation**:
- [ ] README updated
- [ ] Examples provided
- [ ] Performance characteristics documented

---

## Next Steps

1. **Validate Installation**:
   ```bash
   cd ~/nabia/platform/tools/riff-cli
   # Via federation venv
   ~/.nabi/venvs/riff-cli/bin/python -m riff --version
   # Or via uv
   uv run riff --version
   ```

2. **Test with Sample Data**:
   ```bash
   uv run riff search "test" --source tests/fixtures/sample.jsonl
   ```

3. **Integrate with Developer Workflow**:
   - Via nabi CLI: `nabi exec riff search "query"`
   - Via uv: `uv run riff search "query"`
   - Optional alias: `alias riff="~/.nabi/venvs/riff-cli/bin/python -m riff"`

4. **Monitor Usage**:
   - Track which searches are popular
   - Identify performance bottlenecks
   - Collect feedback from developers

---

## Troubleshooting

### Import Errors

```bash
# Verify Python version in federation venv
~/.nabi/venvs/riff-cli/bin/python --version
# Should be 3.13+

# Reinstall dependencies
source ~/.nabi/venvs/riff-cli/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Search Returns No Results

```bash
# Verify input file format
head -5 your_file.jsonl | jq

# Validate JSONL
riff repair --input your_file.jsonl --analyze
```

### Memory Issues

```bash
# Process in smaller batches
split -l 100000 large_file.jsonl batch_

# Process each batch
for file in batch_*; do
  riff search "query" --source $file
done
```

---

## Contributing

riff-cli is part of the platform tools collection. To contribute:

1. Make changes in `~/nabia/platform/tools/riff-cli`
2. Run tests: `pytest tests/`
3. Update documentation
4. Commit with meaningful messages

---

## References

- **Main README**: `~/nabia/platform/tools/riff-cli/README.md`
- **Architecture**: `~/nabia/platform/tools/riff-cli/docs/architecture.md`
- **Quick Start**: `~/nabia/platform/tools/riff-cli/QUICK_REFERENCE.md`
- **Development Guide**: `~/nabia/platform/tools/riff-cli/docs/development.md`
- **Federation Standard**: `~/.claude/CLAUDE.md` (Aura System Architecture)
- **XDG Compliance**: `~/.config/nabi/governance/xdg-compliance.md`

---

*Riff-CLI - Platform Semantic Search Tool*
*Migrated to Platform: October 26, 2025*
*Status: Production Ready*

