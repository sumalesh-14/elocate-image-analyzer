"""
Fuzzy matching service for string similarity calculations.

This module provides fuzzy string matching capabilities using the rapidfuzz library
to handle common variations, misspellings, and text differences in device identification.
"""

import re
from typing import Any, List, Optional, Tuple

from rapidfuzz import fuzz


class FuzzyMatcher:
    """
    Utility class for fuzzy string matching operations.
    
    Provides methods for string normalization, similarity calculation,
    and best match selection from a list of candidates.
    """

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize a string for consistent comparison.
        
        Normalization rules:
        - Convert to lowercase
        - Strip leading/trailing whitespace
        - Replace multiple spaces with single space
        - Remove special characters (except hyphens and underscores)
        
        Args:
            text: Input string to normalize
            
        Returns:
            Normalized string
            
        Examples:
            >>> FuzzyMatcher.normalize("  Apple iPhone  ")
            'apple iphone'
            >>> FuzzyMatcher.normalize("Samsung Galaxy-S23")
            'samsung galaxy-s23'
        """
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower()
        
        # Strip leading/trailing whitespace
        normalized = normalized.strip()
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters except hyphens and underscores
        normalized = re.sub(r'[^\w\s\-]', '', normalized)
        
        # Strip again after removing special characters (they might leave trailing spaces)
        normalized = normalized.strip()
        
        return normalized

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity score between two strings using Levenshtein distance.
        
        Uses rapidfuzz's ratio function which returns a score between 0 and 100,
        normalized to 0.0-1.0 range for consistency with design requirements.
        
        Args:
            text1: First string to compare
            text2: Second string to compare
            
        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)
            
        Examples:
            >>> FuzzyMatcher.calculate_similarity("apple", "apple")
            1.0
            >>> FuzzyMatcher.calculate_similarity("iphone", "iPhone")
            1.0
            >>> FuzzyMatcher.calculate_similarity("apple", "orange")
            < 0.5
        """
        # Normalize both strings for case-insensitive comparison
        norm1 = FuzzyMatcher.normalize(text1)
        norm2 = FuzzyMatcher.normalize(text2)
        
        # Calculate similarity using rapidfuzz ratio (returns 0-100)
        score = fuzz.ratio(norm1, norm2)
        
        # Normalize to 0.0-1.0 range
        return score / 100.0

    @staticmethod
    def find_best_match(
        query: str,
        candidates: List[Tuple[str, Any]],
        threshold: float
    ) -> Optional[Tuple[Any, float]]:
        """
        Find the best matching candidate from a list based on similarity threshold.
        
        Args:
            query: The string to match against candidates
            candidates: List of (text, data) tuples where text is compared and data is returned
            threshold: Minimum similarity score (0.0-1.0) required for a match
            
        Returns:
            Tuple of (data, score) for the best match, or None if no match exceeds threshold
            
        Examples:
            >>> candidates = [("Apple", {"id": 1}), ("Samsung", {"id": 2})]
            >>> FuzzyMatcher.find_best_match("apple", candidates, 0.8)
            ({"id": 1}, 1.0)
            >>> FuzzyMatcher.find_best_match("Nokia", candidates, 0.8)
            None
        """
        if not query or not candidates:
            return None
        
        best_match = None
        best_score = 0.0
        
        for candidate_text, candidate_data in candidates:
            score = FuzzyMatcher.calculate_similarity(query, candidate_text)
            
            if score > best_score:
                best_score = score
                best_match = candidate_data
        
        # Only return match if it exceeds threshold
        if best_score >= threshold:
            return (best_match, best_score)
        
        return None
