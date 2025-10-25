# Semantic Analysis Guide

Comprehensive guide to the semantic analysis module for conversation DAG analysis.

## Overview

The `analysis.py` module provides semantic analysis capabilities for ConversationDAG:

- **ThreadDetector**: Identifies threads, side discussions, and orphaned branches
- **CorruptionScorer**: Scores likelihood of corruption based on structural patterns
- **SemanticAnalyzer**: Extracts topics and clusters messages by semantic similarity

**Key Features**:
- No ML models required (heuristic-based MVP)
- Works with real JSONL data
- Comprehensive logging
- Type-safe with Python 3.13+ annotations

---

## Quick Start

```python
from riff.graph import (
    ConversationDAG,
    JSONLLoader,
    analyze_session_semantics,
)

# Load a session
loader = JSONLLoader("~/.claude/conversations")
dag = ConversationDAG(loader, "session-id")
session = dag.to_session()

# Enhance with semantic analysis
enhanced_session = analyze_session_semantics(session)

# Access semantic information
for thread in enhanced_session.threads:
    print(f"Thread: {thread.semantic_topic} ({len(thread.messages)} messages)")

for orphan in enhanced_session.orphans:
    print(f"Orphan: corruption={orphan.corruption_score:.2f}")
```

---

## ThreadDetector

Identifies threads in a conversation by analyzing parent-child relationships and semantic patterns.

### Algorithm

1. **Find roots**: Messages with no parent
2. **Build components**: Connected groups via DFS traversal
3. **Identify main thread**: Longest continuous path from roots
4. **Classify components**: Side discussions vs orphaned branches
5. **Detect re-entry**: Where side discussions rejoin main thread

### Usage

```python
from riff.graph.analysis import ThreadDetector

messages = [...]  # List of Message objects
detector = ThreadDetector(messages)
threads = detector.identify_threads()

for thread in threads:
    print(f"{thread.thread_type}: {len(thread.messages)} messages")
```

### Thread Classification

#### Main Thread
- Longest continuous path from root
- Primary conversation flow
- Type: `ThreadType.MAIN`

#### Side Discussion
- Branches from main thread
- Has re-entry point back to main
- Often marked with `is_sidechain=True`
- Type: `ThreadType.SIDE_DISCUSSION`

#### Orphaned Branch
- No valid path to main thread
- Broken parent reference
- High corruption score
- Type: `ThreadType.ORPHANED`

### Re-entry Detection

Side discussions are identified by finding where they reconnect to the main thread:

```python
detector = ThreadDetector(messages)
threads = detector.identify_threads()

for thread in threads:
    if thread.thread_type == ThreadType.SIDE_DISCUSSION:
        print(f"Re-enters at: {thread.parent_thread_id}")
```

---

## CorruptionScorer

Analyzes message patterns to detect structural corruption and resume failures.

### Corruption Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Null parent (non-root) | +0.4 | Message without parent but not truly a root |
| Timestamp anomaly | +0.2 | Suspicious timestamp patterns |
| Sidechain without parent | +0.3 | Marked as sidechain but disconnected |
| Continuation markers | +0.1 | Content suggests it's a continuation |

### Usage

```python
from riff.graph.analysis import CorruptionScorer

# Score individual messages
messages = [...]
corruption_score = CorruptionScorer.score_corruption(messages)
print(f"Corruption: {corruption_score:.2f}")

# Detect all orphaned branches
orphans = CorruptionScorer.detect_orphans(messages)
for orphan in orphans:
    print(f"Orphan: {orphan.thread_id}, score={orphan.corruption_score:.2f}")
```

### Corruption Signals

#### Content-based Signals

Messages that look like continuations:

```python
# User messages
- "continue"
- "resume"
- "back to"
- "as we were discussing"
- "returning to"

# Assistant messages
- "as mentioned"
- "as we discussed"
- "continuing from"
- "building on"
```

#### Structural Signals

- `parent_uuid=null` for non-root messages
- `is_sidechain=true` without valid parent
- Timestamp gaps or overlaps
- Disconnected from any root

### Interpretation

| Score | Interpretation | Action |
|-------|---------------|--------|
| 0.0-0.2 | Low corruption | Likely valid structure |
| 0.2-0.5 | Moderate | Review for issues |
| 0.5-0.8 | High | Probable corruption |
| 0.8-1.0 | Critical | Definitely corrupted |

---

## SemanticAnalyzer

Extracts topics and clusters messages using keyword-based heuristics (no ML required).

### Topic Keywords

Pre-defined topic categories with associated keywords:

- **architecture**: design, structure, component, module, system
- **debugging**: error, bug, fix, debug, issue, problem
- **implementation**: implement, code, function, class, feature
- **documentation**: doc, readme, comment, explain
- **testing**: test, unit test, integration, coverage
- **configuration**: config, setup, install, environment
- **question**: how, what, why, when, where, ?
- **planning**: plan, roadmap, todo, task, milestone

### Extract Topic

```python
from riff.graph.analysis import SemanticAnalyzer

messages = [...]
topic = SemanticAnalyzer.extract_semantic_topic(messages)
print(f"Topic: {topic}")
```

### Cluster by Topic

```python
clusters = SemanticAnalyzer.cluster_by_topic(messages)

for topic, msgs in clusters.items():
    print(f"{topic}: {len(msgs)} messages")
```

### Semantic Similarity

Calculate similarity between message groups:

```python
similarity = SemanticAnalyzer.calculate_semantic_similarity(
    messages_group1,
    messages_group2
)
print(f"Similarity: {similarity:.2f}")  # 0.0-1.0
```

**Algorithm**:
1. Extract topics for both groups
2. If topics match: 1.0
3. Otherwise: Jaccard similarity of word sets

---

## Integration with ConversationDAG

The analysis module works seamlessly with the existing DAG infrastructure:

```python
from riff.graph import ConversationDAG, JSONLLoader, analyze_session_semantics

# Build DAG
loader = JSONLLoader("~/.claude/conversations")
dag = ConversationDAG(loader, "session-id")

# Get session with structural analysis
session = dag.to_session()

# Enhance with semantic analysis
enhanced = analyze_session_semantics(session)

# Now session has:
# - thread.semantic_topic populated
# - message.semantic_topic populated
# - Enhanced corruption scores
```

---

## Utility Functions

### analyze_session_semantics()

Main entry point for semantic analysis:

```python
from riff.graph import analyze_session_semantics

# Takes a Session, returns enhanced Session
enhanced_session = analyze_session_semantics(session)
```

**What it does**:
1. Clusters messages by topic
2. Assigns semantic topics to threads
3. Updates message semantic_topic fields

### detect_orphans_with_scoring()

Convenience function for orphan detection:

```python
from riff.graph import detect_orphans_with_scoring

messages = [...]
orphans = detect_orphans_with_scoring(messages)

# Returns List[Thread] sorted by corruption score (descending)
for orphan in orphans:
    print(f"Orphan: {orphan.corruption_score:.2f}")
```

---

## Testing

Run the test suite:

```bash
PYTHONPATH=/path/to/riff-cli/src python3 -m riff.graph.test_analysis
```

**Test coverage**:
- ThreadDetector: main thread, side discussions, orphans
- CorruptionScorer: scoring, orphan detection
- SemanticAnalyzer: topic extraction, clustering, similarity
- Integration: full pipeline

---

## Logging

The module uses Python's logging framework:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger("riff.graph.analysis")
logger.setLevel(logging.INFO)
```

**Log levels**:
- `DEBUG`: Detailed analysis steps
- `INFO`: High-level progress
- `WARNING`: Potential issues
- `ERROR`: Failures

---

## Advanced Usage

### Custom Topic Keywords

Extend the topic keyword dictionary:

```python
from riff.graph.analysis import SemanticAnalyzer

# Add custom topics
SemanticAnalyzer.TOPIC_KEYWORDS["api"] = [
    "api", "endpoint", "rest", "graphql", "request"
]

# Now API-related messages will be classified as "api" topic
```

### Re-entry Point Analysis

Find where side discussions reconnect:

```python
detector = ThreadDetector(messages)
threads = detector.identify_threads()

main = threads[0]  # Main thread

for thread in threads[1:]:
    re_entry = detector._find_re_entry_point(
        thread.messages,
        main
    )
    if re_entry:
        print(f"Thread {thread.thread_id} re-enters at {re_entry}")
```

### Corruption Debugging

Detailed corruption analysis:

```python
for msg in messages:
    if msg.parent_uuid is None and not is_root(msg):
        print(f"Suspicious null parent: {msg.uuid}")

    if hasattr(msg, "is_sidechain") and msg.is_sidechain:
        if msg.parent_uuid not in message_index:
            print(f"Orphaned sidechain: {msg.uuid}")
```

---

## Performance Considerations

### Time Complexity

- **ThreadDetector**: O(n + e) where n=messages, e=edges (parent-child links)
- **CorruptionScorer**: O(n) linear scan
- **SemanticAnalyzer**: O(n * k) where k=keywords per topic

### Memory Usage

- Message index: O(n) for fast UUID lookup
- Children map: O(e) for parent-child relationships
- Topic clusters: O(n) for message groupings

### Optimization Tips

1. **Batch processing**: Process multiple sessions in parallel
2. **Selective analysis**: Only analyze threads that need scoring
3. **Caching**: Cache topic extractions for large messages

---

## Future Enhancements

### Planned Features

- [ ] ML-based topic extraction (sentence-transformers)
- [ ] Advanced similarity metrics (cosine, BERT)
- [ ] Temporal pattern analysis
- [ ] Interactive repair suggestions
- [ ] Export corruption reports

### API Extensions

```python
# Future: ML-enhanced semantic analysis
from riff.graph.analysis import MLSemanticAnalyzer

analyzer = MLSemanticAnalyzer(model="all-MiniLM-L6-v2")
embeddings = analyzer.embed_messages(messages)
similarity = analyzer.semantic_similarity(msg1, msg2)
```

---

## Troubleshooting

### Common Issues

#### Thread detection not working

```python
# Check message structure
for msg in messages:
    print(f"{msg.uuid} -> {msg.parent_uuid}")

# Verify parent references exist
message_uuids = {msg.uuid for msg in messages}
for msg in messages:
    if msg.parent_uuid and msg.parent_uuid not in message_uuids:
        print(f"Broken parent: {msg.uuid} -> {msg.parent_uuid}")
```

#### Corruption scores too high/low

```python
# Debug scoring factors
from riff.graph.analysis import CorruptionScorer

for msg in messages:
    looks_like_continuation = CorruptionScorer._looks_like_continuation(msg)
    if looks_like_continuation:
        print(f"Continuation detected: {msg.content[:50]}")
```

#### Topic extraction inaccurate

```python
# Check keyword matches
text = " ".join(msg.content.lower() for msg in messages)
for topic, keywords in SemanticAnalyzer.TOPIC_KEYWORDS.items():
    matches = sum(text.count(kw) for kw in keywords)
    if matches > 0:
        print(f"{topic}: {matches} matches")
```

---

## See Also

- [ConversationDAG Documentation](./README.md)
- [Semantic DAG Design](../../docs/SEMANTIC_DAG_DESIGN.md)
- [Models Reference](./models.py)
- [DAG Construction](./dag.py)
- [Visualization Guide](./README.md)

---

## License

Part of riff-cli. See project LICENSE for details.
