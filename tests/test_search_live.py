#!/usr/bin/env python3
"""
Live Qdrant Search Testing
Purpose: Test if search actually works with the real Qdrant instance
"""

import sys
sys.path.insert(0, '/Users/tryk/nabia/tools/riff-cli/src')

from riff.search.qdrant import QdrantSearcher
from qdrant_client import QdrantClient

def test_search_functionality():
    """Test various search scenarios against live Qdrant"""

    print("=" * 80)
    print("LIVE QDRANT SEARCH TESTING")
    print("=" * 80)

    # Initialize searcher
    searcher = QdrantSearcher()

    # Test 1: Check connection
    print("\n[TEST 1] Connection Check")
    print("-" * 40)
    is_available = searcher.is_available()
    print(f"Qdrant Available: {is_available}")

    if not is_available:
        print("ERROR: Cannot connect to Qdrant!")
        return

    # Test 2: Basic search
    print("\n[TEST 2] Basic Search")
    print("-" * 40)

    test_queries = [
        "TodoWrite",
        "memchain",
        "hooks",
        "federation",
        "python"
    ]

    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        try:
            results = searcher.search(query, limit=3)
            if results:
                print(f"  ✓ Found {len(results)} results")
                for i, r in enumerate(results, 1):
                    print(f"    {i}. Score: {r.score:.3f}")
                    print(f"       Dir: {r.working_directory}")
                    preview = r.content_preview[:50] if r.content_preview else "[empty]"
                    print(f"       Preview: {preview}")
            else:
                print(f"  ✗ No results found")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Test 3: Search by UUID
    print("\n[TEST 3] Search by UUID")
    print("-" * 40)

    # Use a UUID we know exists from exploration
    test_uuid = "b7992938-755e-45e3-b352-8edff4c4fdb9"
    print(f"Searching for UUID: {test_uuid}")

    try:
        result = searcher.search_by_uuid(test_uuid)
        if result:
            print(f"  ✓ Found session")
            print(f"    Dir: {result.working_directory}")
            print(f"    File: {result.file_path}")
        else:
            print(f"  ✗ UUID not found")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test 4: Check vector dimensions
    print("\n[TEST 4] Vector Dimension Check")
    print("-" * 40)

    # Encode a test query to check dimensions
    test_embedding = searcher.model.encode("test query")
    print(f"Model output dimensions: {len(test_embedding)}")
    print(f"Expected dimensions (from Qdrant): 384")

    if len(test_embedding) == 384:
        print("  ✓ Vector dimensions match!")
    else:
        print("  ✗ DIMENSION MISMATCH - This is the problem!")

    # Test 5: Direct Qdrant query
    print("\n[TEST 5] Direct Qdrant Query (bypass wrapper)")
    print("-" * 40)

    client = QdrantClient(url="http://localhost:6333")

    # Try a direct scroll to get some points
    try:
        response = client.scroll(
            collection_name="claude_sessions",
            limit=5,
            with_payload=True,
            with_vector=False
        )

        points = response[0] if response else []
        print(f"Direct scroll found: {len(points)} points")

        # Now try a direct search
        test_embedding = searcher.model.encode("test").tolist()
        search_response = client.search(
            collection_name="claude_sessions",
            query_vector=test_embedding,
            limit=5
        )

        print(f"Direct search found: {len(search_response)} results")

        if search_response:
            for i, r in enumerate(search_response[:3], 1):
                print(f"  {i}. Score: {r.score:.3f}")
                print(f"     Session: {r.payload.get('session_id', 'N/A')}")

    except Exception as e:
        print(f"  ERROR in direct query: {e}")

    print("\n" + "=" * 80)
    print("END OF TESTING")
    print("=" * 80)

if __name__ == "__main__":
    test_search_functionality()