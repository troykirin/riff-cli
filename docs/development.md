# Riff CLI - Development Guide

**For**: Developers contributing to or extending riff-cli  
**Prerequisites**: Python 3.13+, Docker, uv, task  
**Last Updated**: 2025-10-18

---

## Quick Start

### 1. Clone and Setup

```bash
cd /Users/tryk/nabia/tools/riff-cli
task dev:setup
source .hookrc
```

### 2. Start Infrastructure

```bash
# Start Qdrant
task docker:up

# Verify it's running
task docker:status
```

### 3. Run Tests

```bash
# All tests
task test:all

# Unit tests only
task test:unit

# Integration tests
task test:integration
```

### 4. Try It Out

```bash
# Semantic search
task search -- "memory architecture"

# Or directly
uv run riff search "federation"

# Browse mode (TUI placeholder)
uv run riff browse
```

---

## Development Environment

### Directory Structure

```
riff-cli/
├── src/riff/           # Main package
│   ├── cli.py          # Entry point
│   ├── search/         # Qdrant integration
│   ├── enhance/        # AI enhancement
│   ├── classic/        # Original functionality
│   └── tui/            # TUI (Week 2)
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   ├── fixtures/       # Test data
│   └── pytest.ini      # Pytest config
├── infrastructure/     # Docker configs
├── docs/               # Documentation
├── pyproject.toml      # Project config
└── Taskfile.yml        # Task automation
```

### Virtual Environment

**Location**: `~/.nabi/venvs/riff-cli/`

**Why not `.venv/`?**
- XDG compliance (runtime separate from config)
- Federation integration
- Cross-platform compatibility

**Activation**:
```bash
# Via .hookrc (recommended)
source .hookrc

# Manual
export PATH="$HOME/.nabi/venvs/riff-cli/bin:$PATH"
```

---

## Common Tasks

### Running Commands

```bash
# Search
task search -- "your query"

# Scan JSONL
task scan -- ~/claude/sessions/*.jsonl

# Fix JSONL
task fix -- broken-session.jsonl

# Launch TUI (placeholder)
task riff
```

### Docker Operations

```bash
# Start services
task docker:up

# Stop services
task docker:down

# View logs
task docker:logs

# Restart
task docker:restart

# Check health
task docker:status
```

### Testing

```bash
# Run all tests
task test:all

# Unit tests only
task test:unit

# Integration tests (requires Qdrant running)
task test:integration

# Coverage report
task test:coverage
```

### Code Quality

```bash
# Lint
task dev:lint

# Format
task dev:format

# Clean artifacts
task clean
```

---

## Adding New Features

### 1. Search Enhancements

**File**: `src/riff/search/qdrant.py`

```python
class QdrantSearcher:
    def your_new_method(self, ...):
        """Add your feature here"""
        pass
```

**Tests**: `tests/unit/test_search_core.py`

```python
def test_your_new_feature():
    searcher = QdrantSearcher()
    result = searcher.your_new_method(...)
    assert result == expected
```

### 2. CLI Commands

**File**: `src/riff/cli.py`

```python
def cmd_your_command(args) -> int:
    """Your new command"""
    # Implementation
    return 0

# Add to parser
p_your_cmd = subparsers.add_parser('your-cmd')
p_your_cmd.set_defaults(func=cmd_your_command)
```

### 3. TUI Components (Week 2)

**File**: `src/riff/tui/components/your_component.py`

```python
from prompt_toolkit.widgets import Widget

class YourComponent(Widget):
    """Your TUI component"""
    pass
```

---

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/`

**Coverage Target**: 80%+

```bash
# Run with coverage
uv run pytest tests/unit/ --cov=riff --cov-report=term-missing
```

### Integration Tests

**Location**: `tests/test_search_live.py`

**Requirements**: Qdrant running with test data

```bash
# Ensure Qdrant is up
task docker:status

# Run integration tests
task test:integration
```

### Test Fixtures

**Location**: `tests/fixtures/`

```python
# Use fixtures in tests
def test_with_fixture(mock_session):
    result = search(mock_session)
    assert ...
```

---

## Debugging

### Enable Debug Logging

```bash
# Set environment variable
export RIFF_DEBUG=1
uv run riff search "query"
```

### Check Qdrant Data

```bash
# Collection info
curl http://localhost:6333/collections/claude_sessions

# Search directly
curl -X POST http://localhost:6333/collections/claude_sessions/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [...], "limit": 5}'
```

### Inspect Test Data

```bash
# Explore Qdrant test collection
uv run python tests/explore_qdrant.py
```

---

## Federation Integration

### Register with Nabi CLI

```bash
# Create symlink
task nabi:register

# Verify
task nabi:status

# Test
nabi exec riff search "test"
```

### Update Federation Paths

**File**: `~/.zshenv`

```bash
export NABI_RUNTIME_DIR="$HOME/.nabi"
export NABI_VENV_ROOT="$NABI_RUNTIME_DIR/venvs"
export NABI_BIN_DIR="$NABI_RUNTIME_DIR/bin"
export PATH="$NABI_BIN_DIR:$PATH"
```

---

## Continuous Integration

### Pre-commit Checks

```bash
# Run before committing
task dev:lint
task test:all
task verify
```

### Git Hooks (Future)

```bash
# Install pre-commit hooks
pre-commit install
```

---

## Performance Profiling

### Search Performance

```python
# Add timing
import time
start = time.time()
results = searcher.search(query)
print(f"Search took: {time.time() - start:.2f}s")
```

### Memory Usage

```bash
# Monitor during tests
uv run pytest --memray tests/test_search_live.py
```

---

## Troubleshooting

### Qdrant Not Starting

```bash
# Check Docker
docker ps

# Check logs
task docker:logs

# Restart
task docker:restart
```

### Tests Failing

```bash
# Clean and rebuild
task clean
task dev:setup

# Ensure Qdrant is running
task docker:status

# Run tests with verbose output
uv run pytest -vv
```

### Import Errors

```bash
# Sync dependencies
uv sync

# Verify installation
uv run python -c "import riff; print(riff.__file__)"
```

---

## Contributing

### Code Style

- Use **ruff** for formatting and linting
- Follow PEP 8 guidelines
- Add type hints (Python 3.13 TypedDict, TypeIs)

### Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, refactor, test, chore

**Example**:
```
feat(search): add fuzzy matching to query enhancement

Implemented Levenshtein distance for typo tolerance.
Increases recall by ~15% on test queries.

Closes: NOS-444
```

### Pull Requests

1. Create feature branch
2. Write tests
3. Update documentation
4. Run `task verify`
5. Submit PR with description

---

## Resources

- **Architecture**: docs/ARCHITECTURE.md
- **Handoff Docs**: /private/tmp/docs/riff-cli/
- **Federation**: ~/docs/federation/
- **Nabi CLI**: ~/docs/tools/nabi-cli.md

---

**Need Help?** Check Taskfile: `task --list`
