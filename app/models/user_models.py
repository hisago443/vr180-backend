"""
Authentication-related Pydantic models.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime


class UserRegister(BaseModel):
    """User registration request model."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    display_name: str = Field(..., min_length=2, max_length=50, description="User display name")
    
    @validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login request model."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserProfile(BaseModel):
    """User profile information model."""
    
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    display_name: str = Field(..., description="User display name")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    is_verified: bool = Field(False, description="Email verification status")
    subscription_tier: str = Field("free", description="User subscription tier")
    videos_processed: int = Field(0, description="Total videos processed")
    storage_used_mb: float = Field(0.0, description="Storage used in MB")


class AuthResponse(BaseModel):
    """Authentication response model."""
    
    user_id: str = Field(..., description="Unique user identifier")
    custom_token: str = Field(..., description="Firebase custom token")
    user_info: Optional[UserProfile] = Field(None, description="User profile information")
    expires_in: int = Field(3600, description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    
    user_id: str = Field(..., description="User ID from token")
    email: str = Field(..., description="Email from token")
    exp: int = Field(..., description="Token expiration timestamp")
    iat: int = Field(..., description="Token issued at timestamp")
    iss: str = Field(..., description="Token issuer")
    aud: str = Field(..., description="Token audience")
