"""
Pydantic models for VR 180 Video Processing Platform API.
"""

from .auth import (
    UserRegister,
    UserLogin,
    UserProfile,
    AuthResponse,
    TokenData
)
from .video import (
    VideoUpload,
    VideoUploadResponse,
    VideoConvert,
    VideoConvertResponse,
    VideoStatus,
    VideoInfo,
    VideoDownload,
    VideoPreview,
    VideoList,
    ConversionSettings
)
from .system import (
    HealthResponse,
    MetricsResponse,
    ErrorResponse
)

__all__ = [
    "UserRegister",
    "UserLogin", 
    "UserProfile",
    "AuthResponse",
    "TokenData",
    "VideoUpload",
    "VideoUploadResponse",
    "VideoConvert",
    "VideoConvertResponse",
    "VideoStatus",
    "VideoInfo",
    "VideoDownload",
    "VideoPreview",
    "VideoList",
    "ConversionSettings",
    "HealthResponse",
    "MetricsResponse",
    "ErrorResponse"
]
