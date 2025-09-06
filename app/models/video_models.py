"""
Video-related Pydantic models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class VideoStatusEnum(str, Enum):
    """Video processing status enumeration."""
    
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoQualityEnum(str, Enum):
    """Video quality enumeration."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class VideoResolutionEnum(str, Enum):
    """Video resolution enumeration."""
    
    SD_720P = "720p"
    HD_1080P = "1080p"
    QHD_1440P = "1440p"
    UHD_4K = "4K"


class ConversionSettings(BaseModel):
    """Video conversion settings model."""
    
    resolution: VideoResolutionEnum = Field(VideoResolutionEnum.HD_1080P, description="Output resolution")
    quality: VideoQualityEnum = Field(VideoQualityEnum.HIGH, description="Output quality")
    frame_rate: Optional[int] = Field(30, ge=15, le=60, description="Output frame rate")
    bitrate: Optional[int] = Field(None, ge=1000, le=50000, description="Output bitrate in kbps")
    stereo_mode: str = Field("side-by-side", description="Stereo mode for VR180")
    depth_estimation_model: str = Field("midas", description="Depth estimation model to use")


class VideoUpload(BaseModel):
    """Video upload request model."""
    
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content_type: str = Field(..., description="MIME type of the video file")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    title: Optional[str] = Field(None, max_length=100, description="Video title")
    description: Optional[str] = Field(None, max_length=500, description="Video description")
    
    @validator("content_type")
    @classmethod
    def validate_content_type(cls, v):
        """Validate video content type."""
        allowed_types = [
            "video/mp4",
            "video/avi", 
            "video/mov",
            "video/mkv",
            "video/webm",
            "video/quicktime"
        ]
        if v not in allowed_types:
            raise ValueError(f"Unsupported video format: {v}")
        return v


class VideoUploadResponse(BaseModel):
    """Video upload response model."""
    
    video_id: str = Field(..., description="Unique video identifier")
    signed_upload_url: str = Field(..., description="Signed URL for direct upload")
    upload_metadata: Dict[str, Any] = Field(..., description="Upload metadata")
    expires_at: datetime = Field(..., description="Upload URL expiration time")


class VideoConvert(BaseModel):
    """Video conversion request model."""
    
    video_id: str = Field(..., description="Video ID to convert")
    conversion_settings: ConversionSettings = Field(..., description="Conversion settings")
    priority: int = Field(1, ge=1, le=10, description="Job priority (1=low, 10=high)")


class VideoConvertResponse(BaseModel):
    """Video conversion response model."""
    
    job_id: str = Field(..., description="Unique job identifier")
    video_id: str = Field(..., description="Video ID being converted")
    estimated_time_minutes: int = Field(..., description="Estimated processing time")
    status: VideoStatusEnum = Field(..., description="Current job status")
    queue_position: Optional[int] = Field(None, description="Position in processing queue")


class VideoStatus(BaseModel):
    """Video processing status model."""
    
    job_id: str = Field(..., description="Job identifier")
    video_id: str = Field(..., description="Video identifier")
    status: VideoStatusEnum = Field(..., description="Current processing status")
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0, description="Processing progress")
    stage: str = Field(..., description="Current processing stage")
    eta_minutes: Optional[int] = Field(None, description="Estimated time to completion")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    created_at: datetime = Field(..., description="Job creation time")


class VideoInfo(BaseModel):
    """Video information model."""
    
    video_id: str = Field(..., description="Unique video identifier")
    user_id: str = Field(..., description="Owner user ID")
    title: Optional[str] = Field(None, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., description="File size in bytes")
    duration_seconds: Optional[float] = Field(None, description="Video duration")
    resolution: Optional[str] = Field(None, description="Original resolution")
    frame_rate: Optional[float] = Field(None, description="Original frame rate")
    original_url: Optional[str] = Field(None, description="Original video URL")
    converted_url: Optional[str] = Field(None, description="Converted VR180 video URL")
    thumbnail_url: Optional[str] = Field(None, description="Video thumbnail URL")
    preview_url: Optional[str] = Field(None, description="VR preview URL")
    status: VideoStatusEnum = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    conversion_settings: Optional[ConversionSettings] = Field(None, description="Conversion settings used")


class VideoDownload(BaseModel):
    """Video download response model."""
    
    download_url: str = Field(..., description="Signed download URL")
    filename: str = Field(..., description="Download filename")
    content_type: str = Field(..., description="File MIME type")
    file_size: int = Field(..., description="File size in bytes")
    expires_at: datetime = Field(..., description="Download URL expiration time")


class VideoPreview(BaseModel):
    """Video preview response model."""
    
    preview_url: str = Field(..., description="VR preview player URL")
    thumbnail_url: str = Field(..., description="Video thumbnail URL")
    metadata: Dict[str, Any] = Field(..., description="Preview metadata")
    vr_player_config: Dict[str, Any] = Field(..., description="VR player configuration")


class VideoList(BaseModel):
    """User video list response model."""
    
    videos: List[VideoInfo] = Field(..., description="List of user videos")
    total_count: int = Field(..., description="Total number of videos")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(20, description="Videos per page")
    has_next: bool = Field(False, description="Whether there are more pages")
