# Quick Start Guide

Get started with the SurrealDB conversation schema in 5 minutes.

## Prerequisites

```bash
# Install SurrealDB
brew install surrealdb/tap/surreal  # macOS
# OR
curl -sSf https://install.surrealdb.com | sh  # Linux

# Install Python client
uv pip install surrealdb
```

## 1. Start SurrealDB

```bash
surreal start --bind 0.0.0.0:8000 --user root --pass root
```

## 2. Import Schema

```bash
cd /Users/tryk/nabia/tools/riff-cli

surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  src/riff/surrealdb/schema.sql
```

## 3. Run Examples

```bash
python3 -m src.riff.surrealdb.example_usage
```

## 4. Test Your Setup

```python
import asyncio
from src.riff.surrealdb import (
    prepare_session_record,
    prepare_message_record,
    validate_message_data,
)
from surrealdb import Surreal


async def quick_test():
    """Quick test of SurrealDB schema."""
    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        # Create session
        session = prepare_session_record(
            session_id="quickstart-test",
            message_count=0,
        )
        await db.create("session", session)
        print("✓ Created session")

        # Create message
        message = prepare_message_record(
            session_id="quickstart-test",
            message_uuid="msg-001",
            message_type="user",
            role="user",
            content="Hello from quickstart!",
            timestamp="2025-01-15T10:00:00Z",
        )

        # Validate
        is_valid, error = validate_message_data(message)
        if not is_valid:
            print(f"✗ Validation failed: {error}")
            return

        await db.create("message", message)
        print("✓ Created message")

        # Query back
        result = await db.query(
            "SELECT * FROM message WHERE session_id = 'quickstart-test';"
        )
        print(f"✓ Retrieved {len(result[0]['result'])} messages")
        print("\nQuickstart test passed!")


asyncio.run(quick_test())
```

Save as `quickstart_test.py` and run:
```bash
python3 quickstart_test.py
```

## Expected Output

```
✓ Created session
✓ Created message
✓ Retrieved 1 messages

Quickstart test passed!
```

## Next Steps

1. **Read the Documentation**:
   - [README.md](./README.md) - Full user guide
   - [SCHEMA_REFERENCE.md](./SCHEMA_REFERENCE.md) - Technical reference
   - [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) - Phase 6B integration

2. **Explore Examples**:
   - Run `python3 -m src.riff.surrealdb.example_usage`
   - Browse `example_usage.py` for more patterns

3. **Run Tests**:
   ```bash
   pytest src/riff/surrealdb/test_schema.py -v
   ```

4. **Integrate with riff-cli**:
   - Follow [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
   - Implement `SurrealDBBackend` class
   - Update CLI commands

## Common Issues

### Connection Refused
```bash
# Check SurrealDB is running
ps aux | grep surreal

# Restart if needed
surreal start --bind 0.0.0.0:8000 --user root --pass root
```

### Import Errors
```bash
# Make sure you're in project root
cd /Users/tryk/nabia/tools/riff-cli

# Install dependencies
uv pip install surrealdb
```

### Schema Import Fails
```bash
# Verify SQL syntax
cat src/riff/surrealdb/schema.sql | surreal sql \
  --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations
```

## Help

For detailed help, see:
- **Full Documentation**: [README.md](./README.md)
- **Troubleshooting**: [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md#troubleshooting)
- **API Reference**: [SCHEMA_REFERENCE.md](./SCHEMA_REFERENCE.md)
