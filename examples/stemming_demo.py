#!/usr/bin/env python3
"""
Demonstration of NLP stemming integration with Intent Enhancer.

This script shows the practical benefits of adding NLP stemming to
the search keyword expansion system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integration.intent_enhancer_module import IntentEnhancer
from integration.nlp_stemmer import NLPStemmer


def demo_basic_stemming() -> None:
    """Demonstrate basic NLP stemming."""
    print("=" * 70)
    print("DEMO 1: Basic NLP Stemming")
    print("=" * 70)

    stemmer = NLPStemmer()

    test_words = [
        "running", "federation", "agents", "implementing",
        "configuration", "development", "happiness"
    ]

    print("\nStemming individual words:")
    for word in test_words:
        porter = stemmer.stem(word, "porter")
        snowball = stemmer.stem(word, "snowball")
        print(f"  {word:15s} -> Porter: {porter:12s} Snowball: {snowball}")


def demo_query_stemming() -> None:
    """Demonstrate query stemming with variants."""
    print("\n" + "=" * 70)
    print("DEMO 2: Query Stemming (Generates Variants)")
    print("=" * 70)

    stemmer = NLPStemmer()

    queries = [
        "running federation agents",
        "implementing authentication handlers",
        "configuring development environment"
    ]

    for query in queries:
        variants = stemmer.stem_query(query)
        print(f"\nQuery: '{query}'")
        print(f"Variants ({len(variants)}): {variants}")


def demo_intent_enhancement() -> None:
    """Demonstrate Intent Enhancer with and without stemming."""
    print("\n" + "=" * 70)
    print("DEMO 3: Intent Enhancement (With vs Without Stemming)")
    print("=" * 70)

    # Without stemming
    enhancer_no_stem = IntentEnhancer(enable_stemming=False)
    result_no_stem = enhancer_no_stem.enhance(
        "find conversations about running agents",
        depth=3
    )

    # With stemming
    enhancer_with_stem = IntentEnhancer(enable_stemming=True)
    result_with_stem = enhancer_with_stem.enhance(
        "find conversations about running agents",
        depth=3
    )

    print("\n📝 Query: 'find conversations about running agents'")
    print("\n❌ WITHOUT Stemming:")
    print(f"   Keywords ({result_no_stem['keyword_count']}): {result_no_stem['enhanced_keywords'][:10]}...")

    print("\n✅ WITH Stemming:")
    print(f"   Keywords ({result_with_stem['keyword_count']}): {result_with_stem['enhanced_keywords'][:15]}...")

    improvement = result_with_stem['keyword_count'] - result_no_stem['keyword_count']
    print(f"\n📊 Improvement: +{improvement} keywords ({improvement / result_no_stem['keyword_count'] * 100:.1f}% increase)")


def demo_stemming_methods() -> None:
    """Compare different stemming methods."""
    print("\n" + "=" * 70)
    print("DEMO 4: Comparing Stemming Methods")
    print("=" * 70)

    stemmer = NLPStemmer()

    test_words = ["running", "better", "generalization", "computing"]

    print("\nComparing Porter vs Snowball vs Lemmatizer:")
    print(f"{'Word':<15s} {'Porter':<12s} {'Snowball':<12s} {'Lemmatizer':<12s}")
    print("-" * 55)

    for word in test_words:
        porter = stemmer.stem(word, "porter")
        snowball = stemmer.stem(word, "snowball")
        lemma = stemmer.stem(word, "lemmatizer")
        print(f"{word:<15s} {porter:<12s} {snowball:<12s} {lemma:<12s}")


def demo_real_world_scenario() -> None:
    """Demonstrate real-world search scenario."""
    print("\n" + "=" * 70)
    print("DEMO 5: Real-World Search Scenario")
    print("=" * 70)

    enhancer = IntentEnhancer(enable_stemming=True)

    scenarios = [
        ("User asks:", "find implementations of Linear integration"),
        ("Developer searches:", "debugging authentication errors in production"),
        ("PM queries:", "discussions about project planning and milestones")
    ]

    for label, query in scenarios:
        result = enhancer.enhance(query, depth=4)
        print(f"\n{label} '{query}'")
        print(f"  Strategy: {result['routing']['strategy']}")
        print(f"  Keywords ({result['keyword_count']}): {', '.join(result['enhanced_keywords'][:12])}...")


def demo_capabilities() -> None:
    """Show stemmer capabilities."""
    print("\n" + "=" * 70)
    print("DEMO 6: Stemmer Capabilities")
    print("=" * 70)

    stemmer = NLPStemmer()
    caps = stemmer.get_capabilities()

    print("\n🔍 Stemmer Capabilities:")
    print(f"   NLTK Available: {'✅ Yes' if caps['has_nltk'] else '❌ No'}")
    print(f"   Porter Stemmer: {'✅ Yes' if caps['has_porter'] else '❌ No'}")
    print(f"   Snowball Stemmer: {'✅ Yes' if caps['has_snowball'] else '❌ No'}")
    print(f"   WordNet Lemmatizer: {'✅ Yes' if caps['has_wordnet'] else '❌ No'}")

    if caps['nltk_data_path']:
        print(f"   NLTK Data Path: {caps['nltk_data_path']}")

    enhancer = IntentEnhancer(enable_stemming=True)
    info = enhancer.get_stemming_info()

    print("\n🎯 Intent Enhancer Stemming:")
    print(f"   Enabled: {'✅ Yes' if info['enabled'] else '❌ No'}")
    if info['enabled']:
        print(f"   Method: {info['method']}")


def main() -> None:
    """Run all demonstrations."""
    print("\n🚀 NLP Stemming Integration Demo")
    print("=" * 70)

    try:
        demo_basic_stemming()
        demo_query_stemming()
        demo_intent_enhancement()
        demo_stemming_methods()
        demo_real_world_scenario()
        demo_capabilities()

        print("\n" + "=" * 70)
        print("✅ All demonstrations completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
