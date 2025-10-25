# NabiOS Integration (Optional)

> **Note**: This is optional advanced functionality. Riff CLI works perfectly as a standalone tool.

## What is NabiOS?

NabiOS is a federation ecosystem for autonomous AI agents with:
- Cross-agent coordination
- Persistent memory systems
- Knowledge graph integration
- Multi-agent orchestration

## Integration Benefits

When integrated with NabiOS, Riff CLI gains:

1. **Federated Search**: Coordinate searches across multiple agents
2. **Persistent Memory**: Store search results in federation knowledge base
3. **Enhanced Intent**: Leverage federation-wide context for better keyword expansion
4. **Agent Coordination**: Share search insights across autonomous agents

## Current Status

**Standalone Version**: Riff CLI v3.0.0 has federation features removed for simplicity.

**Federation Version**: Available in the [NabiOS ecosystem](https://github.com/nabiatech/nabia).

## Feature Comparison

| Feature | Standalone | NabiOS Integration |
|---------|-----------|-------------------|
| Claude Export Search | ✅ | ✅ |
| JSONL Search | ✅ | ✅ |
| Intent-Driven Keywords | ✅ | ✅ Enhanced |
| Interactive fzf | ✅ | ✅ |
| Federation Coordination | ❌ | ✅ |
| Persistent Memory | ❌ | ✅ |
| Cross-Agent Search | ❌ | ✅ |
| Knowledge Graph | ❌ | ✅ |

## When to Use NabiOS Integration

Consider NabiOS integration if you:
- Run multiple AI agents that need to coordinate
- Want persistent memory across sessions
- Need knowledge graph integration
- Build complex multi-agent systems

## How to Enable

The NabiOS-integrated version includes:

```nushell
# Federation-specific keyword expansion
let keywords = if ($intent_lower | str contains "nabia") or ($intent_lower | str contains "nabi") {
    $keywords | append ["nabia", "federation", "memchain", "orchestration", "agent", "coordination"]
} else { $keywords }
```

**Installation**:
```bash
# Clone the full NabiOS ecosystem
git clone https://github.com/nabiatech/nabia.git
cd nabia/tools/riff-cli

# Install with federation features
./install.sh
```

## Architecture

### Standalone Riff CLI

```
User → riff → Claude Exports/JSONL → fzf → Results
```

### NabiOS-Integrated Riff CLI

```
User → riff → Federation Layer → Distributed Search
                ↓
          Memory Layer (SurrealDB/Qdrant)
                ↓
          Knowledge Graph Integration
                ↓
          Claude Exports/JSONL → fzf → Results
```

## Migration Path

1. **Start Standalone**: Use this version to learn Riff CLI
2. **Evaluate Needs**: Determine if federation features are needed
3. **Optional Upgrade**: Move to NabiOS ecosystem if needed

## Documentation

For NabiOS integration details, see:
- [NabiOS Documentation](https://github.com/nabiatech/nabia/docs)
- [Federation Protocol](https://github.com/nabiatech/nabia/docs/architecture/FEDERATION.md)
- [Agent Coordination](https://github.com/nabiatech/nabia/docs/architecture/AGENTS.md)

## Support

**Standalone Version**: Open issues on this repository
**NabiOS Integration**: Contact the NabiOS team or open issues on the main repository

---

**Recommendation**: Start with the standalone version. Add NabiOS integration only if you need multi-agent coordination or persistent federation features.
