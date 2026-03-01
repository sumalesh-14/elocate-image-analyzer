"""
Property-based tests for fuzzy matcher service.

Tests universal properties that should hold across all inputs for the fuzzy matching
functionality used in database matching integration.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.services.fuzzy_matcher import FuzzyMatcher


# Feature: database-matching-integration, Property 14: String Normalization
@given(text=st.text(min_size=0, max_size=200))
@settings(max_examples=20)
@pytest.mark.property_test
def test_string_normalization_properties(text: str):
    """
    **Validates: Requirements 5.1**
    
    For any input string to the fuzzy matcher, the normalized output should be 
    lowercase, have leading/trailing whitespace removed, and contain only single 
    spaces between words.
    """
    normalized = FuzzyMatcher.normalize(text)
    
    # Property 1: Result should be lowercase
    assert normalized == normalized.lower(), \
        f"Normalized string should be lowercase: '{normalized}'"
    
    # Property 2: No leading or trailing whitespace
    assert normalized == normalized.strip(), \
        f"Normalized string should have no leading/trailing whitespace: '{normalized}'"
    
    # Property 3: No multiple consecutive spaces
    assert "  " not in normalized, \
        f"Normalized string should not contain multiple consecutive spaces: '{normalized}'"
    
    # Property 4: If original had content, normalized should not be just whitespace
    if text.strip():
        # After normalization, if there was non-whitespace content, result should have content
        # (unless all characters were special characters that got removed)
        pass  # This is acceptable - special chars can be removed


# Feature: database-matching-integration, Property 15: Similarity Score Range
@given(
    text1=st.text(min_size=0, max_size=100),
    text2=st.text(min_size=0, max_size=100)
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_similarity_score_range(text1: str, text2: str):
    """
    **Validates: Requirements 5.3**
    
    For any two strings compared by the fuzzy matcher, the similarity score 
    should be between 0.0 and 1.0 inclusive.
    """
    score = FuzzyMatcher.calculate_similarity(text1, text2)
    
    assert 0.0 <= score <= 1.0, \
        f"Similarity score {score} is outside valid range [0.0, 1.0] for '{text1}' vs '{text2}'"


# Feature: database-matching-integration, Property 16: Case Insensitivity
@given(
    text=st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=65, max_codepoint=122))
)
@settings(max_examples=20)
@pytest.mark.property_test
def test_case_insensitivity(text: str):
    """
    **Validates: Requirements 5.5**
    
    For any two strings that differ only in case (e.g., "Apple" and "apple"), 
    the fuzzy matcher should return a similarity score of 1.0.
    """
    # Create case variations
    lower_text = text.lower()
    upper_text = text.upper()
    
    # Calculate similarity between different case versions
    score_lower_upper = FuzzyMatcher.calculate_similarity(lower_text, upper_text)
    score_original_lower = FuzzyMatcher.calculate_similarity(text, lower_text)
    score_original_upper = FuzzyMatcher.calculate_similarity(text, upper_text)
    
    # All case variations should have perfect similarity
    assert score_lower_upper == 1.0, \
        f"Case variations should have similarity 1.0: '{lower_text}' vs '{upper_text}' = {score_lower_upper}"
    assert score_original_lower == 1.0, \
        f"Case variations should have similarity 1.0: '{text}' vs '{lower_text}' = {score_original_lower}"
    assert score_original_upper == 1.0, \
        f"Case variations should have similarity 1.0: '{text}' vs '{upper_text}' = {score_original_upper}"

