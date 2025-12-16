"""
Aristosys Backend Configuration
Environment variables and settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    anthropic_api_key: str
    deepgram_api_key: str
    supabase_url: str
    supabase_key: str
    
    # Optional settings
    jwt_secret: Optional[str] = None
    cors_origins: str = "*"
    environment: str = "development"
    
    # API Settings
    api_title: str = "Aristosys API"
    api_version: str = "1.0.0"
    api_description: str = "AI-Powered Recruitment Screening Platform"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
