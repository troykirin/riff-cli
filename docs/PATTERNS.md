# Reusable Patterns from riff-cli

This document captures key patterns and insights from riff-cli development that can be applied to other projects in the federation.

## 1. Recursive Keyword Enhancement Pattern

### Pattern Description
Transform simple user intents into comprehensive keyword sets through multi-layer expansion.

### Implementation Template
```python
class KeywordEnhancer:
    def enhance(self, input_text: str) -> List[str]:
        keywords = [input_text]
        keywords.extend(self._pattern_expand(input_text))
        keywords.extend(self._semantic_expand(input_text))
        keywords.extend(self._context_expand(input_text))
        return list(set(keywords))
```

### Use Cases
- **Search Systems**: Improve recall in document/log search
- **Alert Matching**: Expand alert patterns for better coverage
- **Tag Generation**: Auto-generate comprehensive tags
- **Context Retrieval**: Enhance vector database queries

### Federation Applications
- **Loki Log Search**: Enhance log query patterns
- **Memory Retrieval**: Improve knowledge base searches
- **Agent Communication**: Expand handoff context

## 2. Intent-Aware Routing Pattern

### Pattern Description
Analyze user intent to determine optimal processing strategy.

### Implementation Template
```python
class IntentRouter:
    ROUTES = {
        'pattern': (regex, handler, config),
        # ...
    }

    def route(self, intent: str) -> Tuple[handler, config]:
        for pattern, handler, config in self.ROUTES:
            if pattern.match(intent):
                return handler, config
        return default_handler, default_config
```

### Use Cases
- **Multi-Source Search**: Route to appropriate data sources
- **Agent Delegation**: Select appropriate specialist agent
- **Resource Optimization**: Allocate resources based on intent

### Federation Applications
- **Agent Selection**: Route tasks to appropriate specialists
- **Database Selection**: Choose between memory layers
- **API Routing**: Direct requests to correct endpoints

## 3. Format Auto-Detection Pattern

### Pattern Description
Automatically detect data format and adapt processing accordingly.

### Implementation Template
```python
class FormatDetector:
    def detect(self, path: str) -> str:
        indicators = {
            'jsonl': lambda p: glob(p + "**/*.jsonl"),
            'json': lambda p: exists(p + "conversations.json"),
            'csv': lambda p: glob(p + "**/*.csv")
        }

        for format_type, check in indicators.items():
            if check(path):
                return format_type
        return 'unknown'
```

### Use Cases
- **Data Import**: Handle multiple import formats
- **Log Processing**: Adapt to different log formats
- **Export Handling**: Process various export types

### Federation Applications
- **Memory Import**: Handle different knowledge formats
- **Log Aggregation**: Process varied log sources
- **Data Migration**: Convert between formats

## 4. Streaming Processing Pattern

### Pattern Description
Process large datasets without loading everything into memory.

### Implementation Template
```python
def stream_process(filepath: str, processor: Callable):
    with open(filepath) as f:
        for line in f:
            result = processor(line)
            if result:
                yield result
```

### Use Cases
- **Large File Processing**: Handle multi-GB files
- **Real-time Processing**: Process data as it arrives
- **Memory Efficiency**: Reduce memory footprint

### Federation Applications
- **Log Streaming**: Process logs in real-time
- **Event Processing**: Handle federation events
- **Bulk Operations**: Process large datasets

## 5. Progressive Enhancement Pattern

### Pattern Description
Start with basic functionality, progressively add features based on availability.

### Implementation Hierarchy
```
1. Basic (riff.nu) - Core functionality, no dependencies
2. Enhanced (riff-enhanced.nu) - Visual feedback, progress bars
3. Advanced (riff-claude.nu) - Intent analysis, routing
```

### Use Cases
- **Graceful Degradation**: Function with missing dependencies
- **Feature Flags**: Enable features progressively
- **Performance Tiers**: Adapt to system capabilities

### Federation Applications
- **Agent Capabilities**: Scale features by agent tier
- **Resource Adaptation**: Adjust to available resources
- **Fallback Strategies**: Ensure reliability

## 6. Domain Knowledge Encoding Pattern

### Pattern Description
Encode domain knowledge as data structures for easy maintenance.

### Implementation Template
```python
DOMAIN_KNOWLEDGE = {
    'technical_terms': {
        'federation': ['distributed', 'coordination', ...],
        'authentication': ['oauth', 'token', 'session', ...]
    },
    'relationships': {
        'parent-child': [('project', 'task'), ('epic', 'story')],
        'synonyms': [('bug', 'issue'), ('feature', 'enhancement')]
    }
}
```

### Use Cases
- **Knowledge Graphs**: Build relationship maps
- **Ontology Management**: Maintain domain taxonomies
- **Context Building**: Generate relevant context

### Federation Applications
- **Agent Knowledge**: Share domain expertise
- **Memory Organization**: Structure knowledge base
- **Semantic Search**: Enhance search with relationships

## 7. Multi-Strategy Search Pattern

### Pattern Description
Combine multiple search strategies for comprehensive results.

### Implementation Template
```python
class MultiStrategySearcher:
    strategies = [
        ExactMatchStrategy(),
        FuzzyMatchStrategy(),
        SemanticMatchStrategy()
    ]

    def search(self, query: str) -> List[Result]:
        results = []
        for strategy in self.strategies:
            results.extend(strategy.search(query))
        return self.deduplicate(results)
```

### Use Cases
- **Hybrid Search**: Combine keyword + semantic search
- **Fallback Search**: Try multiple approaches
- **Comprehensive Coverage**: Ensure nothing is missed

### Federation Applications
- **Memory Search**: Search across memory layers
- **Agent Discovery**: Find agents by multiple criteria
- **Log Analysis**: Multiple pattern matching strategies

## 8. Interactive Selection Pattern

### Pattern Description
Provide interactive selection interfaces for user choice.

### Implementation Template
```bash
# Using fzf for interactive selection
echo "$results" | fzf --multi --preview 'echo {}'

# Using Python prompt_toolkit
from prompt_toolkit import prompt
selected = prompt('Select: ', completer=completer)
```

### Use Cases
- **Result Selection**: Choose from search results
- **Configuration**: Interactive setup wizards
- **Navigation**: Browse hierarchical data

### Federation Applications
- **Agent Selection**: Choose appropriate agent
- **Task Assignment**: Interactive task routing
- **Configuration Management**: Setup federation

## 9. Result Aggregation Pattern

### Pattern Description
Aggregate results from multiple sources with deduplication.

### Implementation Template
```python
class ResultAggregator:
    def aggregate(self, *sources) -> List[Result]:
        seen_ids = set()
        results = []

        for source in sources:
            for result in source:
                if result.id not in seen_ids:
                    seen_ids.add(result.id)
                    results.append(result)

        return self.rank(results)
```

### Use Cases
- **Multi-Source Search**: Combine results
- **Data Fusion**: Merge from multiple APIs
- **Distributed Queries**: Aggregate from shards

### Federation Applications
- **Cross-Agent Results**: Combine agent outputs
- **Memory Fusion**: Merge memory layer results
- **Event Aggregation**: Combine event streams

## 10. Modular CLI Architecture Pattern

### Pattern Description
Build CLIs as composable modules with clear interfaces.

### Structure Template
```
cli/
├── core/          # Core functionality
├── enhancers/     # Enhancement modules
├── formatters/    # Output formatters
└── integrations/  # External integrations
```

### Use Cases
- **Extensible CLIs**: Plugin architecture
- **Feature Composition**: Mix and match features
- **Testing**: Isolated component testing

### Federation Applications
- **Agent CLIs**: Modular agent tools
- **Federation Tools**: Composable utilities
- **Development Tools**: Extensible dev tools

## Key Insights for Federation

### 1. Pattern Composition
Patterns can be composed for powerful combinations:
- Enhancement + Routing = Smart Search
- Streaming + Aggregation = Scalable Processing
- Detection + Strategy = Adaptive Systems

### 2. Zero-Dependency Design
Critical patterns implemented without external dependencies ensure:
- Portability across environments
- Reduced security surface
- Faster deployment

### 3. Data-Driven Configuration
Encoding knowledge as data rather than code:
- Easier updates without code changes
- Shareable across agents
- Version-controlled knowledge

### 4. Progressive Complexity
Start simple, add complexity only when needed:
- Basic → Enhanced → Advanced
- Maintains maintainability
- Easier debugging

### 5. User-Centric Design
Interactive and visual feedback improves:
- User confidence in results
- Error discovery
- System understanding

## Application to Claude-Code Integration

These patterns are particularly relevant for claude-code:

1. **Search Enhancement**: Apply recursive enhancement to code search
2. **Intent Routing**: Route coding tasks to appropriate handlers
3. **Format Detection**: Handle various code file formats
4. **Streaming**: Process large codebases efficiently
5. **Interactive Selection**: Choose from multiple solutions

## Conclusion

The patterns discovered and refined in riff-cli represent reusable solutions that can significantly improve search, processing, and interaction capabilities across the federation. By applying these patterns consistently, we can build more powerful, efficient, and user-friendly tools.