#!/usr/bin/env python3
"""
Intent-driven keyword enhancement for riff-claude
Integrates with oauth-mcp-proxy intent routing and Grok for recursive search enhancement
"""

import json
import re
import sys
import asyncio
import aiohttp
from typing import List, Dict, Any

class IntentEnhancer:
    """Recursive intent-driven keyword enhancement system"""
    
    def __init__(self, mcp_proxy_url: str = "http://localhost:8002"):
        self.mcp_proxy_url = mcp_proxy_url
        self.max_depth = 5
        
    async def enhance_search_intent(self, original_intent: str, depth: int = 0) -> List[str]:
        """
        Recursively enhance search keywords using Grok and intent analysis
        
        Args:
            original_intent: Original search intent from user
            depth: Current recursion depth (0-based)
            
        Returns:
            List of enhanced keywords for search
        """
        if depth >= self.max_depth:
            return [original_intent]
            
        # Start with original intent
        keywords = [original_intent]
        
        # Extract base keywords using pattern matching
        pattern_keywords = self._extract_pattern_keywords(original_intent)
        keywords.extend(pattern_keywords)
        
        # Generate contextual keywords using Grok if available
        if depth < 2:  # Only use AI for first 2 iterations to control costs
            ai_keywords = await self._generate_ai_keywords(original_intent, depth)
            keywords.extend(ai_keywords)
        
        # Generate domain-specific expansions
        domain_keywords = self._generate_domain_keywords(original_intent)
        keywords.extend(domain_keywords)
        
        # Remove duplicates and return
        return list(set(keywords))
    
    def _extract_pattern_keywords(self, intent: str) -> List[str]:
        """Extract keywords using pattern matching"""
        intent_lower = intent.lower()
        keywords = []
        
        # Technical domain patterns
        domain_patterns = {
            'nabia': ['federation', 'memchain', 'orchestration', 'agent', 'coordination', 'protocol'],
            'claude': ['assistant', 'conversation', 'chat', 'ai', 'llm', 'dialogue'],
            'linear': ['issue', 'project', 'task', 'ticket', 'workflow', 'development'],
            'federation': ['agent', 'coordination', 'protocol', 'handoff', 'orchestration', 'distributed'],
            'memory': ['storage', 'retrieval', 'context', 'persistent', 'ephemeral', 'knowledge'],
            'search': ['query', 'find', 'lookup', 'discover', 'filter', 'match'],
            'integration': ['api', 'webhook', 'connection', 'sync', 'bridge', 'interface'],
            'architecture': ['design', 'pattern', 'structure', 'framework', 'system', 'blueprint']
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
        
        return keywords
    
    async def _generate_ai_keywords(self, intent: str, iteration: int) -> List[str]:
        """Generate keywords using AI (Grok) via MCP proxy"""
        try:
            prompt = self._create_keyword_prompt(intent, iteration)
            
            async with aiohttp.ClientSession() as session:
                # Use Grok via MCP proxy for keyword generation
                payload = {
                    "text": prompt,
                    "execute": False
                }
                
                async with session.post(
                    f"{self.mcp_proxy_url}/intents/route",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'arguments' in result and 'prompt' in result['arguments']:
                            # Extract keywords from Grok response
                            return self._parse_ai_keywords(result['arguments']['prompt'])
                    
        except Exception as e:
            print(f"Warning: AI keyword generation failed: {e}", file=sys.stderr)
            
        return []
    
    def _create_keyword_prompt(self, intent: str, iteration: int) -> str:
        """Create a prompt for AI keyword generation"""
        base_prompt = f"""
        Given this search intent: "{intent}"
        
        Generate 5-10 related keywords/phrases that might appear in:
        - Claude conversation transcripts and AI assistant dialogues
        - Technical discussions about AI agents and automation
        - Software development project documentation
        - Federation and orchestration system logs
        
        Consider:
        - Synonyms and alternative phrasings
        - Technical terminology and jargon
        - Conversational language patterns
        - Context-specific abbreviations
        
        Iteration: {iteration} (focus on {'broader context' if iteration == 0 else 'specific technical terms'})
        
        Return only the keywords, separated by commas.
        """
        
        return base_prompt.strip()
    
    def _parse_ai_keywords(self, ai_response: str) -> List[str]:
        """Parse keywords from AI response"""
        # Extract comma-separated keywords
        keywords = []
        
        # Split by common separators
        for separator in [',', ';', '\n']:
            if separator in ai_response:
                parts = ai_response.split(separator)
                for part in parts:
                    cleaned = part.strip().strip('"\'')
                    if cleaned and len(cleaned) > 2:
                        keywords.append(cleaned)
                break
        
        # If no separators found, extract words
        if not keywords:
            words = re.findall(r'\b[a-zA-Z-]{3,}\b', ai_response)
            keywords.extend(words[:10])  # Limit to 10 words
        
        return keywords[:10]  # Return max 10 keywords
    
    def _generate_domain_keywords(self, intent: str) -> List[str]:
        """Generate domain-specific keyword expansions"""
        intent_lower = intent.lower()
        keywords = []
        
        # Context-aware expansions
        if any(term in intent_lower for term in ['find', 'search', 'look']):
            keywords.extend(['discover', 'locate', 'identify', 'retrieve'])
            
        if any(term in intent_lower for term in ['discuss', 'talk', 'conversation']):
            keywords.extend(['dialogue', 'chat', 'communication', 'exchange'])
            
        if any(term in intent_lower for term in ['problem', 'issue', 'bug']):
            keywords.extend(['error', 'fault', 'defect', 'troubleshoot'])
            
        if any(term in intent_lower for term in ['implement', 'build', 'create']):
            keywords.extend(['develop', 'construct', 'design', 'code'])
        
        return keywords

def route_search_intent(intent: str) -> Dict[str, Any]:
    """
    Route search intent to appropriate search strategy
    Similar to oauth-mcp-proxy intent routing but for search
    """
    intent_lower = intent.lower()
    
    # Conversation search patterns
    if re.search(r'\b(conversation|chat|discuss|talk)\b', intent_lower):
        return {
            "strategy": "conversation_focused",
            "primary_source": "conversations",
            "weight_messages": 0.8,
            "weight_metadata": 0.2
        }
    
    # Project/documentation search patterns  
    if re.search(r'\b(project|documentation|docs|implement)\b', intent_lower):
        return {
            "strategy": "project_focused", 
            "primary_source": "projects",
            "weight_docs": 0.7,
            "weight_description": 0.3
        }
    
    # Technical/code search patterns
    if re.search(r'\b(code|technical|implementation|api)\b', intent_lower):
        return {
            "strategy": "technical_focused",
            "primary_source": "both",
            "boost_technical_terms": True
        }
    
    # Default balanced search
    return {
        "strategy": "balanced",
        "primary_source": "all",
        "weight_all": 0.5
    }

async def main():
    """CLI interface for intent enhancement"""
    if len(sys.argv) < 2:
        print("Usage: python intent_enhancer.py 'search intent' [depth]")
        sys.exit(1)
    
    intent = sys.argv[1]
    _depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    enhancer = IntentEnhancer()
    keywords = await enhancer.enhance_search_intent(intent, 0)
    
    # Output as JSON for nushell consumption
    result = {
        "original_intent": intent,
        "enhanced_keywords": keywords,
        "routing": route_search_intent(intent)
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())