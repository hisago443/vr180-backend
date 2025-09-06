"""
Validation utilities for video processing platform.
"""

import re
from typing import Dict, Any, List
from fastapi import HTTPException, status

from app.config import get_settings


def validate_video_file(filename: str, content_type: str, file_size: int) -> Dict[str, Any]:
    """
    Validate video file parameters.
    
    Args:
        filename: Video filename
        content_type: MIME type
        file_size: File size in bytes
        
    Returns:
        Validation result dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    errors = []
    
    # Validate filename
    if not filename or len(filename) > 255:
        errors.append("Invalid filename")
    
    # Check for dangerous characters
    if re.search(r'[<>:"/\\|?*]', filename):
        errors.append("Filename contains invalid characters")
    
    # Get settings
    settings = get_settings()
    
    # Validate content type
    if content_type not in settings.allowed_video_formats:
        errors.append(f"Unsupported video format: {content_type}")
    
    # Validate file size
    if file_size <= 0:
        errors.append("File size must be greater than 0")
    elif file_size > settings.max_file_size_bytes:
        errors.append(f"File size exceeds maximum limit of {settings.max_file_size_mb}MB")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )
    
    return {
        "valid": True,
        "filename": filename,
        "content_type": content_type,
        "file_size": file_size
    }


def validate_conversion_settings(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate video conversion settings.
    
    Args:
        settings_dict: Conversion settings dictionary
        
    Returns:
        Validated settings dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    errors = []
    
    # Get settings
    settings = get_settings()
    
    # Validate resolution
    if "resolution" in settings_dict:
        resolution = settings_dict["resolution"]
        if resolution not in settings.supported_resolutions:
            errors.append(f"Unsupported resolution: {resolution}")
    
    # Validate quality
    if "quality" in settings_dict:
        quality = settings_dict["quality"]
        valid_qualities = ["low", "medium", "high", "ultra"]
        if quality not in valid_qualities:
            errors.append(f"Invalid quality setting: {quality}")
    
    # Validate frame rate
    if "frame_rate" in settings_dict:
        frame_rate = settings_dict["frame_rate"]
        if not isinstance(frame_rate, int) or frame_rate < 15 or frame_rate > 60:
            errors.append("Frame rate must be between 15 and 60 fps")
    
    # Validate bitrate
    if "bitrate" in settings_dict:
        bitrate = settings_dict["bitrate"]
        if not isinstance(bitrate, int) or bitrate < 1000 or bitrate > 50000:
            errors.append("Bitrate must be between 1000 and 50000 kbps")
    
    # Validate stereo mode
    if "stereo_mode" in settings_dict:
        stereo_mode = settings_dict["stereo_mode"]
        valid_modes = ["side-by-side", "top-bottom"]
        if stereo_mode not in valid_modes:
            errors.append(f"Invalid stereo mode: {stereo_mode}")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )
    
    return settings_dict


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> List[str]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return errors


def validate_user_input(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    Validate user input data.
    
    Args:
        data: Input data dictionary
        required_fields: List of required field names
        
    Returns:
        Validated data dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate string lengths
    string_fields = {
        "display_name": (2, 50),
        "title": (1, 100),
        "description": (0, 500)
    }
    
    for field, (min_len, max_len) in string_fields.items():
        if field in data:
            value = data[field]
            if isinstance(value, str):
                if len(value) < min_len:
                    errors.append(f"{field} must be at least {min_len} characters long")
                elif len(value) > max_len:
                    errors.append(f"{field} must be no more than {max_len} characters long")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )
    
    return data
