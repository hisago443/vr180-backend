"""
Authentication API routes.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer

from app.models.auth import UserRegister, UserLogin, UserProfile, AuthResponse
from app.services.firebase_service import firebase_service
from app.middleware.auth_middleware import get_current_user, get_current_user_id
from app.models.auth import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=AuthResponse)
async def register_user(user_data: UserRegister) -> AuthResponse:
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        
    Returns:
        Authentication response with user info and token
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        logger.info(f"User registration attempt: {user_data.email}")
        
        # Create user in Firebase
        result = await firebase_service.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name
        )
        
        logger.info(f"User registered successfully: {result['user_id']}")
        
        return AuthResponse(
            user_id=result['user_id'],
            custom_token=result['custom_token'],
            user_info=result['user_info'],
            expires_in=3600
        )
        
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        
        # Handle specific Firebase errors
        error_message = str(e)
        if "email-already-exists" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email address is already registered"
            )
        elif "invalid-email" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address format"
            )
        elif "weak-password" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed. Please try again."
            )


@router.post("/login", response_model=AuthResponse)
async def login_user(login_data: UserLogin) -> AuthResponse:
    """
    Authenticate user and return token.
    
    Args:
        login_data: User login credentials
        
    Returns:
        Authentication response with user info and token
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        logger.info(f"User login attempt: {login_data.email}")
        
        # Authenticate user
        result = await firebase_service.authenticate_user(
            email=login_data.email,
            password=login_data.password
        )
        
        logger.info(f"User logged in successfully: {result['user_id']}")
        
        return AuthResponse(
            user_id=result['user_id'],
            custom_token=result['custom_token'],
            user_info=result['user_info'],
            expires_in=3600
        )
        
    except Exception as e:
        logger.error(f"User login failed: {e}")
        
        # Handle specific Firebase errors
        error_message = str(e)
        if "user-not-found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif "wrong-password" in error_message:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif "user-disabled" in error_message:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account has been disabled"
            )
        elif "too-many-requests" in error_message:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed. Please check your credentials."
            )


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> UserProfile:
    """
    Get current user's profile information.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        User profile information
        
    Raises:
        HTTPException: If user not found or authentication fails
    """
    try:
        logger.info(f"Getting user profile: {current_user.user_id}")
        
        # Get user profile from Firestore
        user_profile = await firebase_service.get_user_profile(current_user.user_id)
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        return user_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: Dict[str, Any],
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> UserProfile:
    """
    Update current user's profile information.
    
    Args:
        profile_data: Profile data to update
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Updated user profile information
        
    Raises:
        HTTPException: If update fails
    """
    try:
        logger.info(f"Updating user profile: {current_user.user_id}")
        
        # Validate allowed fields
        allowed_fields = {
            'display_name', 'subscription_tier'
        }
        
        filtered_data = {
            key: value for key, value in profile_data.items() 
            if key in allowed_fields
        }
        
        if not filtered_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update user profile
        success = await firebase_service.update_user_profile(
            current_user.user_id,
            filtered_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )
        
        # Get updated profile
        updated_profile = await firebase_service.get_user_profile(current_user.user_id)
        
        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found after update"
            )
        
        logger.info(f"User profile updated successfully: {current_user.user_id}")
        return updated_profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout user by revoking refresh tokens.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Logout confirmation message
        
    Raises:
        HTTPException: If logout fails
    """
    try:
        logger.info(f"User logout: {current_user.user_id}")
        
        # Revoke refresh tokens
        success = await firebase_service.revoke_refresh_tokens(current_user.user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to logout user"
            )
        
        logger.info(f"User logged out successfully: {current_user.user_id}")
        
        return {"message": "User logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to logout user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout user"
        )


@router.delete("/account")
async def delete_user_account(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Delete user account and all associated data.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Deletion confirmation message
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        logger.info(f"User account deletion: {current_user.user_id}")
        
        # Delete user from Firebase Auth and Firestore
        success = await firebase_service.delete_user(current_user.user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user account"
            )
        
        logger.info(f"User account deleted successfully: {current_user.user_id}")
        
        return {"message": "User account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )


@router.post("/refresh-token", response_model=AuthResponse)
async def refresh_token(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> AuthResponse:
    """
    Refresh user's authentication token.
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        New authentication response with refreshed token
        
    Raises:
        HTTPException: If token refresh fails
    """
    try:
        logger.info(f"Token refresh: {current_user.user_id}")
        
        # Create new custom token
        import firebase_admin.auth as auth
        custom_token = auth.create_custom_token(current_user.user_id)
        
        # Get user profile
        user_profile = await firebase_service.get_user_profile(current_user.user_id)
        
        logger.info(f"Token refreshed successfully: {current_user.user_id}")
        
        return AuthResponse(
            user_id=current_user.user_id,
            custom_token=custom_token.decode('utf-8'),
            user_info=user_profile,
            expires_in=3600
        )
        
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh authentication token"
        )
