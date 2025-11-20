#!/usr/bin/env python3
"""
Standalone Intent Enhancement Module for claude-code integration
Pure Python implementation with no external dependencies

This module can be directly integrated into claude-code for
enhancing search capabilities with pattern-based keyword expansion.
"""

from typing import List, Dict, Any, Set
import re


class IntentEnhancer:
    """
    Intent-driven keyword enhancement for improved search accuracy.

    This class provides pattern-based keyword expansion that transforms
    simple search intents into comprehensive keyword sets, improving
    search recall from ~4 keywords to 19+ contextually relevant terms.
    """

    # Domain knowledge patterns for keyword expansion
    DOMAIN_PATTERNS = {
        'nabia': ['federation', 'memchain', 'orchestration', 'agent', 'coordination', 'protocol', 'cognitive', 'intelligence'],
        'claude': ['assistant', 'conversation', 'chat', 'ai', 'llm', 'dialogue', 'anthropic', 'subagent'],
        'linear': ['issue', 'project', 'task', 'ticket', 'workflow', 'development', 'tracking', 'milestone'],
        'federation': ['agent', 'coordination', 'protocol', 'handoff', 'orchestration', 'distributed', 'network', 'mesh'],
        'memory': ['storage', 'retrieval', 'context', 'persistent', 'ephemeral', 'knowledge', 'cache', 'state'],
        'search': ['query', 'find', 'lookup', 'discover', 'filter', 'match', 'locate', 'identify'],
        'integration': ['api', 'webhook', 'connection', 'sync', 'bridge', 'interface', 'mcp', 'proxy'],
        'architecture': ['design', 'pattern', 'structure', 'framework', 'system', 'blueprint', 'topology'],
        'git': ['commit', 'branch', 'merge', 'repository', 'version', 'control', 'diff', 'pull request'],
        'riff': ['search', 'uuid', 'jsonl', 'conversation', 'logs', 'cli', 'tool', 'query'],
        'agent': ['subagent', 'orchestrator', 'delegation', 'task', 'autonomous', 'cognitive', 'intelligent'],
        'oauth': ['authentication', 'authorization', 'token', 'proxy', 'grok', 'notion', 'api']
    }

    # Action-based synonym patterns
    ACTION_PATTERNS = {
        'find': ['search', 'locate', 'discover', 'identify', 'retrieve', 'lookup'],
        'search': ['find', 'query', 'scan', 'browse', 'explore', 'investigate'],
        'discuss': ['talk', 'conversation', 'dialogue', 'chat', 'communication', 'exchange'],
        'implement': ['build', 'create', 'develop', 'construct', 'design', 'code'],
        'configure': ['setup', 'initialize', 'customize', 'adjust', 'modify', 'tune'],
        'integrate': ['connect', 'link', 'bridge', 'sync', 'merge', 'combine'],
        'debug': ['troubleshoot', 'diagnose', 'fix', 'resolve', 'investigate', 'analyze']
    }

    # Semantic relationship mappings
    SEMANTIC_MAPS = {
        'agent': ['bot', 'assistant', 'worker', 'service', 'process'],
        'system': ['platform', 'framework', 'infrastructure', 'architecture'],
        'data': ['information', 'content', 'payload', 'dataset', 'record'],
        'process': ['workflow', 'pipeline', 'procedure', 'operation', 'task'],
        'network': ['connection', 'link', 'channel', 'communication', 'protocol'],
        'interface': ['api', 'endpoint', 'contract', 'specification', 'definition'],
        'state': ['status', 'condition', 'mode', 'phase', 'situation'],
        'event': ['message', 'signal', 'notification', 'trigger', 'callback']
    }

    def __init__(self):
        """Initialize the Intent Enhancer"""
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        self.quoted_pattern = re.compile(r'"([^"]*)"')
        self.camelcase_pattern = re.compile(r'\b[a-z]+[A-Z][a-zA-Z]*\b')
        self.kebabcase_pattern = re.compile(r'\b[a-z]+-[a-z-]+\b')
        self.abbreviation_pattern = re.compile(r'\b[A-Z]{2,}\b')

    def enhance(self, intent: str, depth: int = 3) -> Dict[str, Any]:
        """
        Enhance search intent with expanded keywords and routing strategy.

        Args:
            intent: Original search intent from user
            depth: Enhancement depth (1-5, affects expansion breadth)

        Returns:
            Dict containing enhanced keywords, routing strategy, and metadata
        """
        if not intent:
            return {
                "original_intent": intent,
                "enhanced_keywords": [],
                "routing": self._get_default_routing(),
                "keyword_count": 0
            }

        # Collect all keywords
        keywords = self._collect_keywords(intent, depth)

        # Determine routing strategy
        routing = self._determine_routing(intent)

        return {
            "original_intent": intent,
            "enhanced_keywords": sorted(list(keywords)),
            "routing": routing,
            "keyword_count": len(keywords)
        }

    def _collect_keywords(self, intent: str, depth: int) -> Set[str]:
        """Collect all relevant keywords based on intent"""
        keywords = {intent}

        # Extract pattern-based keywords
        keywords.update(self._extract_pattern_keywords(intent))

        # Generate domain-specific keywords
        keywords.update(self._generate_domain_keywords(intent, depth))

        # Add semantic variations
        keywords.update(self._generate_semantic_variations(intent))

        # Remove empty strings and None values
        return {k for k in keywords if k}

    def _extract_pattern_keywords(self, intent: str) -> Set[str]:
        """Extract keywords using pattern matching"""
        keywords = set()
        intent_lower = intent.lower()

        # Domain pattern matching
        for term, expansions in self.DOMAIN_PATTERNS.items():
            if term in intent_lower:
                keywords.update(expansions)

        # Extract quoted phrases
        keywords.update(self.quoted_pattern.findall(intent))

        # Extract technical terms
        keywords.update(self.camelcase_pattern.findall(intent))
        keywords.update(self.kebabcase_pattern.findall(intent))
        keywords.update(self.abbreviation_pattern.findall(intent))

        return keywords

    def _generate_domain_keywords(self, intent: str, depth: int) -> Set[str]:
        """Generate domain-specific keyword expansions"""
        keywords = set()
        intent_lower = intent.lower()

        # Action-based expansions
        for action, synonyms in self.ACTION_PATTERNS.items():
            if action in intent_lower:
                keywords.update(synonyms[:depth])

        # Context-aware expansions
        if any(term in intent_lower for term in ['conversation', 'chat', 'talk']):
            keywords.update(['message', 'dialogue', 'transcript', 'session', 'interaction'][:depth])

        if any(term in intent_lower for term in ['project', 'build', 'develop']):
            keywords.update(['implementation', 'feature', 'module', 'component', 'service'][:depth])

        if any(term in intent_lower for term in ['error', 'issue', 'problem']):
            keywords.update(['bug', 'fault', 'exception', 'failure', 'crash'][:depth])

        if any(term in intent_lower for term in ['config', 'setup', 'install']):
            keywords.update(['configuration', 'initialization', 'deployment', 'environment'][:depth])

        return keywords

    def _generate_semantic_variations(self, intent: str) -> Set[str]:
        """Generate semantic variations of terms"""
        keywords = set()
        intent_lower = intent.lower()

        # Apply semantic mappings
        for base_term, variations in self.SEMANTIC_MAPS.items():
            if base_term in intent_lower:
                keywords.update(variations)

        # Technical context variations
        if 'cli' in intent_lower:
            keywords.update(['command', 'terminal', 'shell', 'console', 'interface'])

        if 'json' in intent_lower:
            keywords.update(['jsonl', 'data', 'format', 'structure', 'payload'])

        if 'uuid' in intent_lower:
            keywords.update(['identifier', 'id', 'key', 'reference', 'unique'])

        return keywords

    def _determine_routing(self, intent: str) -> Dict[str, Any]:
        """Determine optimal search routing strategy"""
        intent_lower = intent.lower()

        # Conversation-focused
        if re.search(r'\b(conversation|chat|discuss|talk|dialogue)\b', intent_lower):
            return {
                "strategy": "conversation_focused",
                "primary_source": "conversations",
                "weight_messages": 0.8,
                "weight_metadata": 0.2,
                "boost_terms": ["message", "chat", "text", "dialogue"]
            }

        # Project-focused
        if re.search(r'\b(project|documentation|docs|implement|build)\b', intent_lower):
            return {
                "strategy": "project_focused",
                "primary_source": "projects",
                "weight_docs": 0.7,
                "weight_description": 0.3,
                "boost_terms": ["docs", "content", "description", "implementation"]
            }

        # Technical-focused
        if re.search(r'\b(code|technical|implementation|api|config)\b', intent_lower):
            return {
                "strategy": "technical_focused",
                "primary_source": "both",
                "boost_technical_terms": True,
                "boost_terms": ["code", "implementation", "technical", "config"]
            }

        # User-focused
        if re.search(r'\b(user|person|author|creator)\b', intent_lower):
            return {
                "strategy": "user_focused",
                "primary_source": "users",
                "boost_terms": ["name", "email", "user", "creator"]
            }

        # Default balanced
        return self._get_default_routing()

    def _get_default_routing(self) -> Dict[str, Any]:
        """Get default balanced routing strategy"""
        return {
            "strategy": "balanced",
            "primary_source": "all",
            "weight_all": 0.5,
            "boost_terms": []
        }


# Convenience function for backward compatibility
def enhance_search_intent(intent: str, depth: int = 3) -> List[str]:
    """
    Enhance search intent and return keyword list.

    This is a simplified interface that returns just the keywords
    for easy integration with existing code.
    """
    enhancer = IntentEnhancer()
    result = enhancer.enhance(intent, depth)
    return result["enhanced_keywords"]


# Export main class and function
__all__ = ['IntentEnhancer', 'enhance_search_intent']