"""
Response models for the Image Device Identification API.

These Pydantic models define the structured response format for the API,
ensuring type safety and validation.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, field_serializer
from typing import Optional, Dict, Literal
from datetime import datetime
from uuid import UUID


class DeviceData(BaseModel):
    """Device identification data extracted from image analysis.
    
    Attributes:
        category: Device category (mobile, laptop, etc.)
        brand: Brand name or null if uncertain
        model: Model name or null if uncertain
        deviceType: Device type or sub-category
        confidenceScore: Confidence score between 0.0 and 1.0
        accuracy: AI confidence level (matches confidenceScore)
        attributes: Visible device attributes useful for database matching
        lowConfidence: Flag indicating if confidence < 0.5
        info_note: Optional contextual information about the device
        severity: Disposal risk severity level
        contains_precious_metals: Whether device contains valuable metals
        precious_metals_info: Details about precious metal content
        contains_hazardous_materials: Whether device contains dangerous substances
        hazardous_materials_info: Details about hazardous materials
    """
    model_config = ConfigDict(protected_namespaces=())
    
    category: str = Field(..., description="Device category (mobile, laptop, etc.)")
    brand: Optional[str] = Field(None, description="Brand name or null if uncertain")
    model: Optional[str] = Field(None, description="Model name or null if uncertain")
    deviceType: str = Field(..., description="Device type or sub-category")
    confidenceScore: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score 0.0-1.0"
    )
    accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence level (matches confidenceScore)"
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict, 
        description="Visible device attributes"
    )
    lowConfidence: bool = Field(
        False, 
        description="Flag if confidence < 0.5"
    )
    
    # Enhanced safety and material information fields
    info_note: Optional[str] = Field(
        None,
        max_length=500,
        description="Contextual recycling information"
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Disposal risk severity level"
    )
    contains_precious_metals: bool = Field(
        ...,
        description="Whether device contains valuable metals"
    )
    precious_metals_info: Optional[str] = Field(
        None,
        max_length=300,
        description="Details about precious metal content"
    )
    contains_hazardous_materials: bool = Field(
        ...,
        description="Whether device contains dangerous substances"
    )
    hazardous_materials_info: Optional[str] = Field(
        None,
        max_length=300,
        description="Details about hazardous materials"
    )
    
    # Database matching fields
    category_id: Optional[UUID] = Field(
        None,
        description="Database UUID for matched category"
    )
    brand_id: Optional[UUID] = Field(
        None,
        description="Database UUID for matched brand"
    )
    model_id: Optional[UUID] = Field(
        None,
        description="Database UUID for matched model"
    )
    category_match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Category fuzzy match score (0.0-1.0)"
    )
    brand_match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Brand fuzzy match score (0.0-1.0)"
    )
    model_match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model fuzzy match score (0.0-1.0)"
    )
    database_status: Literal["success", "partial_success", "failure", "unavailable"] = Field(
        "unavailable",
        description="Database matching status: success (all matches found), partial_success (some matches found), failure (query failed), unavailable (database not connected)"
    )
    
    @field_validator('confidenceScore', 'accuracy')
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Validate score is between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Score must be between 0.0 and 1.0')
        return v
    
    @field_validator('info_note')
    @classmethod
    def validate_info_note_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate info_note length does not exceed 500 characters."""
        if v is not None and len(v) > 500:
            raise ValueError('info_note must not exceed 500 characters')
        return v
    
    @field_validator('precious_metals_info')
    @classmethod
    def validate_precious_metals_info_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate precious_metals_info length does not exceed 300 characters."""
        if v is not None and len(v) > 300:
            raise ValueError('precious_metals_info must not exceed 300 characters')
        return v
    
    @field_validator('hazardous_materials_info')
    @classmethod
    def validate_hazardous_materials_info_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate hazardous_materials_info length does not exceed 300 characters."""
        if v is not None and len(v) > 300:
            raise ValueError('hazardous_materials_info must not exceed 300 characters')
        return v
    
    @model_validator(mode='after')
    def validate_conditional_fields(self) -> 'DeviceData':
        """Validate conditional field presence and accuracy equals confidenceScore."""
        # Validate precious_metals_info only present when contains_precious_metals is true
        if not self.contains_precious_metals and self.precious_metals_info is not None:
            raise ValueError('precious_metals_info should only be present when contains_precious_metals is true')
        
        # Validate hazardous_materials_info only present when contains_hazardous_materials is true
        if not self.contains_hazardous_materials and self.hazardous_materials_info is not None:
            raise ValueError('hazardous_materials_info should only be present when contains_hazardous_materials is true')
        
        # Validate accuracy equals confidenceScore
        if abs(self.accuracy - self.confidenceScore) > 1e-9:  # Use small epsilon for float comparison
            raise ValueError('accuracy must equal confidenceScore')
        
        return self
    
    def model_post_init(self, __context) -> None:
        """Set lowConfidence flag based on confidenceScore after initialization."""
        if self.confidenceScore < 0.5:
            object.__setattr__(self, 'lowConfidence', True)


class ErrorData(BaseModel):
    """Error information for failed requests.
    
    Attributes:
        code: Error code identifying the type of error
        message: Human-readable error message
    """
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")


class IdentificationResponse(BaseModel):
    """Standard API response for device identification requests.
    
    Attributes:
        success: Operation success status
        timestamp: Response timestamp in ISO 8601 format
        processingTimeMs: Processing duration in milliseconds
        data: Device data on success (null on failure)
        error: Error data on failure (null on success)
    """
    success: bool = Field(..., description="Operation success status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Response timestamp"
    )
    processingTimeMs: int = Field(..., description="Processing duration in milliseconds")
    data: Optional[DeviceData] = Field(None, description="Device data on success")
    error: Optional[ErrorData] = Field(None, description="Error data on failure")
    
    @field_validator('processingTimeMs')
    @classmethod
    def validate_processing_time(cls, v: int) -> int:
        """Validate processing time is non-negative."""
        if v < 0:
            raise ValueError('processingTimeMs must be non-negative')
        return v
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime) -> str:
        """Serialize timestamp to ISO 8601 format."""
        return timestamp.isoformat()


class HealthResponse(BaseModel):
    """Health check response for monitoring service availability.
    
    Attributes:
        status: Service status (healthy, degraded, unhealthy)
        timestamp: Response timestamp
        gemini_api_available: Gemini API connectivity status
        database_available: Database connectivity status
    """
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    gemini_api_available: bool = Field(
        ..., 
        description="Gemini API connectivity"
    )
    database_available: bool = Field(
        ...,
        description="Database connectivity status"
    )
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime) -> str:
        """Serialize timestamp to ISO 8601 format."""
        return timestamp.isoformat()
