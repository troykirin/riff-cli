#!/usr/bin/env python3
"""
CLI wrapper for query enhancement via stdin/stdout JSON interface.

This script provides a command-line interface to the IntentEnhancer
for integration with external tools (like nabi scan). It reads JSON
from stdin and writes enhanced results to stdout.

Input JSON Format:
{
    "query": "your search query",
    "depth": 3,  # optional, default: 3
    "enable_stemming": true,  # optional, default: true
    "stemming_method": "porter"  # optional, default: "porter"
}

Output JSON Format (success):
{
    "status": "success",
    "query": "original query",
    "enhanced_keywords": ["keyword1", "keyword2", ...],
    "or_pattern": "(keyword1|keyword2|...)",
    "keyword_count": 25,
    "routing": {...},
    "stemming_info": {...}
}

Output JSON Format (error):
{
    "status": "error",
    "error": "error message",
    "query": "original query if available"
}

Exit Codes:
0 - Success
1 - Invalid JSON input
2 - Enhancement error
3 - Missing required fields
"""

import sys
import json
import warnings
from typing import Any, Dict
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from integration.intent_enhancer_module import IntentEnhancer
    HAS_ENHANCER = True
except ImportError:
    HAS_ENHANCER = False


def create_or_pattern(keywords: list[str]) -> str:
    """
    Create a ripgrep-compatible OR pattern from keywords.

    Args:
        keywords: List of keywords to combine

    Returns:
        OR pattern like "(keyword1|keyword2|keyword3)"
    """
    if not keywords:
        return ""

    # Escape special regex characters in keywords
    escaped = []
    for keyword in keywords:
        # Escape regex special chars: . * + ? ^ $ { } [ ] ( ) | \
        escaped_keyword = keyword.replace("\\", "\\\\")
        for char in ['.', '*', '+', '?', '^', '$', '{', '}', '[', ']', '(', ')', '|']:
            escaped_keyword = escaped_keyword.replace(char, f"\\{char}")
        escaped.append(escaped_keyword)

    # Join with OR operator
    return f"({('|'.join(escaped))})"


def enhance_query(
    query: str,
    depth: int = 3,
    enable_stemming: bool = True,
    stemming_method: str = "porter"
) -> Dict[str, Any]:
    """
    Enhance a query using IntentEnhancer.

    Args:
        query: Query string to enhance
        depth: Enhancement depth (1-5)
        enable_stemming: Enable NLP stemming
        stemming_method: Stemming method (porter, snowball, lemmatizer)

    Returns:
        Enhancement result dictionary

    Raises:
        RuntimeError: If enhancer not available
        ValueError: If invalid parameters
    """
    if not HAS_ENHANCER:
        raise RuntimeError("IntentEnhancer not available - import failed")

    # Validate depth
    if not 1 <= depth <= 5:
        raise ValueError(f"depth must be 1-5, got {depth}")

    # Validate stemming method
    valid_methods = ["porter", "snowball", "lemmatizer"]
    if stemming_method not in valid_methods:
        raise ValueError(
            f"stemming_method must be one of {valid_methods}, got '{stemming_method}'"
        )

    # Create enhancer
    enhancer = IntentEnhancer(
        enable_stemming=enable_stemming,
        stemming_method=stemming_method  # type: ignore
    )

    # Enhance query
    result = enhancer.enhance(query, depth=depth)

    # Get stemming info
    stemming_info = enhancer.get_stemming_info()

    # Create OR pattern for ripgrep
    or_pattern = create_or_pattern(result["enhanced_keywords"])

    return {
        "status": "success",
        "query": query,
        "enhanced_keywords": result["enhanced_keywords"],
        "or_pattern": or_pattern,
        "keyword_count": result["keyword_count"],
        "routing": result["routing"],
        "stemming_info": stemming_info
    }


def main() -> int:
    """
    Main CLI entry point.

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    # Suppress warnings for cleaner output
    warnings.filterwarnings("ignore")

    try:
        # Read JSON from stdin
        input_data = sys.stdin.read()

        if not input_data.strip():
            error_result = {
                "status": "error",
                "error": "No input received on stdin"
            }
            json.dump(error_result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 1

        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            error_result = {
                "status": "error",
                "error": f"Invalid JSON input: {e}"
            }
            json.dump(error_result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 1

        # Validate required fields
        if not isinstance(data, dict):
            error_result = {
                "status": "error",
                "error": "Input must be a JSON object"
            }
            json.dump(error_result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 3

        if "query" not in data:
            error_result = {
                "status": "error",
                "error": "Missing required field: 'query'"
            }
            json.dump(error_result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 3

        # Extract parameters
        query = data["query"]
        depth = data.get("depth", 3)
        enable_stemming = data.get("enable_stemming", True)
        stemming_method = data.get("stemming_method", "porter")

        # Enhance query
        try:
            result = enhance_query(
                query=query,
                depth=depth,
                enable_stemming=enable_stemming,
                stemming_method=stemming_method
            )

            # Write result to stdout
            json.dump(result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 0

        except (RuntimeError, ValueError) as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "query": query
            }
            json.dump(error_result, sys.stdout, indent=2)
            print(file=sys.stdout)  # Newline
            return 2

    except Exception as e:
        # Catch-all for unexpected errors
        error_result = {
            "status": "error",
            "error": f"Unexpected error: {e}"
        }
        json.dump(error_result, sys.stdout, indent=2)
        print(file=sys.stdout)  # Newline
        return 2


if __name__ == "__main__":
    sys.exit(main())
