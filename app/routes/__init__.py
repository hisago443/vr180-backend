"""
API routes for VR 180 Video Processing Platform.
"""

from .auth import router as auth_router
from .videos import router as videos_router
from .system import router as system_router
from .internal import router as internal_router

__all__ = [
    "auth_router",
    "videos_router", 
    "system_router",
    "internal_router"
]
