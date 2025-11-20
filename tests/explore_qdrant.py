#!/usr/bin/env python3
"""
Qdrant Data Structure Explorer
Purpose: Understand the actual payload structure in claude_sessions collection
"""

import json
import requests
from typing import Dict, List, Any
from datetime import datetime

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "claude_sessions"

def explore_qdrant_structure():
    """Explore and document Qdrant data structure"""

    print("=" * 80)
    print("QDRANT DATA STRUCTURE EXPLORATION REPORT")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)

    # 1. Get collection info
    print("\n[1] COLLECTION INFORMATION")
    print("-" * 40)

    collection_url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}"
    response = requests.get(collection_url)

    if response.status_code == 200:
        collection_info = response.json()
        print(f"Collection: {COLLECTION_NAME}")
        print(f"Status: {collection_info.get('status', 'Unknown')}")

        if 'result' in collection_info:
            result = collection_info['result']
            print(f"Points Count: {result.get('points_count', 0)}")
            print(f"Vectors Count: {result.get('vectors_count', 0)}")

            # Vector configuration
            if 'config' in result:
                config = result['config']
                params = config.get('params', {})
                print(f"Vector Size: {params.get('vectors', {}).get('size', 'Unknown')}")
                print(f"Distance Metric: {params.get('vectors', {}).get('distance', 'Unknown')}")
    else:
        print(f"ERROR: Could not fetch collection info: {response.status_code}")
        return

    # 2. Fetch sample points
    print("\n[2] SAMPLE POINTS EXPLORATION")
    print("-" * 40)

    # Query for 3 sample points
    scroll_url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/scroll"
    scroll_payload = {
        "limit": 3,
        "with_payload": True,
        "with_vector": False  # Don't need vectors for structure exploration
    }

    response = requests.post(scroll_url, json=scroll_payload)

    if response.status_code != 200:
        print(f"ERROR: Could not fetch points: {response.status_code}")
        print(f"Response: {response.text}")
        return

    data = response.json()
    points = data.get('result', {}).get('points', [])

    if not points:
        print("WARNING: No points found in collection!")
        return

    print(f"Found {len(points)} sample points\n")

    # 3. Analyze payload structure
    print("[3] PAYLOAD STRUCTURE ANALYSIS")
    print("-" * 40)

    # Collect all unique fields across samples
    all_fields = set()
    field_types = {}
    field_samples = {}

    for i, point in enumerate(points, 1):
        print(f"\nSample Point {i}:")
        print(f"  ID: {point.get('id', 'Unknown')}")

        payload = point.get('payload', {})

        if not payload:
            print("  WARNING: Empty payload!")
            continue

        print(f"  Payload Fields ({len(payload)}):")

        for field, value in payload.items():
            all_fields.add(field)

            # Track field types
            field_type = type(value).__name__
            if field not in field_types:
                field_types[field] = set()
            field_types[field].add(field_type)

            # Store sample values
            if field not in field_samples:
                field_samples[field] = []

            # Truncate long values for display
            display_value = str(value)
            if len(display_value) > 100:
                display_value = display_value[:100] + "..."

            field_samples[field].append(display_value)
            print(f"    - {field}: ({field_type}) {display_value}")

    # 4. Field Summary
    print("\n[4] FIELD SUMMARY")
    print("-" * 40)
    print(f"Total Unique Fields: {len(all_fields)}")
    print("\nField Inventory:")

    for field in sorted(all_fields):
        types = ', '.join(field_types.get(field, ['Unknown']))
        print(f"  - {field}: {types}")

    # 5. Expected vs Actual Fields
    print("\n[5] EXPECTED VS ACTUAL FIELDS")
    print("-" * 40)

    # Fields that riff-cli expects (based on code inspection)
    expected_fields = {
        'session_id',
        'content_preview',
        'working_directory',
        'timestamp',
        'commands',
        'files_edited'
    }

    print("Expected Fields (from riff code):")
    for field in sorted(expected_fields):
        status = "✓ FOUND" if field in all_fields else "✗ MISSING"
        print(f"  - {field}: {status}")

    print("\nActual Fields (not expected):")
    unexpected = all_fields - expected_fields
    for field in sorted(unexpected):
        print(f"  - {field}")

    # 6. Search compatibility check
    print("\n[6] SEARCH COMPATIBILITY ANALYSIS")
    print("-" * 40)

    critical_missing = expected_fields - all_fields
    if critical_missing:
        print("CRITICAL: Missing expected fields!")
        print("This is likely why search returns no results.")
        print(f"Missing fields: {', '.join(critical_missing)}")
    else:
        print("All expected fields present.")

    # 7. Sample full payload for reference
    print("\n[7] FULL SAMPLE PAYLOAD (for test fixtures)")
    print("-" * 40)

    if points:
        sample_point = points[0]
        print("Complete payload structure (first point):")
        print(json.dumps(sample_point['payload'], indent=2, default=str))

    # 8. Recommendations
    print("\n[8] RECOMMENDATIONS")
    print("-" * 40)

    if critical_missing:
        print("1. IMMEDIATE FIX NEEDED:")
        print("   - Update QdrantSearcher to use actual field names")
        print("   - Map expected fields to actual payload fields")
        print("")

    print("2. Test Strategy Implications:")
    print("   - Create fixtures using actual payload structure")
    print("   - Mock Qdrant responses with real field names")
    print("   - Test field mapping/transformation logic")

    print("\n" + "=" * 80)
    print("END OF EXPLORATION REPORT")
    print("=" * 80)

    # Return structured data for further processing
    return {
        'collection_info': collection_info if 'collection_info' in locals() else {},
        'sample_points': points,
        'all_fields': list(all_fields),
        'field_types': {k: list(v) for k, v in field_types.items()},
        'expected_fields': list(expected_fields),
        'missing_fields': list(critical_missing) if 'critical_missing' in locals() else []
    }

if __name__ == "__main__":
    try:
        results = explore_qdrant_structure()

        # Save results to JSON for test fixture creation
        if results:
            output_file = "qdrant_exploration_results.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n✓ Results saved to: {output_file}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()