"""
Database matcher service for device identification.

This module provides database matching capabilities to find category, brand, and model
records from PostgreSQL based on text extracted by Gemini Vision API.

Two-pass grounded approach:
  Pass 1 - Categories are fetched from DB and given to Gemini to choose from exactly.
  Pass 2 - Brands (filtered by category) and models (filtered by brand+category) are
           fetched and given to Gemini to choose from exactly.

Auto-seeding:
  When Gemini signals a NEW category/brand/model (prefix "NEW:"), the service
  automatically inserts the new record into the DB so the knowledge base grows
  over time (self-improving loop).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Optional, List, Tuple, Literal, Dict, Any
from uuid import UUID

import asyncpg

from app.config import settings
from app.services.db_connection import db_manager
from app.services.fuzzy_matcher import FuzzyMatcher
from app.services.input_sanitizer import InputSanitizer
from app.services.query_cache import QueryCache

logger = logging.getLogger(__name__)

# Minimum confidence score required before auto-seeding new records into the DB.
# Below this threshold we trust the image too little to pollute the knowledge base.
AUTO_SEED_CONFIDENCE_THRESHOLD = 0.70


@dataclass
class CategoryMatch:
    """
    Result of a category matching operation.

    Attributes:
        id: UUID of the matched category from device_category table
        name: Name of the matched category
        similarity_score: 1.0 means exact pick from grounded list; <1.0 means legacy fuzzy
        is_new: True if this record was just created (auto-seeded)
    """
    id: UUID
    name: str
    similarity_score: float
    is_new: bool = False


@dataclass
class BrandMatch:
    """
    Result of a brand matching operation.

    Attributes:
        id: UUID of the matched brand from device_brand table
        name: Name of the matched brand
        similarity_score: 1.0 means exact pick from grounded list; <1.0 means legacy fuzzy
        is_new: True if this record was just created (auto-seeded)
    """
    id: UUID
    name: str
    similarity_score: float
    is_new: bool = False


@dataclass
class ModelMatch:
    """
    Result of a model matching operation.

    Attributes:
        id: UUID of the matched model from device_model table
        name: Name of the matched model
        similarity_score: 1.0 means exact pick from grounded list; <1.0 means legacy fuzzy
        is_new: True if this record was just created (auto-seeded)
    """
    id: UUID
    name: str
    similarity_score: float
    is_new: bool = False


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
            - "partial_success": Some matches found but not all
            - "failure": Database query failed
            - "unavailable": Database connection not available
    """
    category: Optional[CategoryMatch]
    brand: Optional[BrandMatch]
    model: Optional[ModelMatch]
    database_status: Literal["success", "partial_success", "failure", "unavailable"]


class DatabaseMatcher:
    """
    Service for matching / auto-seeding device data against PostgreSQL.

    Two-pass grounded flow:
      1. get_all_categories()      → list of {id, name} dicts for Pass-1 prompt
      2. get_brands_for_category() → list of {id, name} dicts for Pass-2 prompt
      3. get_models_for_brand()    → list of {id, name} dicts for Pass-2 prompt
      4. match_device_grounded()   → reconcile Gemini picks, auto-seed if NEW

    Legacy fuzzy-match methods (match_category / match_brand / match_model) are
    kept for fallback when DB is unavailable before the Gemini call.
    """

    def __init__(self):
        """Initialize the database matcher with cache."""
        self.cache = QueryCache(
            max_size=settings.QUERY_CACHE_MAX_SIZE,
            ttl=settings.QUERY_CACHE_TTL
        )

    # -------------------------------------------------------------------------
    # Fetch helpers used to build grounded prompts
    # -------------------------------------------------------------------------

    async def get_all_categories(self) -> List[dict]:
        """
        Fetch all active categories from DB for Pass-1 grounded prompt.

        Returns:
            List of dicts: [{"id": UUID, "name": str}, ...]
            Empty list if DB unavailable.
        """
        cache_key = "all_categories_list"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if not db_manager.is_available():
            logger.warning("DB unavailable – cannot fetch categories for grounded prompt")
            return []

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT id, name FROM device_category WHERE is_active = true ORDER BY name"
                    )
                    result = [{"id": row["id"], "name": row["name"]} for row in rows]
                    # Cache for 10 minutes – categories change very rarely
                    self.cache.set(cache_key, result)
                    logger.debug(f"Fetched {len(result)} categories from DB for grounded prompt")
                    return result

        except Exception as e:
            logger.error(f"Failed to fetch categories: {type(e).__name__}: {str(e)}")
            return []

    async def get_brands_for_category(self, category_id: UUID) -> List[dict]:
        """
        Fetch all active brands linked to a category for Pass-2 grounded prompt.

        Args:
            category_id: UUID of the matched category

        Returns:
            List of dicts: [{"id": UUID, "name": str}, ...]
        """
        cache_key = f"brands_for_cat_{category_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if not db_manager.is_available():
            logger.warning("DB unavailable – cannot fetch brands for grounded prompt")
            return []

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT b.id, b.name
                        FROM device_brand b
                        INNER JOIN category_brand cb ON b.id = cb.brand_id
                        WHERE cb.category_id = $1 AND b.is_active = true
                        ORDER BY b.name
                        """,
                        category_id
                    )
                    result = [{"id": row["id"], "name": row["name"]} for row in rows]
                    self.cache.set(cache_key, result)
                    logger.debug(
                        f"Fetched {len(result)} brands for category {category_id}"
                    )
                    return result

        except Exception as e:
            logger.error(f"Failed to fetch brands for category {category_id}: {type(e).__name__}: {str(e)}")
            return []

    async def get_models_for_brand_category(
        self, brand_id: UUID, category_id: UUID
    ) -> List[dict]:
        """
        Fetch all active models for a brand+category combo for Pass-2 grounded prompt.

        Args:
            brand_id: UUID of the matched brand
            category_id: UUID of the matched category

        Returns:
            List of dicts: [{"id": UUID, "name": str}, ...]
        """
        cache_key = f"models_{category_id}_{brand_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if not db_manager.is_available():
            return []

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id, model_name as name
                        FROM device_model
                        WHERE category_id = $1 AND brand_id = $2 AND is_active = true
                        ORDER BY model_name
                        """,
                        category_id,
                        brand_id
                    )
                    result = [{"id": row["id"], "name": row["name"]} for row in rows]
                    self.cache.set(cache_key, result)
                    logger.debug(
                        f"Fetched {len(result)} models for brand {brand_id} / category {category_id}"
                    )
                    return result

        except Exception as e:
            logger.error(
                f"Failed to fetch models for brand {brand_id} / category {category_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            return []

    # -------------------------------------------------------------------------
    # Auto-seed helpers: insert new records into DB
    # -------------------------------------------------------------------------

    async def create_category(self, name: str) -> Optional[UUID]:
        """
        Insert a new category into device_category.

        Uses INSERT ... ON CONFLICT DO NOTHING to handle race conditions when
        multiple concurrent requests try to create the same category.

        Args:
            name: Category name as identified by Gemini

        Returns:
            UUID of inserted (or existing) record, or None on error
        """
        if not db_manager.is_available():
            logger.warning("DB unavailable – cannot auto-seed category")
            return None

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    # Try to insert; ignore if name already exists (case-insensitive)
                    existing = await conn.fetchrow(
                        "SELECT id FROM device_category WHERE LOWER(name) = LOWER($1)", name
                    )
                    if existing:
                        logger.info(f"Category '{name}' already exists – reusing id {existing['id']}")
                        self._invalidate_category_cache()
                        return existing["id"]

                    new_id = uuid.uuid4()
                    # Generate a simple upper snake-case code since 'code' is required
                    category_code = name.upper().strip()
                    for char in [" ", "-", "/"]:
                        category_code = category_code.replace(char, "_")

                    await conn.execute(
                        """
                        INSERT INTO device_category (id, code, name, is_active)
                        VALUES ($1, $2, $3, true)
                        ON CONFLICT DO NOTHING
                        """,
                        new_id, category_code, name
                    )
                    logger.info(f"Auto-seeded new category: '{name}' (id={new_id}, code={category_code})")
                    self._invalidate_category_cache()
                    return new_id

        except Exception as e:
            logger.error(f"Failed to auto-seed category '{name}': {type(e).__name__}: {str(e)}")
            return None

    async def create_brand(self, name: str, category_id: UUID) -> Optional[UUID]:
        """
        Insert a new brand into device_brand and link it to the category via category_brand.

        Args:
            name: Brand name
            category_id: UUID of the category this brand belongs to

        Returns:
            UUID of inserted (or existing) brand record, or None on error
        """
        if not db_manager.is_available():
            logger.warning("DB unavailable – cannot auto-seed brand")
            return None

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    # Check if brand already exists globally
                    existing = await conn.fetchrow(
                        "SELECT id FROM device_brand WHERE LOWER(name) = LOWER($1)", name
                    )

                    if existing:
                        brand_id = existing["id"]
                        logger.info(f"Brand '{name}' already exists (id={brand_id}) – checking mapping")
                    else:
                        brand_id = uuid.uuid4()
                        await conn.execute(
                            """
                            INSERT INTO device_brand (id, name, is_active)
                            VALUES ($1, $2, true)
                            ON CONFLICT DO NOTHING
                            """,
                            brand_id, name
                        )
                        logger.info(f"Auto-seeded new brand: '{name}' (id={brand_id})")

                    # Ensure the category_brand mapping exists (requires its own UUID)
                    mapping_id = uuid.uuid4()
                    await conn.execute(
                        """
                        INSERT INTO category_brand (id, category_id, brand_id)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING
                        """,
                        mapping_id, category_id, brand_id
                    )
                    logger.info(f"Ensured category_brand mapping: category={category_id} ↔ brand={brand_id}")
                    self._invalidate_brand_cache(category_id)
                    return brand_id

        except Exception as e:
            logger.error(
                f"Failed to auto-seed brand '{name}' for category {category_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            return None

    async def create_model(
        self, name: str, brand_id: UUID, category_id: UUID, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Insert a new model into device_model linked to brand and category.

        Args:
            name: Model name
            brand_id: UUID of the brand
            category_id: UUID of the category
            metadata: Optional dictionary with precious metals and recyclability estimates

        Returns:
            UUID of inserted (or existing) model record, or None on error
        """
        if not db_manager.is_available():
            logger.warning("DB unavailable – cannot auto-seed model")
            return None
            
        import json
        metadata = metadata or {}
        recycle_items = metadata.get("recycle_items", [])
        recycle_items_json = json.dumps(recycle_items) if recycle_items else None

        try:
            async with asyncio.timeout(settings.DB_QUERY_TIMEOUT / 1000):
                async with db_manager.pool.acquire() as conn:
                    existing = await conn.fetchrow(
                        """
                        SELECT id FROM device_model
                        WHERE LOWER(model_name) = LOWER($1)
                          AND brand_id = $2
                          AND category_id = $3
                        """,
                        name, brand_id, category_id
                    )

                    if existing:
                        logger.info(
                            f"Model '{name}' already exists for brand={brand_id} / "
                            f"category={category_id} – reusing id {existing['id']}"
                        )
                        return existing["id"]

                    new_id = uuid.uuid4()
                    await conn.execute(
                        """
                        INSERT INTO device_model (
                            id, model_name, brand_id, category_id, is_active,
                            recycle_items
                        )
                        VALUES ($1, $2, $3, $4, true, $5::jsonb)
                        ON CONFLICT DO NOTHING
                        """,
                        new_id, name, brand_id, category_id, recycle_items_json
                    )
                    logger.info(
                        f"Auto-seeded new model: '{name}' (id={new_id}, "
                        f"brand={brand_id}, category={category_id})"
                    )
                    self._invalidate_model_cache(brand_id, category_id)
                    return new_id

        except Exception as e:
            logger.error(
                f"Failed to auto-seed model '{name}': {type(e).__name__}: {str(e)}"
            )
            return None

    # -------------------------------------------------------------------------
    # Main entry-point: two-pass grounded device matching
    # -------------------------------------------------------------------------

    async def match_device_grounded(
        self,
        category_pick: Optional[str],
        brand_pick: Optional[str],
        model_pick: Optional[str],
        categories: List[dict],
        brands: List[dict],
        models: List[dict],
        confidence: float = 1.0,
    ) -> DeviceMatch:
        """
        Reconcile Gemini's grounded picks against DB records.

        Gemini signals "NEW:<name>" when a value is not in the provided list.
        This method handles the three outcomes for each field:

          1. Exact match in provided list → look up UUID directly
          2. "NEW:<name>" prefix → auto-seed into DB if confidence ≥ threshold
          3. None / null → skip

        Args:
            category_pick: Gemini output for category (exact name or "NEW:...")
            brand_pick: Gemini output for brand (exact name, "NEW:...", or None)
            model_pick: Gemini output for model (exact name, "NEW:...", or None)
            categories: The list that was given to Gemini in Pass 1
            brands: The list that was given to Gemini in Pass 2
            models: The list that was given to Gemini in Pass 2
            confidence: Overall confidence score from Gemini (used for auto-seed gate)

        Returns:
            DeviceMatch with matched/created entities and status
        """
        if not db_manager.is_available():
            return DeviceMatch(
                category=None, brand=None, model=None,
                database_status="unavailable"
            )

        try:
            # -- Category --
            category_match = await self._resolve_category(
                category_pick, categories, confidence
            )

            # -- Brand --
            brand_match = None
            if category_match and brand_pick:
                brand_match = await self._resolve_brand(
                    brand_pick, brands, category_match.id, confidence
                )

            # -- Model --
            model_match = None
            if category_match and brand_match and model_pick:
                model_match = await self._resolve_model(
                    model_pick, models, brand_match.id, category_match.id, confidence
                )

            status = self._determine_status(
                category_match, brand_match, model_match, brand_pick, model_pick
            )

            logger.info(
                "Grounded device match complete",
                extra={
                    "category": category_match.name if category_match else None,
                    "category_new": category_match.is_new if category_match else False,
                    "brand": brand_match.name if brand_match else None,
                    "brand_new": brand_match.is_new if brand_match else False,
                    "model": model_match.name if model_match else None,
                    "model_new": model_match.is_new if model_match else False,
                    "status": status,
                }
            )

            return DeviceMatch(
                category=category_match,
                brand=brand_match,
                model=model_match,
                database_status=status
            )

        except Exception as e:
            logger.error(f"Grounded device matching failed: {type(e).__name__}: {str(e)}", exc_info=True)
            return DeviceMatch(
                category=None, brand=None, model=None,
                database_status="failure"
            )

    # -------------------------------------------------------------------------
    # Private resolve helpers
    # -------------------------------------------------------------------------

    async def _resolve_category(
        self,
        pick: Optional[str],
        categories: List[dict],
        confidence: float,
    ) -> Optional[CategoryMatch]:
        """Resolve a category pick (exact or NEW:) to a DB record."""
        if not pick:
            return None

        is_new, clean_name = self._parse_new_prefix(pick)

        if not clean_name:
            return None

        if is_new:
            if confidence < AUTO_SEED_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Skipping auto-seed for new category '{clean_name}' "
                    f"– confidence {confidence:.2f} below threshold {AUTO_SEED_CONFIDENCE_THRESHOLD}"
                )
                return None

            new_id = await self.create_category(clean_name)
            if new_id:
                return CategoryMatch(
                    id=new_id, name=clean_name,
                    similarity_score=1.0, is_new=True
                )
            return None

        # Exact lookup in the provided list
        for cat in categories:
            if cat["name"].strip().lower() == clean_name.strip().lower():
                return CategoryMatch(
                    id=cat["id"], name=cat["name"],
                    similarity_score=1.0, is_new=False
                )

        # Fallback: fuzzy match within the list (in case Gemini slightly deviated)
        logger.warning(
            f"Category pick '{clean_name}' not found exactly in list – trying fuzzy fallback"
        )
        candidates = [(c["name"], c) for c in categories]
        result = FuzzyMatcher.find_best_match(clean_name, candidates, 0.75)
        if result:
            data, score = result
            logger.info(f"Category fuzzy fallback: '{clean_name}' → '{data['name']}' ({score:.2f})")
            return CategoryMatch(
                id=data["id"], name=data["name"],
                similarity_score=score, is_new=False
            )

        logger.warning(f"Category '{clean_name}' could not be resolved – no fuzzy match above 0.75")
        return None

    async def _resolve_brand(
        self,
        pick: Optional[str],
        brands: List[dict],
        category_id: UUID,
        confidence: float,
    ) -> Optional[BrandMatch]:
        """Resolve a brand pick (exact or NEW:) to a DB record."""
        if not pick:
            return None

        is_new, clean_name = self._parse_new_prefix(pick)

        if not clean_name:
            return None

        if is_new:
            if confidence < AUTO_SEED_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Skipping auto-seed for new brand '{clean_name}' "
                    f"– confidence {confidence:.2f} below threshold"
                )
                return None

            new_id = await self.create_brand(clean_name, category_id)
            if new_id:
                return BrandMatch(
                    id=new_id, name=clean_name,
                    similarity_score=1.0, is_new=True
                )
            return None

        # Exact lookup
        for b in brands:
            if b["name"].strip().lower() == clean_name.strip().lower():
                return BrandMatch(
                    id=b["id"], name=b["name"],
                    similarity_score=1.0, is_new=False
                )

        # Fuzzy fallback within provided list
        logger.warning(f"Brand pick '{clean_name}' not found exactly – trying fuzzy fallback")
        candidates = [(b["name"], b) for b in brands]
        result = FuzzyMatcher.find_best_match(clean_name, candidates, 0.75)
        if result:
            data, score = result
            logger.info(f"Brand fuzzy fallback: '{clean_name}' → '{data['name']}' ({score:.2f})")
            return BrandMatch(
                id=data["id"], name=data["name"],
                similarity_score=score, is_new=False
            )

        logger.warning(f"Brand '{clean_name}' could not be resolved")
        return None

    async def _resolve_model(
        self,
        pick: Optional[str],
        models: List[dict],
        brand_id: UUID,
        category_id: UUID,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ModelMatch]:
        """Resolve a model pick (exact or NEW:) to a DB record."""
        if not pick:
            return None

        is_new, clean_name = self._parse_new_prefix(pick)

        if not clean_name:
            return None

        if is_new:
            if confidence < AUTO_SEED_CONFIDENCE_THRESHOLD:
                logger.warning(
                    f"Skipping auto-seed for new model '{clean_name}' "
                    f"– confidence {confidence:.2f} below threshold"
                )
                return None

            new_id = await self.create_model(clean_name, brand_id, category_id, metadata=metadata)
            if new_id:
                return ModelMatch(
                    id=new_id, name=clean_name,
                    similarity_score=1.0, is_new=True
                )
            return None

        # Exact lookup
        for m in models:
            if m["name"].strip().lower() == clean_name.strip().lower():
                return ModelMatch(
                    id=m["id"], name=m["name"],
                    similarity_score=1.0, is_new=False
                )

        # Fuzzy fallback (models have many variations – keep 0.70 threshold)
        candidates = [(m["name"], m) for m in models]
        result = FuzzyMatcher.find_best_match(clean_name, candidates, 0.70)
        if result:
            data, score = result
            logger.info(f"Model fuzzy fallback: '{clean_name}' → '{data['name']}' ({score:.2f})")
            return ModelMatch(
                id=data["id"], name=data["name"],
                similarity_score=score, is_new=False
            )

        logger.warning(f"Model '{clean_name}' could not be resolved")
        return None

    @staticmethod
    def _parse_new_prefix(value: str) -> Tuple[bool, str]:
        """
        Parse Gemini's NEW: prefix signal.

        Returns:
            (is_new, cleaned_name) tuple
            is_new=True means the value was not in the provided list
        """
        stripped = value.strip()
        if stripped.upper().startswith("NEW:"):
            clean = stripped[4:].strip()
            return True, clean
        return False, stripped

    # -------------------------------------------------------------------------
    # Cache invalidation helpers
    # -------------------------------------------------------------------------

    def _invalidate_category_cache(self):
        """Clear the full cache after a new category is seeded so the next
        prompt fetch picks up the new entry immediately."""
        try:
            self.cache.clear()
        except Exception:
            pass
        logger.debug("Cache cleared after category auto-seed")

    def _invalidate_brand_cache(self, category_id: UUID):
        """Remove brand cache for this category."""
        try:
            with self.cache._lock:
                self.cache._cache.pop(f"brands_for_cat_{category_id}", None)
        except Exception:
            pass

    def _invalidate_model_cache(self, brand_id: UUID, category_id: UUID):
        """Remove model cache for this brand+category."""
        try:
            with self.cache._lock:
                self.cache._cache.pop(f"models_{category_id}_{brand_id}", None)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Status helper
    # -------------------------------------------------------------------------

    def _determine_status(
        self,
        category_match: Optional[CategoryMatch],
        brand_match: Optional[BrandMatch],
        model_match: Optional[ModelMatch],
        brand_text: Optional[str],
        model_text: Optional[str],
    ) -> Literal["success", "partial_success", "failure", "unavailable"]:
        """Determine database_status based on matching results."""
        requested = 1  # category always
        if brand_text:
            requested += 1
        if model_text:
            requested += 1

        found = sum([
            1 if category_match else 0,
            1 if brand_match else 0,
            1 if model_match else 0,
        ])

        if found == 0:
            return "failure"
        elif found == requested:
            return "success"
        else:
            return "partial_success"

    # -------------------------------------------------------------------------
    # Legacy fuzzy match methods (kept as fallback when DB unavailable pre-Gemini)
    # -------------------------------------------------------------------------

    async def match_category(self, category_text: str) -> Optional[CategoryMatch]:
        """Legacy fuzzy category match – used as fallback only."""
        if not category_text or not db_manager.is_available():
            return None

        sanitized = InputSanitizer.sanitize(category_text)
        if not sanitized:
            return None

        categories = await self.get_all_categories()
        if not categories:
            return None

        candidates = [(c["name"], c) for c in categories]
        result = FuzzyMatcher.find_best_match(
            sanitized, candidates, settings.CATEGORY_MATCH_THRESHOLD
        )
        if result:
            data, score = result
            return CategoryMatch(id=data["id"], name=data["name"], similarity_score=score)
        return None

    async def match_device(
        self,
        category_text: str,
        brand_text: Optional[str],
        model_text: Optional[str],
    ) -> DeviceMatch:
        """
        Legacy entry-point (fuzzy only) kept for backward compatibility.
        The new code path uses match_device_grounded().
        """
        if not db_manager.is_available():
            return DeviceMatch(
                category=None, brand=None, model=None,
                database_status="unavailable"
            )

        try:
            category_match = await self.match_category(category_text)

            brand_match = None
            if category_match and brand_text:
                brands = await self.get_brands_for_category(category_match.id)
                candidates = [(b["name"], b) for b in brands]
                sanitized_brand = InputSanitizer.sanitize(brand_text)
                result = FuzzyMatcher.find_best_match(
                    sanitized_brand, candidates, settings.BRAND_MATCH_THRESHOLD
                )
                if result:
                    data, score = result
                    brand_match = BrandMatch(id=data["id"], name=data["name"], similarity_score=score)

            model_match = None
            if category_match and brand_match and model_text:
                models = await self.get_models_for_brand_category(brand_match.id, category_match.id)
                candidates = [(m["name"], m) for m in models]
                sanitized_model = InputSanitizer.sanitize(model_text)
                result = FuzzyMatcher.find_best_match(
                    sanitized_model, candidates, settings.MODEL_MATCH_THRESHOLD
                )
                if result:
                    data, score = result
                    model_match = ModelMatch(id=data["id"], name=data["name"], similarity_score=score)

            status = self._determine_status(
                category_match, brand_match, model_match, brand_text, model_text
            )
            return DeviceMatch(
                category=category_match, brand=brand_match,
                model=model_match, database_status=status
            )

        except Exception as e:
            logger.error(f"Legacy device matching failed: {type(e).__name__}: {str(e)}")
            return DeviceMatch(
                category=None, brand=None, model=None,
                database_status="failure"
            )


# Global database matcher instance
database_matcher = DatabaseMatcher()
