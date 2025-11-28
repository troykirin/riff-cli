# NLP Stemming Quick Reference

## Installation

```bash
# With NLP support (recommended)
cd /Users/tryk/nabia/tools/riff-cli
uv pip install -e ".[nlp]"

# Without NLP (uses fallback stemming)
uv pip install -e .
```

## Basic Usage

### Standalone Stemming

```python
from integration.nlp_stemmer import NLPStemmer

# Initialize
stemmer = NLPStemmer()

# Stem a single word
stemmer.stem("running")  # -> "run"

# Stem a query (get all variants)
stemmer.stem_query("running agents")
# -> ["agent", "agents", "run", "running"]
```

### Intent Enhancement

```python
from integration.intent_enhancer_module import IntentEnhancer

# Initialize with stemming enabled
enhancer = IntentEnhancer(enable_stemming=True)

# Enhance a search query
result = enhancer.enhance("find running agents", depth=3)
print(result["enhanced_keywords"])
# -> ["agent", "agents", "bot", "find", "run", "running", ...]
```

## API Reference

### NLPStemmer Class

#### Constructor
```python
NLPStemmer(
    auto_download: bool = False,      # Auto-download NLTK data
    language: str = "english",         # Snowball language
    suppress_warnings: bool = True     # Suppress NLTK warnings
)
```

#### Methods

**stem(word, method)**
```python
stemmer.stem("running", method="porter")    # -> "run"
stemmer.stem("running", method="snowball")  # -> "run"
stemmer.stem("running", method="lemmatizer") # -> "run"
```

**stem_query(query)**
```python
stemmer.stem_query("running agents")
# -> ["agent", "agents", "run", "running"]
```

**batch_stem(words, method)**
```python
stemmer.batch_stem(["running", "agents"], method="porter")
# -> ["run", "agent"]
```

**stem_with_metadata(word, method)**
```python
result = stemmer.stem_with_metadata("running")
# -> {
#   "original": "running",
#   "stemmed": "run",
#   "method": "porter",
#   "success": True
# }
```

**get_capabilities()**
```python
caps = stemmer.get_capabilities()
# -> {
#   "has_nltk": True/False,
#   "has_porter": True/False,
#   "has_snowball": True/False,
#   "has_wordnet": True/False,
#   "nltk_data_path": "path" or None
# }
```

### IntentEnhancer Class

#### Constructor
```python
IntentEnhancer(
    enable_stemming: bool = True,        # Enable NLP stemming
    auto_download_nltk: bool = False,    # Auto-download NLTK
    stemming_method: str = "porter"      # "porter", "snowball", "lemmatizer"
)
```

#### Methods

**enhance(intent, depth)**
```python
result = enhancer.enhance("find agents", depth=3)
# -> {
#   "original_intent": "find agents",
#   "enhanced_keywords": [...],
#   "routing": {...},
#   "keyword_count": 15
# }
```

**stem_query(query)** *(new)*
```python
variants = enhancer.stem_query("running agents")
# -> ["agent", "agents", "run", "running"]
```

**get_stemming_info()** *(new)*
```python
info = enhancer.get_stemming_info()
# -> {
#   "enabled": True,
#   "method": "porter",
#   "has_nltk": True,
#   "capabilities": {...}
# }
```

## Stemming Methods Comparison

| Method | Speed | Accuracy | Best For |
|--------|-------|----------|----------|
| **Porter** | Fastest | Good | English general text |
| **Snowball** | Fast | Better | Multi-language support |
| **Lemmatizer** | Slower | Best | Semantic precision |
| **Fallback** | Fastest | Fair | No NLTK available |

## Common Patterns

### Check if Stemming is Available
```python
from integration.nlp_stemmer import has_nltk_support

if has_nltk_support():
    print("NLTK available")
else:
    print("Using fallback stemming")
```

### Use Different Stemming Methods
```python
# Porter (fast, basic)
enhancer_porter = IntentEnhancer(
    enable_stemming=True,
    stemming_method="porter"
)

# Snowball (balanced)
enhancer_snowball = IntentEnhancer(
    enable_stemming=True,
    stemming_method="snowball"
)

# Lemmatizer (accurate)
enhancer_lemma = IntentEnhancer(
    enable_stemming=True,
    stemming_method="lemmatizer"
)
```

### Disable Stemming
```python
# Disable for specific use cases
enhancer = IntentEnhancer(enable_stemming=False)
```

### Auto-Download NLTK Data
```python
# First time setup - auto-download NLTK data
enhancer = IntentEnhancer(
    enable_stemming=True,
    auto_download_nltk=True  # Downloads on first use
)
```

## Examples by Use Case

### Search Enhancement
```python
from integration.intent_enhancer_module import IntentEnhancer

enhancer = IntentEnhancer(enable_stemming=True)

# User search query
user_query = "find conversations about implementing Linear"

# Enhance for search
result = enhancer.enhance(user_query, depth=4)

# Use expanded keywords for search
keywords = result["enhanced_keywords"]
# -> ["api", "build", "conversation", "create", "develop",
#     "dialogue", "implement", "implementing", "linear", ...]
```

### Keyword Expansion
```python
from integration.nlp_stemmer import NLPStemmer

stemmer = NLPStemmer()

# Expand single keyword
base_keyword = "development"
variants = stemmer.stem_query(base_keyword)
# -> ["develop", "development"]

# Use all variants in search
for variant in variants:
    search_with_keyword(variant)
```

### Batch Processing
```python
from integration.nlp_stemmer import NLPStemmer

stemmer = NLPStemmer()

# Process multiple keywords at once
keywords = ["running", "implementing", "configuration"]
stemmed = stemmer.batch_stem(keywords, method="porter")
# -> ["run", "implement", "configur"]
```

## Type Definitions

### StemResult
```python
from integration.nlp_stemmer import StemResult

result: StemResult = {
    "original": "running",
    "stemmed": "run",
    "method": "porter",  # "porter" | "snowball" | "lemmatizer" | "fallback"
    "success": True
}
```

### StemmerCapabilities
```python
from integration.nlp_stemmer import StemmerCapabilities

caps: StemmerCapabilities = {
    "has_nltk": True,
    "has_porter": True,
    "has_snowball": True,
    "has_wordnet": True,
    "nltk_data_path": "/path/to/nltk_data"
}
```

## Testing

### Run Tests
```bash
# Run stemmer tests
pytest tests/test_nlp_stemmer.py -v

# Run integration tests
pytest tests/test_intent_enhancer_nlp.py -v

# Run all tests
pytest tests/test_nlp_stemmer.py tests/test_intent_enhancer_nlp.py -v
```

### Type Checking
```bash
# Check type safety
mypy src/integration/nlp_stemmer.py --strict
mypy src/integration/intent_enhancer_module.py --strict
```

### Linting
```bash
# Verify code quality
ruff check src/integration/nlp_stemmer.py
ruff check src/integration/intent_enhancer_module.py
```

## Performance Tips

1. **Reuse stemmer instances** - Creating a stemmer is expensive
   ```python
   # Good
   stemmer = NLPStemmer()
   for word in words:
       stemmer.stem(word)

   # Bad
   for word in words:
       stemmer = NLPStemmer()  # Creates new instance each time
       stemmer.stem(word)
   ```

2. **Use batch operations** for multiple words
   ```python
   # Better
   results = stemmer.batch_stem(words)

   # Slower
   results = [stemmer.stem(w) for w in words]
   ```

3. **Choose the right method** for your use case
   - Use **Porter** for speed
   - Use **Snowball** for balance
   - Use **Lemmatizer** for accuracy

4. **Cache results** if stemming same words repeatedly
   ```python
   cache = {}
   def cached_stem(word):
       if word not in cache:
           cache[word] = stemmer.stem(word)
       return cache[word]
   ```

## Troubleshooting

### NLTK Import Error
```python
# If you get "No module named 'nltk'"
# Install with: uv pip install nltk

# Or use fallback (already built-in)
enhancer = IntentEnhancer(enable_stemming=True)
# Will automatically use fallback if NLTK unavailable
```

### NLTK Data Not Found
```python
# Auto-download NLTK data
stemmer = NLPStemmer(auto_download=True)

# Or manually download
import nltk
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')
```

### Unexpected Stemming Results
```python
# Try different methods
porter = stemmer.stem("running", "porter")
snowball = stemmer.stem("running", "snowball")
lemma = stemmer.stem("running", "lemmatizer")

# Compare results
print(f"Porter: {porter}, Snowball: {snowball}, Lemma: {lemma}")
```

## More Information

- **Full documentation**: See `STEMMING_IMPLEMENTATION_SUMMARY.md`
- **Examples**: See `examples/stemming_demo.py`
- **Tests**: See `tests/test_nlp_stemmer.py` and `tests/test_intent_enhancer_nlp.py`
- **Source code**: See `src/integration/nlp_stemmer.py` and `src/integration/intent_enhancer_module.py`
