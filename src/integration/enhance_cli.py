#!/usr/bin/env python3
"""
CLI wrapper for IntentEnhancer - Rust→Python bridge for nabi scan query enhancement.

This script provides a JSON stdin/stdout interface for the IntentEnhancer module,
allowing Rust code to enhance search queries via subprocess communication.

Protocol:
    Input (stdin):  {"query": "search term", "context": "docs"}
    Output (stdout): {"enhanced_keywords": ["word1", "word2", ...], "original_query": "..."}
    Errors (stderr): Human-readable error messages

Usage:
    echo '{"query": "federation events", "context": "docs"}' | python enhance_cli.py
    uv run enhance_cli.py < request.json
"""

import json
import sys
from typing import Dict, Any

try:
    from intent_enhancer_module import IntentEnhancer
except ImportError:
    # Handle both standalone and package execution
    from .intent_enhancer_module import IntentEnhancer


def enhance_query_cli() -> int:
    """
    Main CLI entry point for query enhancement.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Read JSON request from stdin
        request_data = sys.stdin.read()
        if not request_data:
            print(json.dumps({
                "error": "No input provided",
                "enhanced_keywords": [],
                "original_query": ""
            }))
            return 1

        # Parse request
        try:
            request: Dict[str, Any] = json.loads(request_data)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "error": f"Invalid JSON input: {e}",
                "enhanced_keywords": [],
                "original_query": ""
            }))
            return 1

        # Extract query
        query = request.get("query", "")
        if not query:
            print(json.dumps({
                "error": "Missing 'query' field in request",
                "enhanced_keywords": [],
                "original_query": ""
            }))
            return 1

        # Initialize enhancer with minimal NLP (fast startup)
        # Disable stemming for speed unless explicitly requested
        enhancer = IntentEnhancer(
            enable_stemming=request.get("enable_stemming", False),
            auto_download_nltk=False
        )

        # Enhance the query
        depth = request.get("depth", 3)
        result = enhancer.enhance(query, depth=depth)

        # Build response
        response = {
            "enhanced_keywords": result["enhanced_keywords"],
            "original_query": query,
            "keyword_count": result["keyword_count"],
            "routing": result.get("routing", {})
        }

        # Output JSON to stdout
        print(json.dumps(response))
        return 0

    except Exception as e:
        # Log error to stderr for debugging
        print(f"Error: {e}", file=sys.stderr)

        # Return minimal valid JSON on stdout
        print(json.dumps({
            "error": str(e),
            "enhanced_keywords": [],
            "original_query": request.get("query", "") if 'request' in locals() else ""
        }))
        return 1


if __name__ == "__main__":
    sys.exit(enhance_query_cli())
