"""
Unit tests for fuzzy matcher service.

Tests specific examples, edge cases, and known scenarios for the fuzzy matching
functionality used in database matching integration.
"""

import pytest

from app.services.fuzzy_matcher import FuzzyMatcher


class TestNormalize:
    """Test cases for string normalization."""

    def test_normalize_empty_string(self):
        """Empty string should return empty string."""
        assert FuzzyMatcher.normalize("") == ""

    def test_normalize_whitespace_only(self):
        """String with only whitespace should return empty string."""
        assert FuzzyMatcher.normalize("   ") == ""
        assert FuzzyMatcher.normalize("\t\n") == ""

    def test_normalize_lowercase_conversion(self):
        """Should convert to lowercase."""
        assert FuzzyMatcher.normalize("APPLE") == "apple"
        assert FuzzyMatcher.normalize("iPhone") == "iphone"
        assert FuzzyMatcher.normalize("SaMsUnG") == "samsung"

    def test_normalize_whitespace_trimming(self):
        """Should remove leading and trailing whitespace."""
        assert FuzzyMatcher.normalize("  apple  ") == "apple"
        assert FuzzyMatcher.normalize("\tiphone\n") == "iphone"

    def test_normalize_multiple_spaces(self):
        """Should replace multiple spaces with single space."""
        assert FuzzyMatcher.normalize("apple  iphone") == "apple iphone"
        assert FuzzyMatcher.normalize("samsung   galaxy    s23") == "samsung galaxy s23"

    def test_normalize_special_characters(self):
        """Should remove special characters except hyphens and underscores."""
        assert FuzzyMatcher.normalize("apple!@#$%") == "apple"
        assert FuzzyMatcher.normalize("iphone (14)") == "iphone 14"
        assert FuzzyMatcher.normalize("galaxy*s23") == "galaxys23"

    def test_normalize_preserve_hyphens_underscores(self):
        """Should preserve hyphens and underscores."""
        assert FuzzyMatcher.normalize("galaxy-s23") == "galaxy-s23"
        assert FuzzyMatcher.normalize("iphone_14") == "iphone_14"
        assert FuzzyMatcher.normalize("model-name_v2") == "model-name_v2"

    def test_normalize_complex_string(self):
        """Should handle complex strings with multiple issues."""
        assert FuzzyMatcher.normalize("  Apple  iPhone-14  Pro!!  ") == "apple iphone-14 pro"
        assert FuzzyMatcher.normalize("SAMSUNG (Galaxy) S23+") == "samsung galaxy s23"


class TestCalculateSimilarity:
    """Test cases for similarity calculation."""

    def test_identical_strings(self):
        """Identical strings should have similarity 1.0."""
        assert FuzzyMatcher.calculate_similarity("apple", "apple") == 1.0
        assert FuzzyMatcher.calculate_similarity("iphone", "iphone") == 1.0

    def test_case_insensitive_matching(self):
        """Case differences should not affect similarity."""
        assert FuzzyMatcher.calculate_similarity("Apple", "apple") == 1.0
        assert FuzzyMatcher.calculate_similarity("IPHONE", "iphone") == 1.0
        assert FuzzyMatcher.calculate_similarity("SaMsUnG", "samsung") == 1.0

    def test_empty_strings(self):
        """Empty strings should have similarity 1.0 with each other."""
        assert FuzzyMatcher.calculate_similarity("", "") == 1.0

    def test_one_empty_string(self):
        """One empty string should have low similarity."""
        score = FuzzyMatcher.calculate_similarity("apple", "")
        assert score == 0.0

    def test_completely_different_strings(self):
        """Completely different strings should have low similarity."""
        score = FuzzyMatcher.calculate_similarity("apple", "samsung")
        assert score < 0.5

    def test_similar_strings(self):
        """Similar strings should have high similarity."""
        # "iphone" vs "iphone 14" should be fairly similar
        score = FuzzyMatcher.calculate_similarity("iphone", "iphone 14")
        assert score > 0.6

    def test_misspellings(self):
        """Misspellings should still have reasonable similarity."""
        # "iphone" vs "iphon" (missing 'e')
        score = FuzzyMatcher.calculate_similarity("iphone", "iphon")
        assert score > 0.8

    def test_whitespace_differences(self):
        """Whitespace differences should be normalized."""
        assert FuzzyMatcher.calculate_similarity("apple iphone", "apple  iphone") == 1.0
        assert FuzzyMatcher.calculate_similarity("  apple", "apple  ") == 1.0

    def test_special_character_differences(self):
        """Special characters should be normalized."""
        score1 = FuzzyMatcher.calculate_similarity("galaxy-s23", "galaxy s23")
        score2 = FuzzyMatcher.calculate_similarity("iphone (14)", "iphone 14")
        # Should be very similar after normalization
        assert score1 >= 0.9
        assert score2 >= 0.9


class TestFindBestMatch:
    """Test cases for finding best match from candidates."""

    def test_exact_match(self):
        """Should find exact match with score 1.0."""
        candidates = [
            ("Apple", {"id": 1}),
            ("Samsung", {"id": 2}),
            ("Google", {"id": 3})
        ]
        result = FuzzyMatcher.find_best_match("apple", candidates, 0.8)
        assert result is not None
        assert result[0] == {"id": 1}
        assert result[1] == 1.0

    def test_no_match_below_threshold(self):
        """Should return None when no match exceeds threshold."""
        candidates = [
            ("Apple", {"id": 1}),
            ("Samsung", {"id": 2})
        ]
        result = FuzzyMatcher.find_best_match("Nokia", candidates, 0.8)
        assert result is None

    def test_best_match_selection(self):
        """Should select the best match when multiple candidates match."""
        candidates = [
            ("iPhone", {"id": 1}),
            ("iPhone 14", {"id": 2}),
            ("iPhone 14 Pro", {"id": 3})
        ]
        result = FuzzyMatcher.find_best_match("iphone 14", candidates, 0.7)
        assert result is not None
        # Should match "iPhone 14" exactly
        assert result[0] == {"id": 2}
        assert result[1] == 1.0

    def test_empty_candidates(self):
        """Should return None for empty candidates list."""
        result = FuzzyMatcher.find_best_match("apple", [], 0.8)
        assert result is None

    def test_empty_query(self):
        """Should return None for empty query."""
        candidates = [("Apple", {"id": 1})]
        result = FuzzyMatcher.find_best_match("", candidates, 0.8)
        assert result is None

    def test_threshold_enforcement(self):
        """Should respect threshold parameter."""
        candidates = [
            ("Apple", {"id": 1}),
            ("Samsung", {"id": 2})
        ]
        # With high threshold, "appl" shouldn't match "Apple"
        result = FuzzyMatcher.find_best_match("appl", candidates, 0.95)
        assert result is None
        
        # With lower threshold, it should match
        result = FuzzyMatcher.find_best_match("appl", candidates, 0.7)
        assert result is not None
        assert result[0] == {"id": 1}

    def test_case_insensitive_matching(self):
        """Should match regardless of case."""
        candidates = [
            ("Apple", {"id": 1}),
            ("SAMSUNG", {"id": 2})
        ]
        result = FuzzyMatcher.find_best_match("APPLE", candidates, 0.8)
        assert result is not None
        assert result[0] == {"id": 1}
        assert result[1] == 1.0

    def test_complex_candidate_data(self):
        """Should handle complex candidate data structures."""
        candidates = [
            ("iPhone 14 Pro", {"id": "uuid-1", "name": "iPhone 14 Pro", "active": True}),
            ("Galaxy S23", {"id": "uuid-2", "name": "Galaxy S23", "active": True})
        ]
        result = FuzzyMatcher.find_best_match("iphone 14 pro", candidates, 0.8)
        assert result is not None
        assert result[0]["id"] == "uuid-1"
        assert result[0]["name"] == "iPhone 14 Pro"

    def test_multiple_similar_matches(self):
        """Should return the best match when multiple are similar."""
        candidates = [
            ("Galaxy S23", {"id": 1}),
            ("Galaxy S23 Plus", {"id": 2}),
            ("Galaxy S23 Ultra", {"id": 3})
        ]
        result = FuzzyMatcher.find_best_match("galaxy s23", candidates, 0.7)
        assert result is not None
        # Should match "Galaxy S23" exactly
        assert result[0] == {"id": 1}
        assert result[1] == 1.0

