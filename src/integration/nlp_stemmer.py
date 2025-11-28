#!/usr/bin/env python3
"""
Type-safe NLP stemming module with graceful fallback.

This module provides Porter and Snowball stemming with optional WordNet
lemmatization. It includes comprehensive type annotations for Python 3.13+
and handles missing NLTK data gracefully.

Features:
- Porter stemmer for basic stemming
- Snowball stemmer for advanced multi-language support
- WordNet lemmatizer for better semantic accuracy
- Automatic NLTK data download with user control
- Graceful degradation when NLTK is unavailable
- Full type safety with TypedDict and modern type annotations
"""

from typing import Protocol, TypedDict, final
from typing import Literal, overload
import re
import warnings


# Type definitions for structured return types
class StemResult(TypedDict):
    """Result of stemming operation with metadata."""
    original: str
    stemmed: str
    method: Literal["porter", "snowball", "lemmatizer", "fallback"]
    success: bool


class StemmerCapabilities(TypedDict):
    """Available stemmer capabilities."""
    has_nltk: bool
    has_porter: bool
    has_snowball: bool
    has_wordnet: bool
    nltk_data_path: str | None


class StemmerProtocol(Protocol):
    """Protocol for NLTK stemmer interface."""
    def stem(self, word: str) -> str:
        """Stem a word to its root form."""
        ...


class LemmatizerProtocol(Protocol):
    """Protocol for NLTK lemmatizer interface."""
    def lemmatize(self, word: str, pos: str = "n") -> str:
        """Lemmatize a word with optional part-of-speech tag."""
        ...


# Check for NLTK availability
def has_nltk_support() -> bool:
    """Check if NLTK is available."""
    try:
        import nltk  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


@final
class NLPStemmer:
    """
    Type-safe NLP stemming with multiple algorithms.

    This class provides stemming and lemmatization with graceful fallback
    when NLTK is unavailable. All methods are fully type-annotated for
    Python 3.13+ type checkers.

    Attributes:
        _porter_stemmer: Optional Porter stemmer instance
        _snowball_stemmer: Optional Snowball stemmer instance
        _lemmatizer: Optional WordNet lemmatizer instance
        _nltk_available: Whether NLTK is available
        _data_downloaded: Whether NLTK data has been downloaded
    """

    def __init__(
        self,
        auto_download: bool = False,
        language: str = "english",
        suppress_warnings: bool = True
    ) -> None:
        """
        Initialize NLP stemmer with optional auto-download.

        Args:
            auto_download: Automatically download NLTK data if missing
            language: Language for Snowball stemmer (default: "english")
            suppress_warnings: Suppress NLTK download warnings

        Note:
            If auto_download is False and NLTK data is missing, stemmer
            will fall back to simple pattern-based stemming.
        """
        self._porter_stemmer: StemmerProtocol | None = None
        self._snowball_stemmer: StemmerProtocol | None = None
        self._lemmatizer: LemmatizerProtocol | None = None
        self._nltk_available: bool = False
        self._data_downloaded: bool = False
        self._language: str = language

        if suppress_warnings:
            warnings.filterwarnings("ignore", category=UserWarning, module="nltk")

        self._initialize_stemmers(auto_download)

    def _initialize_stemmers(self, auto_download: bool) -> None:
        """Initialize NLTK stemmers if available."""
        if not has_nltk_support():
            return

        try:
            import nltk  # type: ignore  # noqa: F401
            from nltk.stem import PorterStemmer, SnowballStemmer  # type: ignore
            from nltk.stem import WordNetLemmatizer  # type: ignore

            self._nltk_available = True

            # Try to initialize stemmers
            try:
                self._porter_stemmer = PorterStemmer()
                self._snowball_stemmer = SnowballStemmer(self._language)
                self._lemmatizer = WordNetLemmatizer()
                self._data_downloaded = True
            except LookupError:
                # NLTK data not available
                if auto_download:
                    self._download_nltk_data()
                    # Retry initialization
                    try:
                        self._porter_stemmer = PorterStemmer()
                        self._snowball_stemmer = SnowballStemmer(self._language)
                        self._lemmatizer = WordNetLemmatizer()
                        self._data_downloaded = True
                    except LookupError:
                        pass  # Fall back to pattern-based stemming
        except Exception as e:
            # Log error but don't fail - fall back to pattern-based
            if not auto_download:
                warnings.warn(
                    f"NLTK initialization failed: {e}. Using fallback stemming.",
                    UserWarning
                )

    def _download_nltk_data(self) -> None:
        """Download required NLTK data packages."""
        try:
            import nltk  # type: ignore

            # Download required packages quietly
            for package in ["punkt", "wordnet", "omw-1.4", "averaged_perceptron_tagger"]:
                try:
                    nltk.download(package, quiet=True)  # type: ignore
                except Exception:
                    pass  # Continue even if some packages fail
        except Exception:
            pass  # Graceful degradation

    @overload
    def stem(
        self,
        word: str,
        method: Literal["porter"] = "porter"
    ) -> str: ...

    @overload
    def stem(
        self,
        word: str,
        method: Literal["snowball"]
    ) -> str: ...

    @overload
    def stem(
        self,
        word: str,
        method: Literal["lemmatizer"]
    ) -> str: ...

    def stem(
        self,
        word: str,
        method: Literal["porter", "snowball", "lemmatizer"] = "porter"
    ) -> str:
        """
        Stem a single word using specified method.

        Args:
            word: Word to stem
            method: Stemming method ("porter", "snowball", "lemmatizer")

        Returns:
            Stemmed word (or original if stemming unavailable)

        Examples:
            >>> stemmer = NLPStemmer()
            >>> stemmer.stem("running")
            "run"
            >>> stemmer.stem("federation")
            "feder"
        """
        if not word or not word.strip():
            return word

        word_clean = word.strip().lower()

        # Try requested method
        if method == "porter" and self._porter_stemmer:
            return self._porter_stemmer.stem(word_clean)
        elif method == "snowball" and self._snowball_stemmer:
            return self._snowball_stemmer.stem(word_clean)
        elif method == "lemmatizer" and self._lemmatizer:
            return self._lemmatizer.lemmatize(word_clean)

        # Fallback to pattern-based stemming
        return self._fallback_stem(word_clean)

    def stem_query(self, query: str) -> list[str]:
        """
        Stem all words in a query and return unique variants.

        This method tokenizes the query and generates stemmed variants
        using all available stemming methods. It returns a deduplicated
        list of all variants.

        Args:
            query: Query string to stem

        Returns:
            List of unique stemmed word variants

        Examples:
            >>> stemmer = NLPStemmer()
            >>> stemmer.stem_query("running federation")
            ["run", "running", "feder", "federation"]
        """
        if not query or not query.strip():
            return []

        # Tokenize query (simple whitespace + word boundary)
        words = self._tokenize(query)

        variants: set[str] = set(words)  # Include original words

        # Generate stemmed variants using all available methods
        for word in words:
            # Skip very short words and stop words
            if len(word) <= 2:
                continue

            # Porter stemming
            if self._porter_stemmer:
                variants.add(self.stem(word, "porter"))

            # Snowball stemming
            if self._snowball_stemmer:
                variants.add(self.stem(word, "snowball"))

            # Lemmatization
            if self._lemmatizer:
                variants.add(self.stem(word, "lemmatizer"))

            # Fallback stemming
            if not self._nltk_available:
                variants.add(self._fallback_stem(word))

        return sorted(list(variants))

    def stem_with_metadata(
        self,
        word: str,
        method: Literal["porter", "snowball", "lemmatizer"] = "porter"
    ) -> StemResult:
        """
        Stem a word and return detailed metadata.

        Args:
            word: Word to stem
            method: Stemming method to use

        Returns:
            StemResult with original, stemmed form, method, and success flag

        Examples:
            >>> stemmer = NLPStemmer()
            >>> result = stemmer.stem_with_metadata("running")
            >>> result["stemmed"]
            "run"
            >>> result["method"]
            "porter"
        """
        original = word.strip()
        stemmed = self.stem(word, method)

        # Determine actual method used
        actual_method: Literal["porter", "snowball", "lemmatizer", "fallback"]
        if method == "porter" and self._porter_stemmer:
            actual_method = "porter"
        elif method == "snowball" and self._snowball_stemmer:
            actual_method = "snowball"
        elif method == "lemmatizer" and self._lemmatizer:
            actual_method = "lemmatizer"
        else:
            actual_method = "fallback"

        return StemResult(
            original=original,
            stemmed=stemmed,
            method=actual_method,
            success=stemmed != original
        )

    def batch_stem(
        self,
        words: list[str],
        method: Literal["porter", "snowball", "lemmatizer"] = "porter"
    ) -> list[str]:
        """
        Stem multiple words efficiently.

        Args:
            words: List of words to stem
            method: Stemming method to use

        Returns:
            List of stemmed words in same order

        Examples:
            >>> stemmer = NLPStemmer()
            >>> stemmer.batch_stem(["running", "federation", "agents"])
            ["run", "feder", "agent"]
        """
        return [self.stem(word, method) for word in words]

    def get_capabilities(self) -> StemmerCapabilities:
        """
        Get available stemmer capabilities.

        Returns:
            StemmerCapabilities dict with availability flags

        Examples:
            >>> stemmer = NLPStemmer()
            >>> caps = stemmer.get_capabilities()
            >>> caps["has_nltk"]
            True
        """
        nltk_data_path: str | None = None

        if self._nltk_available:
            try:
                import nltk  # type: ignore
                if nltk.data.path:  # type: ignore
                    nltk_data_path = str(nltk.data.path[0])  # type: ignore
            except Exception:
                pass

        return StemmerCapabilities(
            has_nltk=self._nltk_available,
            has_porter=self._porter_stemmer is not None,
            has_snowball=self._snowball_stemmer is not None,
            has_wordnet=self._lemmatizer is not None,
            nltk_data_path=nltk_data_path
        )

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into words.

        Args:
            text: Text to tokenize

        Returns:
            List of word tokens
        """
        # Simple word tokenization (alphanumeric + hyphens)
        words = re.findall(r'\b[a-zA-Z][-a-zA-Z]*\b', text.lower())
        return [w for w in words if len(w) > 0]

    def _fallback_stem(self, word: str) -> str:
        """
        Pattern-based stemming fallback when NLTK is unavailable.

        This implements a simplified Porter-like stemming algorithm
        using regex patterns for common English suffixes.

        Args:
            word: Word to stem

        Returns:
            Stemmed word using pattern matching
        """
        if len(word) <= 3:
            return word

        # Common suffix removal patterns (simplified Porter stemmer rules)
        patterns = [
            (r'(ing|ed)$', ''),           # running -> run, wanted -> want
            (r'(ies)$', 'y'),              # cities -> city
            (r'(es)$', ''),                # searches -> search
            (r'(s)$', ''),                 # agents -> agent
            (r'(tion|sion)$', 't'),        # federation -> federat
            (r'(ment)$', ''),              # development -> develop
            (r'(ness)$', ''),              # happiness -> happi
            (r'(ism)$', ''),               # capitalism -> capital
            (r'(ity)$', ''),               # complexity -> complex
            (r'(ful)$', ''),               # beautiful -> beauti
            (r'(ous)$', ''),               # dangerous -> danger
            (r'(ive)$', ''),               # active -> act
            (r'(able|ible)$', ''),         # readable -> read
            (r'(al)$', ''),                # national -> nation
            (r'(ant|ent)$', ''),           # important -> import
            (r'(er|or)$', ''),             # writer -> write
            (r'(ly)$', ''),                # quickly -> quick
        ]

        stemmed = word
        for pattern, replacement in patterns:
            new_stemmed = re.sub(pattern, replacement, stemmed)
            if new_stemmed != stemmed and len(new_stemmed) >= 3:
                stemmed = new_stemmed
                break  # Apply only one rule

        return stemmed


# Convenience function for backward compatibility
def stem_text(text: str, method: Literal["porter", "snowball", "lemmatizer"] = "porter") -> list[str]:
    """
    Convenience function to stem text and return variants.

    Args:
        text: Text to stem
        method: Stemming method to use

    Returns:
        List of unique stemmed variants

    Examples:
        >>> stem_text("running federation")
        ["run", "running", "feder", "federation"]
    """
    stemmer = NLPStemmer(auto_download=False)
    return stemmer.stem_query(text)


__all__ = [
    "NLPStemmer",
    "stem_text",
    "StemResult",
    "StemmerCapabilities",
    "has_nltk_support",
]
