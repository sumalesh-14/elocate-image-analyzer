"""
Material analysis models for device recycling value estimation.

These models define the request/response structure for analyzing
precious and recyclable materials in electronic devices.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID


class MaterialAnalysisRequest(BaseModel):
    """Request model for material analysis endpoint.
    
    Attributes:
        brand_id: Brand identifier
        brand_name: Brand name
        category_id: Category identifier
        category_name: Category name (e.g., Smartphone, Laptop)
        model_id: Model identifier
        model_name: Model name
        country: Country code or name for market rate lookup
        description: Optional additional context about the device
    """
    brand_id: str = Field(..., description="Brand identifier")
    brand_name: str = Field(..., description="Brand name")
    category_id: str = Field(..., description="Category identifier")
    category_name: str = Field(..., description="Category name")
    model_id: str = Field(..., description="Model identifier")
    model_name: str = Field(..., description="Model name")
    country: str = Field(..., description="Country for market rate lookup")
    description: Optional[str] = Field(None, description="Additional device context")
    
    @field_validator('brand_name', 'category_name', 'model_name', 'country')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate required string fields are not empty."""
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class MaterialData(BaseModel):
    """Individual material information.
    
    Attributes:
        material_name: Name of the material (e.g., Gold, Silver, Copper)
        is_precious: Whether this is a precious metal
        estimated_quantity_grams: Estimated quantity in grams
        market_rate_per_gram: Current market rate per gram
        currency: Currency code (e.g., INR, USD)
        found_in: Component/part where this material is typically found
    """
    material_name: str = Field(..., alias="materialName", description="Material name")
    is_precious: bool = Field(..., alias="isPrecious", description="Is precious metal")
    estimated_quantity_grams: float = Field(
        ..., 
        alias="estimatedQuantityGrams",
        ge=0.0,
        description="Estimated quantity in grams"
    )
    market_rate_per_gram: float = Field(
        ...,
        alias="marketRatePerGram",
        ge=0.0,
        description="Market rate per gram"
    )
    currency: str = Field(..., description="Currency code")
    found_in: str = Field(..., alias="foundIn", description="Component where material is found")
    
    class Config:
        populate_by_name = True
    
    @field_validator('material_name', 'currency', 'found_in')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate string fields are not empty."""
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class BrandInfo(BaseModel):
    """Brand information."""
    id: str = Field(..., description="Brand identifier")
    name: str = Field(..., description="Brand name")


class CategoryInfo(BaseModel):
    """Category information."""
    id: str = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")


class ModelInfo(BaseModel):
    """Model information."""
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Model name")


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis process."""
    llm_model: str = Field(..., alias="llmModel", description="LLM model used")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        alias="analysisTimestamp",
        description="Analysis timestamp"
    )
    
    class Config:
        populate_by_name = True


class MaterialAnalysisData(BaseModel):
    """Material analysis result data.
    
    Attributes:
        brand: Brand information
        category: Category information
        model: Model information
        country: Country for market rates
        analysis_description: Description of the analysis
        materials: List of materials found in the device
        metadata: Analysis metadata
    """
    brand: BrandInfo = Field(..., description="Brand information")
    category: CategoryInfo = Field(..., description="Category information")
    model: ModelInfo = Field(..., description="Model information")
    country: str = Field(..., description="Country for market rates")
    analysis_description: str = Field(
        ...,
        alias="analysisDescription",
        description="Analysis description"
    )
    materials: List[MaterialData] = Field(..., description="List of materials")
    metadata: AnalysisMetadata = Field(..., description="Analysis metadata")
    
    class Config:
        populate_by_name = True
    
    @field_validator('materials')
    @classmethod
    def validate_materials_not_empty(cls, v: List[MaterialData]) -> List[MaterialData]:
        """Validate materials list is not empty."""
        if not v:
            raise ValueError('Materials list cannot be empty')
        return v


class MaterialAnalysisResponse(BaseModel):
    """Response model for material analysis endpoint.
    
    Attributes:
        success: Operation success status
        timestamp: Response timestamp
        processing_time_ms: Processing duration in milliseconds
        data: Material analysis data on success
        error: Error information on failure
    """
    success: bool = Field(..., description="Operation success status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    processing_time_ms: int = Field(
        ...,
        alias="processingTimeMs",
        ge=0,
        description="Processing duration in milliseconds"
    )
    data: Optional[MaterialAnalysisData] = Field(None, description="Analysis data")
    error: Optional[dict] = Field(None, description="Error information")
    
    class Config:
        populate_by_name = True
