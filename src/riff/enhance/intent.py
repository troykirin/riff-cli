"""AI-powered intent enhancement for search queries with NLP stemming support"""

from __future__ import annotations

from typing import Literal
import sys
from pathlib import Path

# Import NLP-enabled IntentEnhancer from integration module
# Add src to path to allow relative imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from integration.intent_enhancer_module import IntentEnhancer as NLPIntentEnhancer
    HAS_NLP = True
except ImportError:
    # Fallback if integration module not available
    HAS_NLP = False
    NLPIntentEnhancer = None  # type: ignore


class IntentEnhancer:
    """
    Enhance search queries with keyword expansion and intent detection.
    
    This is a wrapper around the NLP-enabled IntentEnhancer that provides
    backward compatibility with the simple API while enabling NLP stemming
    when available.
    """

    def __init__(
        self,
        enable_stemming: bool = True,
        auto_download_nltk: bool = False,
        stemming_method: Literal["porter", "snowball", "lemmatizer"] = "porter"
    ):
        """
        Initialize intent enhancer.
        
        Args:
            enable_stemming: Enable NLP stemming if available (default: True)
            auto_download_nltk: Auto-download NLTK data if missing (default: False)
            stemming_method: Preferred stemming method (default: "porter")
        """
        if HAS_NLP and NLPIntentEnhancer is not None:
            # Use NLP-enabled version
            self._enhancer = NLPIntentEnhancer(
                enable_stemming=enable_stemming,
                auto_download_nltk=auto_download_nltk,
                stemming_method=stemming_method
            )
            self._has_nlp = True
        else:
            # Fallback to simple pattern-based enhancement
            self._enhancer = None
            self._has_nlp = False
            # Simple patterns for fallback
            self.patterns = {
                r'memory': ['memory', 'context', 'state', 'persistence', 'storage'],
                r'federation': ['federation', 'coordination', 'agents', 'multi-agent', 'distributed'],
                r'search': ['search', 'query', 'find', 'lookup', 'discover'],
                r'bug|error|issue': ['bug', 'error', 'issue', 'problem', 'failure', 'crash'],
                r'riff': ['riff', 'conversation', 'session', 'dialogue', 'chat'],
                r'performance': ['performance', 'speed', 'optimization', 'efficiency', 'latency'],
            }

    def enhance_query(self, query: str) -> str:
        """
        Expand query with related keywords (backward-compatible API).
        
        Args:
            query: Search query to enhance
            
        Returns:
            Enhanced query string with expanded keywords
        """
        if self._has_nlp and self._enhancer is not None:
            # Use NLP-enabled enhancement
            result = self._enhancer.enhance(query, depth=3)
            # Return space-separated keywords for backward compatibility
            return " ".join(result["enhanced_keywords"])
        else:
            # Fallback to simple pattern matching
            return self._simple_enhance(query)

    def _simple_enhance(self, query: str) -> str:
        """Simple pattern-based enhancement (fallback)"""
        import re
        words = query.split()
        expanded = []

        for word in words:
            expanded.append(word)

            # Check if word matches any pattern
            for pattern, replacements in self.patterns.items():
                if re.search(pattern, word.lower()):
                    # Add related keywords (avoid duplicates)
                    for replacement in replacements:
                        if replacement.lower() not in [w.lower() for w in expanded]:
                            expanded.append(replacement)
                    break

        return " ".join(expanded)

    def enhance(self, intent: str, depth: int = 3) -> dict:
        """
        Enhance search intent with expanded keywords (full API).
        
        Args:
            intent: Original search intent from user
            depth: Enhancement depth (1-5, affects expansion breadth)
            
        Returns:
            Dict containing enhanced keywords, routing strategy, and metadata
        """
        if self._has_nlp and self._enhancer is not None:
            return self._enhancer.enhance(intent, depth)
        else:
            # Fallback: return simple enhancement as dict
            keywords = self._simple_enhance(intent).split()
            return {
                "original_intent": intent,
                "enhanced_keywords": keywords,
                "routing": {"strategy": "balanced"},
                "keyword_count": len(keywords)
            }

    def stem_query(self, query: str) -> list[str]:
        """
        Stem all words in a query using NLP stemming.
        
        Args:
            query: Query string to stem
            
        Returns:
            List of unique stemmed word variants
        """
        if self._has_nlp and self._enhancer is not None:
            return self._enhancer.stem_query(query)
        else:
            # Fallback: return tokenized words
            import re
            return re.findall(r'\b[a-zA-Z][-a-zA-Z]*\b', query.lower())

    def get_stemming_info(self) -> dict:
        """
        Get information about stemming capabilities.
        
        Returns:
            Dict with stemming status and capabilities
        """
        if self._has_nlp and self._enhancer is not None:
            return self._enhancer.get_stemming_info()
        else:
            return {
                "enabled": False,
                "method": None,
                "has_nltk": False,
                "capabilities": {}
            }

    def detect_intent(self, query: str) -> str:
        """
        Detect query intent type (backward-compatible method).
        
        Args:
            query: Query string to analyze
            
        Returns:
            Intent type: "question", "search", "debug", "optimization", or "general"
        """
        query_lower = query.lower()

        if any(word in query_lower for word in ['what', 'how', 'why', 'where']):
            return "question"
        elif any(word in query_lower for word in ['find', 'search', 'look', 'show']):
            return "search"
        elif any(word in query_lower for word in ['error', 'bug', 'fail', 'crash']):
            return "debug"
        elif any(word in query_lower for word in ['improve', 'optimize', 'speed', 'faster']):
            return "optimization"
        else:
            return "general"

    def suggest_filters(self, query: str) -> dict:
        """
        Suggest useful filters based on query intent (backward-compatible method).
        
        Args:
            query: Query string to analyze
            
        Returns:
            Dict with intent and suggested filters
        """
        intent = self.detect_intent(query)
        suggestions = {
            "intent": intent,
            "suggested_filters": []
        }

        if intent == "debug":
            suggestions["suggested_filters"] = ["--min-score=0.5"]
        elif intent == "optimization":
            suggestions["suggested_filters"] = ["--limit=20"]

        return suggestions
