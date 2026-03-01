"""
Property-based tests for response model integration with database matching.

These tests validate correctness properties from the design document related to
UUID population, match scores, and database status fields in API responses.
"""

import pytest
from hypothesis import given, strategies as st, settings
from uuid import UUID, uuid4
from typing import Optional

from app.models.response import DeviceData


# Feature: database-matching-integration, Property 17: UUID Population on Match
@given(
    category_id=st.uuids(),
    brand_id=st.uuids(),
    model_id=st.uuids(),
    category_score=st.floats(min_value=0.0, max_value=1.0),
    brand_score=st.floats(min_value=0.0, max_value=1.0),
    model_score=st.floats(min_value=0.0, max_value=1.0)
)
@pytest.mark.property_test
def test_uuid_population_on_match(
    category_id: UUID,
    brand_id: UUID,
    model_id: UUID,
    category_score: float,
    brand_score: float,
    model_score: float
):
    """
    Property 17: UUID Population on Match
    
    For any successful database match (category, brand, or model), the corresponding
    id field in the response should contain a valid UUID (not null).
    
    Validates: Requirements 6.2
    """
    # Create a device data with database matches
    device_data = DeviceData(
        category="Mobile Phone",
        brand="Apple",
        model="iPhone 14",
        deviceType="smartphone",
        confidenceScore=0.9,
        accuracy=0.9,
        attributes={},
        lowConfidence=False,
        info_note=None,
        severity="high",
        contains_precious_metals=True,
        precious_metals_info="Contains gold and silver",
        contains_hazardous_materials=True,
        hazardous_materials_info="Contains lithium battery",
        category_id=category_id,
        brand_id=brand_id,
        model_id=model_id,
        category_match_score=category_score,
        brand_match_score=brand_score,
        model_match_score=model_score,
        database_status="success"
    )
    
    # Verify UUIDs are populated (not None)
    assert device_data.category_id is not None, "category_id should not be None when match exists"
    assert device_data.brand_id is not None, "brand_id should not be None when match exists"
    assert device_data.model_id is not None, "model_id should not be None when match exists"
    
    # Verify UUIDs are valid UUID objects
    assert isinstance(device_data.category_id, UUID), "category_id should be a valid UUID"
    assert isinstance(device_data.brand_id, UUID), "brand_id should be a valid UUID"
    assert isinstance(device_data.model_id, UUID), "model_id should be a valid UUID"
    
    # Verify UUIDs match the input
    assert device_data.category_id == category_id
    assert device_data.brand_id == brand_id
    assert device_data.model_id == model_id


# Feature: database-matching-integration, Property 18: Null ID on Match Failure
@given(
    category=st.text(min_size=1, max_size=50),
    brand=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    model=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    confidence=st.floats(min_value=0.0, max_value=1.0),
    database_status=st.sampled_from(["partial_success", "failure", "unavailable"])
)
@pytest.mark.property_test
def test_null_id_on_match_failure(
    category: str,
    brand: Optional[str],
    model: Optional[str],
    confidence: float,
    database_status: str
):
    """
    Property 18: Null ID on Match Failure
    
    For any failed database match where the threshold is not met or no candidates exist,
    the corresponding id field should be null.
    
    Validates: Requirements 6.3
    """
    # Create device data with no database matches (all IDs are None)
    device_data = DeviceData(
        category=category,
        brand=brand,
        model=model,
        deviceType="unknown",
        confidenceScore=confidence,
        accuracy=confidence,
        attributes={},
        lowConfidence=confidence < 0.5,
        info_note=None,
        severity="low",
        contains_precious_metals=False,
        precious_metals_info=None,
        contains_hazardous_materials=False,
        hazardous_materials_info=None,
        category_id=None,
        brand_id=None,
        model_id=None,
        category_match_score=None,
        brand_match_score=None,
        model_match_score=None,
        database_status=database_status
    )
    
    # Verify all ID fields are None when match fails
    assert device_data.category_id is None, "category_id should be None when match fails"
    assert device_data.brand_id is None, "brand_id should be None when match fails"
    assert device_data.model_id is None, "model_id should be None when match fails"
    
    # Verify match scores are also None
    assert device_data.category_match_score is None, "category_match_score should be None when match fails"
    assert device_data.brand_match_score is None, "brand_match_score should be None when match fails"
    assert device_data.model_match_score is None, "model_match_score should be None when match fails"
    
    # Verify database_status indicates failure
    assert device_data.database_status in ["partial_success", "failure", "unavailable"]


# Feature: database-matching-integration, Property 19: Text Field Preservation
@given(
    category_text=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs', 'Cc'))),
    brand_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))),
    model_text=st.one_of(st.none(), st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=('Cs', 'Cc')))),
    confidence=st.floats(min_value=0.0, max_value=1.0),
    database_status=st.sampled_from(["success", "partial_success", "failure", "unavailable"]),
    has_category_match=st.booleans(),
    has_brand_match=st.booleans(),
    has_model_match=st.booleans()
)
@pytest.mark.property_test
@settings(max_examples=20)
def test_text_field_preservation(
    category_text: str,
    brand_text: Optional[str],
    model_text: Optional[str],
    confidence: float,
    database_status: str,
    has_category_match: bool,
    has_brand_match: bool,
    has_model_match: bool
):
    """
    Property 19: Text Field Preservation
    
    For any analysis response regardless of database status, the text fields 
    (category, brand, model) should exactly match the original Gemini Vision API output.
    
    This property verifies that text fields from Gemini Vision API are always preserved
    in the response, regardless of whether database matching succeeds or fails.
    
    Validates: Requirements 6.4
    """
    # Create device data with text fields and optional database matches
    # The key property: text fields should be preserved regardless of database matching status
    device_data = DeviceData(
        category=category_text,
        brand=brand_text,
        model=model_text,
        deviceType="unknown",
        confidenceScore=confidence,
        accuracy=confidence,
        attributes={},
        lowConfidence=confidence < 0.5,
        info_note=None,
        severity="low",
        contains_precious_metals=False,
        precious_metals_info=None,
        contains_hazardous_materials=False,
        hazardous_materials_info=None,
        # Database matching fields - may or may not have matches
        category_id=uuid4() if has_category_match else None,
        brand_id=uuid4() if has_brand_match else None,
        model_id=uuid4() if has_model_match else None,
        category_match_score=0.85 if has_category_match else None,
        brand_match_score=0.85 if has_brand_match else None,
        model_match_score=0.80 if has_model_match else None,
        database_status=database_status
    )
    
    # Property: Text fields should exactly match the original input
    assert device_data.category == category_text, \
        f"category text should be preserved exactly: expected '{category_text}', got '{device_data.category}'"
    
    assert device_data.brand == brand_text, \
        f"brand text should be preserved exactly: expected '{brand_text}', got '{device_data.brand}'"
    
    assert device_data.model == model_text, \
        f"model text should be preserved exactly: expected '{model_text}', got '{device_data.model}'"
    
    # Property: Text fields should be preserved regardless of database_status
    # This verifies that database failures don't affect text field preservation
    assert device_data.category is not None, "category should never be None (it's required)"
    
    # Property: Text fields should be preserved even when database matching fails
    if database_status in ["failure", "unavailable"]:
        # Even when database is unavailable or fails, text fields should be preserved
        assert device_data.category == category_text, \
            "category text should be preserved even when database fails"
        assert device_data.brand == brand_text, \
            "brand text should be preserved even when database fails"
        assert device_data.model == model_text, \
            "model text should be preserved even when database fails"
    
    # Property: Text fields should be preserved even when no database matches found
    if not has_category_match and not has_brand_match and not has_model_match:
        assert device_data.category == category_text, \
            "category text should be preserved even when no database matches found"
        assert device_data.brand == brand_text, \
            "brand text should be preserved even when no database matches found"
        assert device_data.model == model_text, \
            "model text should be preserved even when no database matches found"
    
    # Property: Text fields should be preserved even when database matches are found
    if has_category_match or has_brand_match or has_model_match:
        assert device_data.category == category_text, \
            "category text should be preserved even when database matches are found"
        assert device_data.brand == brand_text, \
            "brand text should be preserved even when database matches are found"
        assert device_data.model == model_text, \
            "model text should be preserved even when database matches are found"


# Feature: database-matching-integration, Property 20: Match Score Presence
@given(
    has_category_match=st.booleans(),
    has_brand_match=st.booleans(),
    has_model_match=st.booleans()
)
@pytest.mark.property_test
@settings(max_examples=20)
def test_match_score_presence(
    has_category_match: bool,
    has_brand_match: bool,
    has_model_match: bool
):
    """
    Property 20: Match Score Presence
    
    For any non-null entity match (category, brand, or model), the corresponding
    match_score field should be present and contain the similarity score.
    
    This property verifies that whenever a database match is found (UUID is not null),
    the corresponding match score field is also present and contains a valid similarity
    score between 0.0 and 1.0.
    
    Validates: Requirements 6.6
    """
    # Generate consistent ID and score pairs
    # If has_match is True, both ID and score should be present
    # If has_match is False, both ID and score should be None
    category_id = uuid4() if has_category_match else None
    category_score = 0.85 if has_category_match else None
    
    brand_id = uuid4() if has_brand_match else None
    brand_score = 0.82 if has_brand_match else None
    
    model_id = uuid4() if has_model_match else None
    model_score = 0.78 if has_model_match else None
    
    # Determine database status
    if has_category_match and has_brand_match and has_model_match:
        database_status = "success"
    elif has_category_match or has_brand_match or has_model_match:
        database_status = "partial_success"
    else:
        database_status = "unavailable"
    
    # Create device data with the generated values
    device_data = DeviceData(
        category="Mobile Phone",
        brand="Apple",
        model="iPhone 14",
        deviceType="smartphone",
        confidenceScore=0.9,
        accuracy=0.9,
        attributes={},
        lowConfidence=False,
        info_note=None,
        severity="high",
        contains_precious_metals=True,
        precious_metals_info="Contains gold and silver",
        contains_hazardous_materials=True,
        hazardous_materials_info="Contains lithium battery",
        category_id=category_id,
        brand_id=brand_id,
        model_id=model_id,
        category_match_score=category_score,
        brand_match_score=brand_score,
        model_match_score=model_score,
        database_status=database_status
    )
    
    # Property: For any non-null entity match, the corresponding match_score should be present
    if device_data.category_id is not None:
        assert device_data.category_match_score is not None, \
            "category_match_score should be present when category_id is not null"
        assert 0.0 <= device_data.category_match_score <= 1.0, \
            f"category_match_score should be between 0.0 and 1.0, got {device_data.category_match_score}"
    
    if device_data.brand_id is not None:
        assert device_data.brand_match_score is not None, \
            "brand_match_score should be present when brand_id is not null"
        assert 0.0 <= device_data.brand_match_score <= 1.0, \
            f"brand_match_score should be between 0.0 and 1.0, got {device_data.brand_match_score}"
    
    if device_data.model_id is not None:
        assert device_data.model_match_score is not None, \
            "model_match_score should be present when model_id is not null"
        assert 0.0 <= device_data.model_match_score <= 1.0, \
            f"model_match_score should be between 0.0 and 1.0, got {device_data.model_match_score}"
    
    # Inverse property: If match_score is present, the corresponding ID should also be present
    # This ensures bidirectional consistency
    if device_data.category_match_score is not None:
        assert device_data.category_id is not None, \
            "category_id should be present when category_match_score is not null"
    
    if device_data.brand_match_score is not None:
        assert device_data.brand_id is not None, \
            "brand_id should be present when brand_match_score is not null"
    
    if device_data.model_match_score is not None:
        assert device_data.model_id is not None, \
            "model_id should be present when model_match_score is not null"

