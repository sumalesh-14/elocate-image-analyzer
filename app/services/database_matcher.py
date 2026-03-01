"""
Database matcher service for device identification.

This module provides database matching capabilities to find category, brand, and model
records from PostgreSQL based on text extracted by Gemini Vision API. Uses fuzzy matching
to handle variations and misspellings, with hierarchical validation of relationships.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Literal
from uuid import UUID

import asyncpg

from app.config import settings
from app.services.db_connection import db_manager
from app.services.fuzzy_matcher import FuzzyMatcher
from app.services.input_sanitizer import InputSanitizer
from app.services.query_cache import QueryCache

logger = logging.getLogger(__name__)


@dataclass
class CategoryMatch:
    """
    Result of a category matching operation.
    
    Attributes:
        id: UUID of the matched category from device_category table
        name: Name of the matched category
        similarity_score: Fuzzy match similarity score (0.0-1.0)
    """
    id: UUID
    name: str
    similarity_score: float


@dataclass
class BrandMatch:
    """
    Result of a brand matching operation.
    
    Attributes:
        id: UUID of the matched brand from device_brand table
        name: Name of the matched brand
        similarity_score: Fuzzy match similarity score (0.0-1.0)
    """
    id: UUID
    name: str
    similarity_score: float


@dataclass
class ModelMatch:
    """
    Result of a model matching operation.
    
    Attributes:
        id: UUID of the matched model from device_model table
        name: Name of the matched model
        similarity_score: Fuzzy match similarity score (0.0-1.0)
    """
    id: UUID
    name: str
    similarity_score: float


@dataclass
class DeviceMatch:
    """
    Complete device matching result with all entities and status.
    
    Attributes:
        category: Matched category or None if not found
        brand: Matched brand or None if not found
        model: Matched model or None if not found
        database_status: Status of database matching operation
            - "success": All requested matches found
            - "partial_success": Some matches found
            - "failure": Database query failed
            - "unavailable": Database connection not available
    """
    category: Optional[CategoryMatch]
    brand: Optional[BrandMatch]
    model: Optional[ModelMatch]
    database_status: Literal["success", "partial_success", "failure", "unavailable"]


class DatabaseMatcher:
    """
    Service for matching device text against PostgreSQL database records.
    
    Provides hierarchical matching with fuzzy string comparison:
    - Category matching (80% threshold)
    - Brand matching with category validation (80% threshold)
    - Model matching with category and brand validation (75% threshold)
    
    Uses query caching to reduce database load and improve performance.
    Implements graceful degradation when database is unavailable.
    """
    
    def __init__(self):
        """Initialize the database matcher with cache."""
        self.cache = QueryCache(
            max_size=settings.QUERY_CACHE_MAX_SIZE,
            ttl=settings.QUERY_CACHE_TTL
        )
    
    async def match_category(self, category_text: str) -> Optional[CategoryMatch]:
        """
        Match category text against device_category table.
        
        Queries all active categories and applies fuzzy matching with 80% threshold.
        Results are cached for 5 minutes to reduce database load.
        
        Args:
            category_text: Category text extracted from image (e.g., "Mobile Phone")
        
        Returns:
            CategoryMatch if a match is found above threshold, None otherwise
        
        Raises:
            None - errors are logged and None is returned for graceful degradation
        """
        if not category_text:
            return None
        
        # Sanitize input to prevent SQL injection
        sanitized_text = InputSanitizer.sanitize(category_text)
        if sanitized_text is None:
            logger.warning(f"Category text rejected by input sanitizer: '{category_text}'")
            return None
        
        # Use sanitized text for all operations
        category_text = sanitized_text
        
        # Check if database is available
        if not db_manager.is_available():
            logger.warning("Database unavailable for category matching")
            return None
        
        # Normalize text for cache key
        normalized_text = FuzzyMatcher.normalize(category_text)
        cache_key = QueryCache.build_key("category", normalized_text, "")
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for category: {normalized_text}")
            return cached_result
        
        try:
            # Query database with timeout
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    query = """
                        SELECT id, name 
                        FROM device_category 
                        WHERE is_active = true
                    """
                    rows = await conn.fetch(query)
                    
                    # Build candidates list for fuzzy matching
                    candidates: List[Tuple[str, dict]] = [
                        (row['name'], {'id': row['id'], 'name': row['name']})
                        for row in rows
                    ]
                    
                    # Find best match using fuzzy matcher
                    match_result = FuzzyMatcher.find_best_match(
                        category_text,
                        candidates,
                        settings.CATEGORY_MATCH_THRESHOLD
                    )
                    
                    if match_result:
                        data, score = match_result
                        category_match = CategoryMatch(
                            id=data['id'],
                            name=data['name'],
                            similarity_score=score
                        )
                        logger.info(
                            f"Category match found: '{category_text}' -> '{data['name']}' (score: {score:.2f})"
                        )
                        # Cache the result
                        self.cache.set(cache_key, category_match)
                        return category_match
                    else:
                        logger.info(
                            f"No category match found for '{category_text}' above threshold {settings.CATEGORY_MATCH_THRESHOLD}"
                        )
                        # Cache the None result to avoid repeated queries
                        self.cache.set(cache_key, None)
                        return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Category query timeout after {settings.DB_QUERY_TIMEOUT}ms for '{category_text}'")
            return None
        except (asyncpg.PostgresError, Exception) as e:
            logger.error(f"Category query failed for '{category_text}': {type(e).__name__}: {str(e)}")
            return None
    
    async def match_brand(
        self,
        brand_text: str,
        category_id: Optional[UUID]
    ) -> Optional[BrandMatch]:
        """
        Match brand text against device_brand table with category validation.
        
        Only matches brands that are valid for the given category according to
        the category_brand junction table. Applies fuzzy matching with 80% threshold.
        Results are cached for 5 minutes.
        
        Args:
            brand_text: Brand text extracted from image (e.g., "Apple")
            category_id: UUID of matched category for validation, or None to skip
        
        Returns:
            BrandMatch if a match is found above threshold, None otherwise
            Returns None if category_id is None (hierarchical dependency)
        
        Raises:
            None - errors are logged and None is returned for graceful degradation
        """
        # Hierarchical dependency: brand requires category
        if not category_id:
            logger.debug("Skipping brand matching: no category_id provided")
            return None
        
        if not brand_text:
            return None
        
        # Sanitize input to prevent SQL injection
        sanitized_text = InputSanitizer.sanitize(brand_text)
        if sanitized_text is None:
            logger.warning(f"Brand text rejected by input sanitizer: '{brand_text}'")
            return None
        
        # Use sanitized text for all operations
        brand_text = sanitized_text
        
        # Check if database is available
        if not db_manager.is_available():
            logger.warning("Database unavailable for brand matching")
            return None
        
        # Normalize text for cache key
        normalized_text = FuzzyMatcher.normalize(brand_text)
        cache_key = QueryCache.build_key("brand", normalized_text, str(category_id))
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for brand: {normalized_text} (category: {category_id})")
            return cached_result
        
        try:
            # Query database with timeout and category validation
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    query = """
                        SELECT b.id, b.name 
                        FROM device_brand b
                        INNER JOIN category_brand cb ON b.id = cb.brand_id
                        WHERE cb.category_id = $1 
                          AND b.is_active = true
                    """
                    rows = await conn.fetch(query, category_id)
                    
                    # Build candidates list for fuzzy matching
                    candidates: List[Tuple[str, dict]] = [
                        (row['name'], {'id': row['id'], 'name': row['name']})
                        for row in rows
                    ]
                    
                    # Find best match using fuzzy matcher
                    match_result = FuzzyMatcher.find_best_match(
                        brand_text,
                        candidates,
                        settings.BRAND_MATCH_THRESHOLD
                    )
                    
                    if match_result:
                        data, score = match_result
                        brand_match = BrandMatch(
                            id=data['id'],
                            name=data['name'],
                            similarity_score=score
                        )
                        logger.info(
                            f"Brand match found: '{brand_text}' -> '{data['name']}' (score: {score:.2f}, category: {category_id})"
                        )
                        # Cache the result
                        self.cache.set(cache_key, brand_match)
                        return brand_match
                    else:
                        logger.info(
                            f"No brand match found for '{brand_text}' above threshold {settings.BRAND_MATCH_THRESHOLD} (category: {category_id})"
                        )
                        # Cache the None result to avoid repeated queries
                        self.cache.set(cache_key, None)
                        return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Brand query timeout after {settings.DB_QUERY_TIMEOUT}ms for '{brand_text}'")
            return None
        except (asyncpg.PostgresError, Exception) as e:
            logger.error(f"Brand query failed for '{brand_text}': {type(e).__name__}: {str(e)}")
            return None
    
    async def match_model(
        self,
        model_text: str,
        category_id: Optional[UUID],
        brand_id: Optional[UUID]
    ) -> Optional[ModelMatch]:
        """
        Match model text against device_model table with category and brand validation.
        
        Only matches models that belong to the given category and brand.
        Applies fuzzy matching with 75% threshold.
        Results are cached for 5 minutes.
        
        Args:
            model_text: Model text extracted from image (e.g., "iPhone 14 Pro")
            category_id: UUID of matched category for filtering, or None to skip
            brand_id: UUID of matched brand for filtering, or None to skip
        
        Returns:
            ModelMatch if a match is found above threshold, None otherwise
            Returns None if category_id or brand_id is None (hierarchical dependency)
        
        Raises:
            None - errors are logged and None is returned for graceful degradation
        """
        # Hierarchical dependency: model requires both category and brand
        if not category_id or not brand_id:
            logger.debug("Skipping model matching: category_id or brand_id not provided")
            return None
        
        if not model_text:
            return None
        
        # Sanitize input to prevent SQL injection
        sanitized_text = InputSanitizer.sanitize(model_text)
        if sanitized_text is None:
            logger.warning(f"Model text rejected by input sanitizer: '{model_text}'")
            return None
        
        # Use sanitized text for all operations
        model_text = sanitized_text
        
        # Check if database is available
        if not db_manager.is_available():
            logger.warning("Database unavailable for model matching")
            return None
        
        # Normalize text for cache key
        normalized_text = FuzzyMatcher.normalize(model_text)
        cache_key = QueryCache.build_key("model", normalized_text, f"{category_id}:{brand_id}")
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for model: {normalized_text} (category: {category_id}, brand: {brand_id})")
            return cached_result
        
        try:
            # Query database with timeout and category/brand validation
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    query = """
                        SELECT id, name 
                        FROM device_model 
                        WHERE category_id = $1 
                          AND brand_id = $2 
                          AND is_active = true
                    """
                    rows = await conn.fetch(query, category_id, brand_id)
                    
                    # Build candidates list for fuzzy matching
                    candidates: List[Tuple[str, dict]] = [
                        (row['name'], {'id': row['id'], 'name': row['name']})
                        for row in rows
                    ]
                    
                    # Find best match using fuzzy matcher
                    match_result = FuzzyMatcher.find_best_match(
                        model_text,
                        candidates,
                        settings.MODEL_MATCH_THRESHOLD
                    )
                    
                    if match_result:
                        data, score = match_result
                        model_match = ModelMatch(
                            id=data['id'],
                            name=data['name'],
                            similarity_score=score
                        )
                        logger.info(
                            f"Model match found: '{model_text}' -> '{data['name']}' (score: {score:.2f}, category: {category_id}, brand: {brand_id})"
                        )
                        # Cache the result
                        self.cache.set(cache_key, model_match)
                        return model_match
                    else:
                        logger.info(
                            f"No model match found for '{model_text}' above threshold {settings.MODEL_MATCH_THRESHOLD} (category: {category_id}, brand: {brand_id})"
                        )
                        # Cache the None result to avoid repeated queries
                        self.cache.set(cache_key, None)
                        return None
        
        except asyncio.TimeoutError:
            logger.warning(f"Model query timeout after {settings.DB_QUERY_TIMEOUT}ms for '{model_text}'")
            return None
        except (asyncpg.PostgresError, Exception) as e:
            logger.error(f"Model query failed for '{model_text}': {type(e).__name__}: {str(e)}")
            return None
    
    async def match_device(
        self,
        category_text: str,
        brand_text: Optional[str],
        model_text: Optional[str]
    ) -> DeviceMatch:
        """
        Orchestrate hierarchical device matching: category → brand → model.
        
        Implements hierarchical dependencies:
        - Brand matching only executes if category is found
        - Model matching only executes if both category and brand are found
        
        Sets database_status based on results:
        - "success": All provided texts matched successfully
        - "partial_success": Some matches found but not all
        - "failure": Database queries failed
        - "unavailable": Database connection not available
        
        Args:
            category_text: Category text from Gemini (required)
            brand_text: Brand text from Gemini (optional)
            model_text: Model text from Gemini (optional)
        
        Returns:
            DeviceMatch with all matched entities and status
        """
        # Check if database is available
        if not db_manager.is_available():
            logger.warning("Database unavailable for device matching")
            return DeviceMatch(
                category=None,
                brand=None,
                model=None,
                database_status="unavailable"
            )
        
        try:
            # Step 1: Match category (always attempted)
            category_match = await self.match_category(category_text)
            
            # Step 2: Match brand (only if category found and brand_text provided)
            brand_match = None
            if category_match and brand_text:
                brand_match = await self.match_brand(brand_text, category_match.id)
            
            # Step 3: Match model (only if both category and brand found, and model_text provided)
            model_match = None
            if category_match and brand_match and model_text:
                model_match = await self.match_model(model_text, category_match.id, brand_match.id)
            
            # Determine database_status based on results
            database_status = self._determine_status(
                category_match,
                brand_match,
                model_match,
                brand_text,
                model_text
            )
            
            return DeviceMatch(
                category=category_match,
                brand=brand_match,
                model=model_match,
                database_status=database_status
            )
        
        except Exception as e:
            logger.error(f"Device matching failed: {type(e).__name__}: {str(e)}")
            return DeviceMatch(
                category=None,
                brand=None,
                model=None,
                database_status="failure"
            )
    
    def _determine_status(
        self,
        category_match: Optional[CategoryMatch],
        brand_match: Optional[BrandMatch],
        model_match: Optional[ModelMatch],
        brand_text: Optional[str],
        model_text: Optional[str]
    ) -> Literal["success", "partial_success", "failure", "unavailable"]:
        """
        Determine database_status based on matching results.
        
        Logic:
        - "success": All provided texts were matched
        - "partial_success": Some matches found but not all provided texts matched
        - "failure": No matches found at all
        
        Args:
            category_match: Category match result
            brand_match: Brand match result
            model_match: Model match result
            brand_text: Original brand text (to know if brand was requested)
            model_text: Original model text (to know if model was requested)
        
        Returns:
            Status string
        """
        # Count what was requested vs what was found
        requested = 1  # category is always requested
        if brand_text:
            requested += 1
        if model_text:
            requested += 1
        
        found = 0
        if category_match:
            found += 1
        if brand_match:
            found += 1
        if model_match:
            found += 1
        
        # Determine status
        if found == 0:
            return "failure"
        elif found == requested:
            return "success"
        else:
            return "partial_success"


# Global database matcher instance
database_matcher = DatabaseMatcher()
