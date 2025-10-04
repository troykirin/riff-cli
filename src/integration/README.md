# Integration Modules for claude-code

This directory contains standalone modules extracted from riff-cli that can be directly integrated into claude-code.

## Available Modules

### intent_enhancer_module.py

**Purpose**: Enhances search intents with pattern-based keyword expansion

**Key Features**:
- Zero external dependencies (pure Python)
- Transforms 4 words → 19+ contextually relevant keywords
- Domain-aware pattern matching for technical terms
- Search routing strategy recommendations

**Integration Example**:
```python
from intent_enhancer_module import IntentEnhancer

# Initialize enhancer
enhancer = IntentEnhancer()

# Enhance a search intent
result = enhancer.enhance("find nabia federation discussions", depth=3)

# Access enhanced keywords
keywords = result["enhanced_keywords"]
# ['nabia', 'federation', 'memchain', 'orchestration', 'agent',
#  'coordination', 'protocol', 'discussions', 'conversation',
#  'dialogue', 'chat', 'find', 'search', 'locate', 'discover', ...]

# Get routing strategy
routing = result["routing"]
# {'strategy': 'conversation_focused', 'primary_source': 'conversations', ...}
```

**API Reference**:

```python
class IntentEnhancer:
    def enhance(intent: str, depth: int = 3) -> Dict[str, Any]:
        """
        Returns:
        {
            "original_intent": str,
            "enhanced_keywords": List[str],
            "routing": Dict[str, Any],
            "keyword_count": int
        }
        """
```

## Integration Points

### 1. Search Enhancement
- Drop into claude-code's search functionality
- Use enhanced keywords for improved recall
- Apply routing strategies for targeted searches

### 2. Context Expansion
- Enhance user queries before processing
- Generate related terms for broader context retrieval
- Improve match accuracy in large datasets

### 3. Intent Analysis
- Determine user's search focus (conversation/project/technical)
- Route queries to appropriate data sources
- Optimize search performance with targeted strategies

## Type Safety

The module is designed with type hints for easy integration:

```python
from typing import List, Dict, Any

def enhance(intent: str, depth: int = 3) -> Dict[str, Any]: ...
```

## Performance Characteristics

- **Memory**: O(1) - Fixed pattern dictionaries
- **Time**: O(n) where n is intent string length
- **No I/O**: Pure computation, no file/network access
- **Thread-safe**: No mutable shared state

## Testing

Comprehensive test suite available in `tests/test_intent_enhancer.py`:
- 95%+ code coverage
- Edge case handling
- Unicode support
- Pattern matching validation

Run tests:
```bash
pytest tests/test_intent_enhancer.py -v
```

## License Compatibility

This module is provided as-is for integration into claude-code.
No external dependencies ensure maximum compatibility.