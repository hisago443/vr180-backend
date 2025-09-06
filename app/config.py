"""
Configuration management for VR 180 Video Processing Platform.
Handles environment variables and application settings.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "VR 180 Video Processing Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Firebase Configuration
    firebase_project_id: str
    firebase_service_account_key_path: Optional[str] = None
    firebase_service_account_key_json: Optional[str] = None
    
    # Google Cloud Configuration
    google_cloud_project_id: str
    google_cloud_storage_bucket: str
    google_cloud_region: str = "us-central1"
    
    # CORS Configuration
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Security
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # File Upload Limits
    max_file_size_mb: int = 500
    max_file_size_bytes: int = 500 * 1024 * 1024
    allowed_video_formats: List[str] = ["video/mp4", "video/avi", "video/mov", "video/mkv", "video/webm"]
    
    # Video Processing
    max_concurrent_jobs: int = 5
    job_timeout_minutes: int = 60
    default_video_quality: str = "high"
    supported_resolutions: List[str] = ["720p", "1080p", "1440p", "4K"]
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_upload_per_hour: int = 10
    rate_limit_convert_per_hour: int = 5
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    @validator("allowed_origins", pre=True)
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse comma-separated origins string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_video_formats", pre=True)
    @classmethod
    def parse_allowed_video_formats(cls, v):
        """Parse comma-separated video formats string."""
        if isinstance(v, str):
            return [format.strip() for format in v.split(",")]
        return v
    
    @validator("supported_resolutions", pre=True)
    @classmethod
    def parse_supported_resolutions(cls, v):
        """Parse comma-separated resolutions string."""
        if isinstance(v, str):
            return [resolution.strip() for resolution in v.split(",")]
        return v
    
    @validator("max_file_size_bytes", pre=True)
    @classmethod
    def calculate_max_file_size_bytes(cls, v, values):
        """Calculate max file size in bytes from MB."""
        if "max_file_size_mb" in values:
            return values["max_file_size_mb"] * 1024 * 1024
        return v
    
    @validator("debug", pre=True)
    @classmethod
    def parse_debug(cls, v):
        """Parse debug flag from string."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance (lazy initialization)
_settings = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
