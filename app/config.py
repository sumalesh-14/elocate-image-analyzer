"""
Configuration module for the Image Device Identification Service.
Loads environment variables and provides application settings.
"""

import os
import re
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from urllib.parse import urlparse, parse_qs


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_KEYS: Optional[str] = None
    OPENAI_API_KEYS: Optional[str] = None
    GROQ_API_KEYS: Optional[str] = None
    API_KEY: str
    
    # CORS Configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 10
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Request Configuration
    REQUEST_TIMEOUT: int = 30
    
    # Rate Limiting
    RATE_LIMIT: str = "10/minute"
    
    # Image Analysis LLM Priority Order
    IMAGE_ANALYSIS_LLM_PRIORITY: str = "gemini,openai,groq"
    
    # Material Analysis LLM Priority Order
    MATERIAL_ANALYSIS_LLM_PRIORITY: str = "groq,gemini,openai"
    
    # Chat (EcoBot) LLM Priority Order
    CHAT_LLM_PRIORITY: str = "groq,gemini,openai"
    
    # Database Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "elocate"
    DB_USER: str = "analyzer_readonly"
    DB_PASSWORD: str = ""
    DB_SSL_MODE: str = "require"
    DB_MIN_POOL_SIZE: int = 5
    DB_MAX_POOL_SIZE: int = 20
    DB_CONNECTION_TIMEOUT: int = 60
    DB_QUERY_TIMEOUT: int = 50  # milliseconds
    
    # Optional: Full JDBC URL (will override individual DB settings if provided)
    DATABASE_URL: Optional[str] = None
    
    # Flag to make database optional
    DB_REQUIRED: bool = False  # Set to True in production
    
    # Fuzzy Matching Thresholds
    CATEGORY_MATCH_THRESHOLD: float = 0.80
    BRAND_MATCH_THRESHOLD: float = 0.80
    MODEL_MATCH_THRESHOLD: float = 0.75
    
    # Cache Configuration
    QUERY_CACHE_TTL: int = 300  # 5 minutes
    QUERY_CACHE_MAX_SIZE: int = 1000
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MAX_FILE_SIZE_MB to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS comma-separated string into list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    @property
    def gemini_api_keys_list(self) -> List[str]:
        """Parse GEMINI_API_KEYS into list, falling back to GEMINI_API_KEY if not set."""
        if self.GEMINI_API_KEYS:
            return [key.strip() for key in self.GEMINI_API_KEYS.split(",") if key.strip()]
        if self.GEMINI_API_KEY:
            return [self.GEMINI_API_KEY]
        return []
        
    @property
    def openai_api_keys_list(self) -> List[str]:
        """Parse OPENAI_API_KEYS into list."""
        if self.OPENAI_API_KEYS:
            return [key.strip() for key in self.OPENAI_API_KEYS.split(",") if key.strip()]
        return []
        
    @property
    def groq_api_keys_list(self) -> List[str]:
        """Parse GROQ_API_KEYS into list."""
        if self.GROQ_API_KEYS:
            return [key.strip() for key in self.GROQ_API_KEYS.split(",") if key.strip()]
        return []
    
    @property
    def chat_llm_priority_list(self) -> List[str]:
        """Parse CHAT_LLM_PRIORITY into list of provider names."""
        return [p.strip().lower() for p in self.CHAT_LLM_PRIORITY.split(",") if p.strip()]

    @property
    def material_analysis_llm_priority_list(self) -> List[str]:
        """Parse MATERIAL_ANALYSIS_LLM_PRIORITY into list of provider names."""
        if self.MATERIAL_ANALYSIS_LLM_PRIORITY:
            return [provider.strip().lower() for provider in self.MATERIAL_ANALYSIS_LLM_PRIORITY.split(",") if provider.strip()]
        return ["groq", "gemini", "openai"]  # Default order
    
    @property
    def image_analysis_llm_priority_list(self) -> List[str]:
        """Parse IMAGE_ANALYSIS_LLM_PRIORITY into list of provider names."""
        if self.IMAGE_ANALYSIS_LLM_PRIORITY:
            return [provider.strip().lower() for provider in self.IMAGE_ANALYSIS_LLM_PRIORITY.split(",") if provider.strip()]
        return ["gemini", "openai", "groq"]  # Default order
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @field_validator('DB_MIN_POOL_SIZE', 'DB_MAX_POOL_SIZE')
    @classmethod
    def validate_pool_size(cls, v: int, info) -> int:
        """Validate pool size is positive."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v
    
    @field_validator('DB_MAX_POOL_SIZE')
    @classmethod
    def validate_max_pool_size(cls, v: int, info) -> int:
        """Validate max pool size is greater than min."""
        # Note: This validator runs after validate_pool_size
        # We'll check the relationship in model_validator
        return v
    
    @field_validator('CATEGORY_MATCH_THRESHOLD', 'BRAND_MATCH_THRESHOLD', 'MODEL_MATCH_THRESHOLD')
    @classmethod
    def validate_threshold(cls, v: float, info) -> float:
        """Validate threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{info.field_name} must be between 0.0 and 1.0")
        return v
    
    @field_validator('QUERY_CACHE_TTL', 'QUERY_CACHE_MAX_SIZE')
    @classmethod
    def validate_cache_config(cls, v: int, info) -> int:
        """Validate cache configuration is positive."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive")
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate configuration after model initialization."""
        if self.DB_MAX_POOL_SIZE < self.DB_MIN_POOL_SIZE:
            raise ValueError("DB_MAX_POOL_SIZE must be greater than or equal to DB_MIN_POOL_SIZE")
        
        # Parse DATABASE_URL if provided (JDBC format support)
        if self.DATABASE_URL:
            self._parse_database_url()
    
    def _parse_database_url(self) -> None:
        """Parse JDBC or PostgreSQL URL and extract connection parameters."""
        url = self.DATABASE_URL
        
        # Handle JDBC URL format: jdbc:postgresql://host:port/database?params
        if url.startswith('jdbc:postgresql://'):
            url = url.replace('jdbc:postgresql://', 'postgresql://')
        elif url.startswith('jdbc:'):
            # Strip jdbc: prefix for other formats
            url = url[5:]
        
        # Parse the URL
        try:
            # Format: postgresql://user:password@host:port/database?params
            # or: postgresql://host:port/database?params (credentials in query params)
            
            parsed = urlparse(url)
            
            # Extract host and port
            if parsed.hostname:
                self.DB_HOST = parsed.hostname
            if parsed.port:
                self.DB_PORT = parsed.port
            
            # Extract database name (remove leading slash)
            if parsed.path:
                self.DB_NAME = parsed.path.lstrip('/')
            
            # Extract username and password if in URL
            if parsed.username:
                self.DB_USER = parsed.username
            if parsed.password:
                self.DB_PASSWORD = parsed.password
            
            # Parse query parameters
            if parsed.query:
                params = parse_qs(parsed.query)
                
                # Extract SSL mode
                if 'sslmode' in params:
                    self.DB_SSL_MODE = params['sslmode'][0]
                
                # Extract user/password from query params if not in URL
                if 'user' in params and not parsed.username:
                    self.DB_USER = params['user'][0]
                if 'password' in params and not parsed.password:
                    self.DB_PASSWORD = params['password'][0]
        
        except Exception as e:
            raise ValueError(f"Failed to parse DATABASE_URL: {e}")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()



