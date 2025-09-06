"""
Helper utilities for video processing platform.
"""

import uuid
import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


def generate_video_id() -> str:
    """
    Generate a unique video ID.
    
    Returns:
        Unique video ID string
    """
    return str(uuid.uuid4())


def generate_job_id() -> str:
    """
    Generate a unique job ID.
    
    Returns:
        Unique job ID string
    """
    return str(uuid.uuid4())


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def calculate_processing_time(
    file_size: int,
    resolution: str = "1080p",
    quality: str = "high"
) -> int:
    """
    Calculate estimated processing time in minutes.
    
    Args:
        file_size: File size in bytes
        resolution: Output resolution
        quality: Output quality
        
    Returns:
        Estimated processing time in minutes
    """
    # Base processing time in minutes per GB
    base_time_per_gb = 5
    
    # Quality multipliers
    quality_multipliers = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
        "ultra": 2.0
    }
    
    # Resolution multipliers
    resolution_multipliers = {
        "720p": 0.5,
        "1080p": 1.0,
        "1440p": 1.5,
        "4K": 2.5
    }
    
    # Calculate estimated time
    file_size_gb = file_size / (1024 ** 3)
    base_time = file_size_gb * base_time_per_gb
    quality_multiplier = quality_multipliers.get(quality, 1.0)
    resolution_multiplier = resolution_multipliers.get(resolution, 1.0)
    
    estimated_time = int(base_time * quality_multiplier * resolution_multiplier)
    
    # Minimum processing time
    return max(estimated_time, 2)


def generate_file_hash(file_path: str) -> str:
    """
    Generate MD5 hash for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace dangerous characters
    dangerous_chars = '<>:"/\\|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = f"file_{int(time.time())}"
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_length] + (f'.{ext}' if ext else '')
    
    return filename


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Filename
        
    Returns:
        File extension (without dot)
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ""


def is_video_file(filename: str) -> bool:
    """
    Check if file is a video based on extension.
    
    Args:
        filename: Filename to check
        
    Returns:
        True if video file, False otherwise
    """
    video_extensions = {
        'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'm4v', '3gp', 'ogv'
    }
    extension = get_file_extension(filename)
    return extension in video_extensions


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (HH:MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_utc_timestamp() -> datetime:
    """
    Get current UTC timestamp.
    
    Returns:
        Current UTC datetime
    """
    return datetime.utcnow()


def add_timezone_offset(dt: datetime, hours: int = 0) -> datetime:
    """
    Add timezone offset to datetime.
    
    Args:
        dt: Datetime object
        hours: Hours to add (can be negative)
        
    Returns:
        Datetime with offset applied
    """
    return dt + timedelta(hours=hours)


def create_expiration_time(minutes: int = 60) -> datetime:
    """
    Create expiration time from current time.
    
    Args:
        minutes: Minutes from now
        
    Returns:
        Expiration datetime
    """
    return datetime.utcnow() + timedelta(minutes=minutes)


def is_expired(expiration_time: datetime) -> bool:
    """
    Check if expiration time has passed.
    
    Args:
        expiration_time: Expiration datetime
        
    Returns:
        True if expired, False otherwise
    """
    return datetime.utcnow() > expiration_time


def chunk_list(lst: list, chunk_size: int) -> list:
    """
    Split list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely get value from dictionary.
    
    Args:
        dictionary: Dictionary to get value from
        key: Key to get
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    return dictionary.get(key, default)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
