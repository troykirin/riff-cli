"""AI-powered intent enhancement for search queries"""

from __future__ import annotations

import re


class IntentEnhancer:
    """Enhance search queries with keyword expansion and intent detection"""

    def __init__(self):
        """Initialize intent enhancer"""
        # Common patterns and their expansions
        self.patterns = {
            r'memory': ['memory', 'context', 'state', 'persistence', 'storage'],
            r'federation': ['federation', 'coordination', 'agents', 'multi-agent', 'distributed'],
            r'search': ['search', 'query', 'find', 'lookup', 'discover'],
            r'bug|error|issue': ['bug', 'error', 'issue', 'problem', 'failure', 'crash'],
            r'riff': ['riff', 'conversation', 'session', 'dialogue', 'chat'],
            r'performance': ['performance', 'speed', 'optimization', 'efficiency', 'latency'],
        }

    def enhance_query(self, query: str) -> str:
        """Expand query with related keywords"""
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

    def detect_intent(self, query: str) -> str:
        """Detect query intent type"""
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
        """Suggest useful filters based on query intent"""
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
