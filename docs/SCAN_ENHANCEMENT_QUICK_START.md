# nabi scan Query Enhancement - Quick Start Guide

## Overview

The `nabi scan` query enhancement feature transforms simple search queries into comprehensive keyword sets using NLP stemming and pattern-based expansion. This guide helps you get started quickly.

## Installation

```bash
cd /Users/tryk/nabia/tools/riff-cli

# Install dependencies
uv sync

# Optional: Install with NLP support
uv sync --extra nlp
```

## Quick Test

```bash
# Test the CLI wrapper
echo '{"query": "federation event schema"}' | python3 src/enhance_cli.py | jq

# Run all tests
task test:scan
```

Expected output:
```json
{
  "status": "success",
  "query": "federation event schema",
  "enhanced_keywords": [
    "agent",
    "coordination",
    "distributed",
    "event",
    "federation",
    "message",
    "network",
    "protocol",
    "schema",
    ...
  ],
  "or_pattern": "(agent|coordination|distributed|event|federation|...)",
  "keyword_count": 25,
  "routing": {
    "strategy": "balanced",
    "primary_source": "all"
  },
  "stemming_info": {
    "enabled": true,
    "method": "porter",
    "has_nltk": true
  }
}
```

## Usage Examples

### 1. Basic Enhancement

```bash
echo '{"query": "find agents"}' | python3 src/enhance_cli.py
```

### 2. Custom Depth

```bash
echo '{"query": "find agents", "depth": 5}' | python3 src/enhance_cli.py
```

### 3. Disable Stemming

```bash
echo '{"query": "running agents", "enable_stemming": false}' | python3 src/enhance_cli.py
```

### 4. Different Stemming Method

```bash
echo '{"query": "running", "stemming_method": "lemmatizer"}' | python3 src/enhance_cli.py
```

## Test Commands

```bash
# All scan tests (115 tests)
task test:scan

# CLI wrapper tests only (25 tests)
task test:scan:cli

# E2E integration tests (21 tests)
task test:scan:e2e

# NLP stemming tests (69 tests)
task test:scan:nlp
```

## Test File Locations

- **CLI Wrapper**: `/Users/tryk/nabia/tools/riff-cli/src/enhance_cli.py`
- **CLI Tests**: `/Users/tryk/nabia/tools/riff-cli/tests/test_enhance_cli.py`
- **E2E Tests**: `/Users/tryk/nabia/tools/riff-cli/tests/e2e/test_scan_integration.py`
- **NLP Tests**: `/Users/tryk/nabia/tools/riff-cli/tests/test_nlp_stemmer.py`

## Common Test Scenarios

### Testing Enhancement

```python
# In your test
import subprocess
import json

input_data = {"query": "your test query"}
result = subprocess.run(
    ["python3", "src/enhance_cli.py"],
    input=json.dumps(input_data),
    capture_output=True,
    text=True,
    timeout=5
)

output = json.loads(result.stdout)
assert output["status"] == "success"
```

### Testing Error Handling

```python
# Test invalid JSON
result = subprocess.run(
    ["python3", "src/enhance_cli.py"],
    input="not valid json",
    capture_output=True,
    text=True
)

assert result.returncode == 1
output = json.loads(result.stdout)
assert output["status"] == "error"
```

### Testing Timeout

```python
# Test with timeout protection
result = subprocess.run(
    ["python3", "src/enhance_cli.py"],
    input=json.dumps({"query": "test"}),
    timeout=5  # 5 second timeout
)
```

## Adding New Test Cases

### 1. Add to test_enhance_cli.py

```python
class TestYourFeature:
    """Test your new feature"""

    def test_your_scenario(self) -> None:
        """Test description"""
        input_data = {
            "query": "your test query"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "success"
        # Add your assertions
```

### 2. Run Your Test

```bash
uv run pytest tests/test_enhance_cli.py::TestYourFeature::test_your_scenario -v
```

## Troubleshooting

### Tests Failing with Import Errors

```bash
# Ensure dependencies installed
uv sync

# Check Python path
which python3

# Verify src/ in Python path
cd /Users/tryk/nabia/tools/riff-cli
```

### NLTK Data Missing

```bash
# Install NLTK and download data
uv pip install nltk
python3 -c "import nltk; nltk.download('punkt'); nltk.download('wordnet')"
```

Or test without stemming:
```json
{"query": "test", "enable_stemming": false}
```

### Timeout Issues

Increase timeout in tests if running on slow machine:
```python
result = subprocess.run([...], timeout=10)  # Increase from 5s
```

## Integration with nabi-cli

### Rust Integration Pattern

```rust
// In nabi-cli Rust code
use std::process::{Command, Stdio};

fn enhance_query(query: &str) -> Result<Vec<String>> {
    let input = serde_json::json!({
        "query": query,
        "depth": 3,
        "enable_stemming": true
    });

    let mut child = Command::new("python3")
        .arg("enhance_cli.py")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()?;

    // Write input
    serde_json::to_writer(child.stdin.as_mut().unwrap(), &input)?;

    // Read output
    let output: serde_json::Value = serde_json::from_reader(child.stdout.unwrap())?;

    if output["status"] == "success" {
        Ok(output["enhanced_keywords"].as_array()
            .unwrap()
            .iter()
            .map(|k| k.as_str().unwrap().to_string())
            .collect())
    } else {
        Err(anyhow!("Enhancement failed: {}", output["error"]))
    }
}
```

## Performance Tips

1. **Reuse subprocess**: For batch queries, keep subprocess alive
2. **Cache results**: Cache enhancement for frequent queries
3. **Adjust depth**: Lower depth (1-2) for faster processing
4. **Disable stemming**: Skip NLTK if not needed for speed

## Next Steps

1. Read full documentation: `/Users/tryk/nabia/tools/riff-cli/docs/TEST_SUITE_DOCUMENTATION.md`
2. Explore test files for examples
3. Add new test cases for your use cases
4. Integrate with Rust nabi-cli

## Quick Reference Card

| Command | Purpose |
|---------|---------|
| `task test:scan` | Run all scan tests (115 tests) |
| `task test:scan:cli` | Run CLI wrapper tests (25 tests) |
| `task test:scan:e2e` | Run E2E tests (21 tests) |
| `task test:scan:nlp` | Run NLP tests (69 tests) |
| `uv sync` | Install dependencies |
| `uv run pytest <file> -v` | Run specific test file |

---

**Ready to test?** Run: `task test:scan`
