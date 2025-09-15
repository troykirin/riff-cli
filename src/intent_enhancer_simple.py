#!/usr/bin/env python3
"""
Simplified intent-driven keyword enhancement for riff-claude
Pattern-based keyword expansion without external dependencies
"""

import json
import re
import sys
from typing import List, Dict, Any

def enhance_search_intent(original_intent: str, depth: int = 3) -> List[str]:
    """
    Enhance search keywords using pattern matching and domain knowledge
    
    Args:
        original_intent: Original search intent from user
        depth: Enhancement depth (affects number of keyword expansions)
        
    Returns:
        List of enhanced keywords for search
    """
    # Start with original intent
    keywords = [original_intent]
    
    # Extract base keywords using pattern matching
    pattern_keywords = extract_pattern_keywords(original_intent)
    keywords.extend(pattern_keywords)
    
    # Generate domain-specific expansions
    domain_keywords = generate_domain_keywords(original_intent, depth)
    keywords.extend(domain_keywords)
    
    # Extract semantic variations
    semantic_keywords = generate_semantic_variations(original_intent)
    keywords.extend(semantic_keywords)
    
    # Remove duplicates and return
    return list(set(filter(None, keywords)))

def extract_pattern_keywords(intent: str) -> List[str]:
    """Extract keywords using pattern matching"""
    intent_lower = intent.lower()
    keywords = []
    
    # Technical domain patterns with comprehensive expansions
    domain_patterns = {
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
    
    for term, expansions in domain_patterns.items():
        if term in intent_lower:
            keywords.extend(expansions)
    
    # Extract quoted phrases
    quoted_phrases = re.findall(r'"([^"]*)"', intent)
    keywords.extend(quoted_phrases)
    
    # Extract camelCase and kebab-case terms
    tech_terms = re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b|\b[a-z]+-[a-z-]+\b', intent)
    keywords.extend(tech_terms)
    
    # Extract technical abbreviations
    abbreviations = re.findall(r'\b[A-Z]{2,}\b', intent)
    keywords.extend(abbreviations)
    
    return keywords

def generate_domain_keywords(intent: str, depth: int) -> List[str]:
    """Generate domain-specific keyword expansions based on context"""
    intent_lower = intent.lower()
    keywords = []
    
    # Action-based expansions
    action_patterns = {
        'find': ['search', 'locate', 'discover', 'identify', 'retrieve', 'lookup'],
        'search': ['find', 'query', 'scan', 'browse', 'explore', 'investigate'],
        'discuss': ['talk', 'conversation', 'dialogue', 'chat', 'communication', 'exchange'],
        'implement': ['build', 'create', 'develop', 'construct', 'design', 'code'],
        'configure': ['setup', 'initialize', 'customize', 'adjust', 'modify', 'tune'],
        'integrate': ['connect', 'link', 'bridge', 'sync', 'merge', 'combine'],
        'debug': ['troubleshoot', 'diagnose', 'fix', 'resolve', 'investigate', 'analyze']
    }
    
    for action, synonyms in action_patterns.items():
        if action in intent_lower:
            keywords.extend(synonyms[:depth])  # Limit by depth
    
    # Context-aware technical expansions
    if any(term in intent_lower for term in ['conversation', 'chat', 'talk']):
        keywords.extend(['message', 'dialogue', 'transcript', 'session', 'interaction'])
        
    if any(term in intent_lower for term in ['project', 'build', 'develop']):
        keywords.extend(['implementation', 'feature', 'module', 'component', 'service'])
        
    if any(term in intent_lower for term in ['error', 'issue', 'problem']):
        keywords.extend(['bug', 'fault', 'exception', 'failure', 'crash'])
        
    if any(term in intent_lower for term in ['config', 'setup', 'install']):
        keywords.extend(['configuration', 'initialization', 'deployment', 'environment'])
    
    return keywords

def generate_semantic_variations(intent: str) -> List[str]:
    """Generate semantic variations and related terms"""
    intent_lower = intent.lower()
    keywords = []
    
    # Semantic relationship mappings
    semantic_maps = {
        'agent': ['bot', 'assistant', 'worker', 'service', 'process'],
        'system': ['platform', 'framework', 'infrastructure', 'architecture'],
        'data': ['information', 'content', 'payload', 'dataset', 'record'],
        'process': ['workflow', 'pipeline', 'procedure', 'operation', 'task'],
        'network': ['connection', 'link', 'channel', 'communication', 'protocol'],
        'interface': ['api', 'endpoint', 'contract', 'specification', 'definition'],
        'state': ['status', 'condition', 'mode', 'phase', 'situation'],
        'event': ['message', 'signal', 'notification', 'trigger', 'callback']
    }
    
    for base_term, variations in semantic_maps.items():
        if base_term in intent_lower:
            keywords.extend(variations)
    
    # Technical context variations
    if 'cli' in intent_lower:
        keywords.extend(['command', 'terminal', 'shell', 'console', 'interface'])
        
    if 'json' in intent_lower:
        keywords.extend(['jsonl', 'data', 'format', 'structure', 'payload'])
        
    if 'uuid' in intent_lower:
        keywords.extend(['identifier', 'id', 'key', 'reference', 'unique'])
    
    return keywords

def route_search_intent(intent: str) -> Dict[str, Any]:
    """
    Route search intent to appropriate search strategy
    """
    intent_lower = intent.lower()
    
    # Conversation search patterns
    if re.search(r'\b(conversation|chat|discuss|talk|dialogue)\b', intent_lower):
        return {
            "strategy": "conversation_focused",
            "primary_source": "conversations",
            "weight_messages": 0.8,
            "weight_metadata": 0.2,
            "boost_terms": ["message", "chat", "text", "dialogue"]
        }
    
    # Project/documentation search patterns  
    if re.search(r'\b(project|documentation|docs|implement|build)\b', intent_lower):
        return {
            "strategy": "project_focused", 
            "primary_source": "projects",
            "weight_docs": 0.7,
            "weight_description": 0.3,
            "boost_terms": ["docs", "content", "description", "implementation"]
        }
    
    # Technical/code search patterns
    if re.search(r'\b(code|technical|implementation|api|config)\b', intent_lower):
        return {
            "strategy": "technical_focused",
            "primary_source": "both",
            "boost_technical_terms": True,
            "boost_terms": ["code", "implementation", "technical", "config"]
        }
    
    # User/identity search patterns
    if re.search(r'\b(user|person|author|creator)\b', intent_lower):
        return {
            "strategy": "user_focused",
            "primary_source": "users",
            "boost_terms": ["name", "email", "user", "creator"]
        }
    
    # Default balanced search
    return {
        "strategy": "balanced",
        "primary_source": "all",
        "weight_all": 0.5,
        "boost_terms": []
    }

def main():
    """CLI interface for intent enhancement"""
    if len(sys.argv) < 2:
        print("Usage: python intent_enhancer_simple.py 'search intent' [depth]")
        sys.exit(1)
    
    intent = sys.argv[1]
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    keywords = enhance_search_intent(intent, depth)
    routing = route_search_intent(intent)
    
    # Output as JSON for nushell consumption
    result = {
        "original_intent": intent,
        "enhanced_keywords": keywords,
        "routing": routing,
        "keyword_count": len(keywords)
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()