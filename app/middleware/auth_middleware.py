"""
Authentication middleware for Firebase JWT token validation.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.firebase_service import firebase_service
from app.models.auth import TokenData

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for Firebase JWT validation."""
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        """
        Initialize authentication middleware.
        
        Args:
            app: FastAPI application
            excluded_paths: List of paths to exclude from authentication
        """
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login"
        ]
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate authentication.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler
        """
        # Skip authentication for excluded paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)
        
        try:
            # Extract token from Authorization header
            token = await self._extract_token(request)
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization token required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Verify token with Firebase
            token_data = await firebase_service.verify_token(token)
            
            # Add user context to request state
            request.state.user_id = token_data.user_id
            request.state.user_email = token_data.email
            request.state.token_data = token_data
            
            logger.debug(f"User authenticated: {token_data.user_id}")
            
            # Continue to next handler
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def _should_skip_auth(self, path: str) -> bool:
        """
        Check if path should skip authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if authentication should be skipped
        """
        # Check exact matches
        if path in self.excluded_paths:
            return True
        
        # Check if path starts with excluded prefix
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        
        return False
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request.
        
        Args:
            request: Incoming request
            
        Returns:
            JWT token string or None
        """
        # Try Authorization header first
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.split(" ")[1]
        
        # Try query parameter (for WebSocket connections)
        token = request.query_params.get("token")
        if token:
            return token
        
        return None


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    """Optional authentication middleware that doesn't require auth but adds user context if available."""
    
    def __init__(self, app):
        """Initialize optional authentication middleware."""
        super().__init__(app)
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with optional authentication.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler
        """
        try:
            # Try to extract and verify token
            token = await self._extract_token(request)
            
            if token:
                try:
                    token_data = await firebase_service.verify_token(token)
                    request.state.user_id = token_data.user_id
                    request.state.user_email = token_data.email
                    request.state.token_data = token_data
                    request.state.authenticated = True
                    
                    logger.debug(f"Optional auth successful: {token_data.user_id}")
                except Exception as e:
                    logger.debug(f"Optional auth failed: {e}")
                    request.state.authenticated = False
            else:
                request.state.authenticated = False
            
            # Continue to next handler
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Optional authentication error: {e}")
            request.state.authenticated = False
            response = await call_next(request)
            return response
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request.
        
        Args:
            request: Incoming request
            
        Returns:
            JWT token string or None
        """
        # Try Authorization header first
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            return authorization.split(" ")[1]
        
        # Try query parameter
        token = request.query_params.get("token")
        if token:
            return token
        
        return None


def get_current_user(request: Request) -> TokenData:
    """
    Get current authenticated user from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        TokenData object with user information
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, 'token_data'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return request.state.token_data


def get_current_user_id(request: Request) -> str:
    """
    Get current user ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID string
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, 'user_id'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return request.state.user_id


def get_current_user_email(request: Request) -> str:
    """
    Get current user email from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User email string
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, 'user_email'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    return request.state.user_email


def is_authenticated(request: Request) -> bool:
    """
    Check if user is authenticated.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if user is authenticated, False otherwise
    """
    return hasattr(request.state, 'authenticated') and request.state.authenticated
