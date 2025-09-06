"""
Video management API routes.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from fastapi.responses import JSONResponse

from app.models.video import (
    VideoUpload, VideoUploadResponse, VideoConvert, VideoConvertResponse,
    VideoStatus, VideoInfo, VideoDownload, VideoPreview, VideoList,
    VideoStatusEnum, ConversionSettings
)
from app.models.auth import TokenData
from app.services.gcs_service import gcs_service
from app.services.firestore_service import firestore_service
from app.services.cloud_tasks_service import cloud_tasks_service
from app.middleware.auth_middleware import get_current_user, get_current_user_id
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["Videos"])
settings = get_settings()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    upload_data: VideoUpload,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> VideoUploadResponse:
    """
    Generate signed URL for direct video upload to Google Cloud Storage.
    
    Args:
        upload_data: Video upload metadata
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Signed upload URL and video metadata
        
    Raises:
        HTTPException: If upload preparation fails
    """
    try:
        logger.info(f"Video upload request: {upload_data.filename} by {current_user.user_id}")
        
        # Validate file size
        if upload_data.file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum limit of {settings.max_file_size_mb}MB"
            )
        
        # Validate content type
        if upload_data.content_type not in settings.allowed_video_formats:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported video format: {upload_data.content_type}"
            )
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Generate signed upload URL
        upload_result = await gcs_service.generate_signed_upload_url(
            user_id=current_user.user_id,
            video_id=video_id,
            filename=upload_data.filename,
            content_type=upload_data.content_type,
            expiration_minutes=60
        )
        
        # Create video record in Firestore
        video_data = {
            'video_id': video_id,
            'user_id': current_user.user_id,
            'title': upload_data.title,
            'description': upload_data.description,
            'filename': upload_data.filename,
            'content_type': upload_data.content_type,
            'file_size': upload_data.file_size,
            'status': VideoStatusEnum.UPLOADING,
            'original_url': None,
            'converted_url': None,
            'thumbnail_url': None,
            'preview_url': None
        }
        
        await firestore_service.create_video_record(video_data)
        
        logger.info(f"Upload URL generated for video: {video_id}")
        
        return VideoUploadResponse(
            video_id=video_id,
            signed_upload_url=upload_result['signed_upload_url'],
            upload_metadata=upload_result['upload_metadata'],
            expires_at=upload_result['expires_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video upload preparation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare video upload"
        )


@router.post("/convert", response_model=VideoConvertResponse)
async def convert_video(
    convert_data: VideoConvert,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> VideoConvertResponse:
    """
    Queue video for 2D to VR 180° conversion.
    
    Args:
        convert_data: Video conversion request data
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Conversion job information
        
    Raises:
        HTTPException: If conversion queuing fails
    """
    try:
        logger.info(f"Video conversion request: {convert_data.video_id} by {current_user.user_id}")
        
        # Get video information
        video_info = await firestore_service.get_video_by_id(convert_data.video_id)
        
        if not video_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Verify ownership
        if video_info.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Check if video is ready for conversion
        if video_info.status != VideoStatusEnum.UPLOADED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video is not ready for conversion. Current status: {video_info.status}"
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job record in Firestore
        job_data = {
            'job_id': job_id,
            'video_id': convert_data.video_id,
            'user_id': current_user.user_id,
            'status': VideoStatusEnum.QUEUED,
            'progress_percentage': 0.0,
            'stage': 'Queued for processing',
            'eta_minutes': None,
            'error_message': None,
            'conversion_settings': convert_data.conversion_settings.dict()
        }
        
        await firestore_service.create_job_record(job_data)
        
        # Update video status
        await firestore_service.update_video(convert_data.video_id, {
            'status': VideoStatusEnum.QUEUED
        })
        
        # Create Cloud Tasks job
        task_name = await cloud_tasks_service.create_video_conversion_task(
            video_id=convert_data.video_id,
            user_id=current_user.user_id,
            job_id=job_id,
            conversion_settings=convert_data.conversion_settings.dict(),
            priority=convert_data.priority
        )
        
        # Estimate processing time based on video size and settings
        estimated_time = _estimate_processing_time(video_info.file_size, convert_data.conversion_settings)
        
        logger.info(f"Video conversion queued: {job_id}")
        
        return VideoConvertResponse(
            job_id=job_id,
            video_id=convert_data.video_id,
            estimated_time_minutes=estimated_time,
            status=VideoStatusEnum.QUEUED,
            queue_position=1  # TODO: Implement actual queue position
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video conversion queuing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue video conversion"
        )


@router.get("/status/{job_id}", response_model=VideoStatus)
async def get_conversion_status(
    job_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> VideoStatus:
    """
    Get video conversion job status.
    
    Args:
        job_id: Job ID
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Job status information
        
    Raises:
        HTTPException: If job not found or access denied
    """
    try:
        logger.info(f"Status request for job: {job_id}")
        
        # Get job status
        job_status = await firestore_service.get_job_by_id(job_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify ownership
        if job_status.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


@router.get("/{video_id}", response_model=VideoInfo)
async def get_video_info(
    video_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> VideoInfo:
    """
    Get video information and metadata.
    
    Args:
        video_id: Video ID
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Video information
        
    Raises:
        HTTPException: If video not found or access denied
    """
    try:
        logger.info(f"Video info request: {video_id}")
        
        # Get video information
        video_info = await firestore_service.get_video_by_id(video_id)
        
        if not video_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Verify ownership
        if video_info.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        return video_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video information"
        )


@router.get("/download/{video_id}", response_model=VideoDownload)
async def get_download_url(
    video_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    format_type: str = Query("original", description="Download format: original or vr180")
) -> VideoDownload:
    """
    Get signed download URL for video file.
    
    Args:
        video_id: Video ID
        format_type: Download format (original or vr180)
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Signed download URL and metadata
        
    Raises:
        HTTPException: If video not found or access denied
    """
    try:
        logger.info(f"Download request: {video_id} ({format_type})")
        
        # Get video information
        video_info = await firestore_service.get_video_by_id(video_id)
        
        if not video_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Verify ownership
        if video_info.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Determine filename based on format
        if format_type == "vr180":
            if not video_info.converted_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="VR 180° version not available"
                )
            filename = f"converted_vr180_{video_info.filename}"
        else:
            filename = video_info.filename
        
        # Generate signed download URL
        download_result = await gcs_service.generate_signed_download_url(
            user_id=current_user.user_id,
            video_id=video_id,
            filename=filename,
            expiration_minutes=60
        )
        
        return VideoDownload(
            download_url=download_result['download_url'],
            filename=download_result['filename'],
            content_type=download_result['content_type'],
            file_size=download_result['file_size'],
            expires_at=download_result['expires_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


@router.get("/preview/{video_id}", response_model=VideoPreview)
async def get_preview_url(
    video_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> VideoPreview:
    """
    Get VR preview URLs for video.
    
    Args:
        video_id: Video ID
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Preview URLs and VR player configuration
        
    Raises:
        HTTPException: If video not found or access denied
    """
    try:
        logger.info(f"Preview request: {video_id}")
        
        # Get video information
        video_info = await firestore_service.get_video_by_id(video_id)
        
        if not video_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Verify ownership
        if video_info.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Check if VR 180° version is available
        if not video_info.converted_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="VR 180° version not available for preview"
            )
        
        # Generate preview URLs
        preview_url = await gcs_service.generate_public_url(
            user_id=current_user.user_id,
            video_id=video_id,
            filename=f"converted_vr180_{video_info.filename}"
        )
        
        thumbnail_url = await gcs_service.generate_public_url(
            user_id=current_user.user_id,
            video_id=video_id,
            filename="thumbnail.jpg"
        )
        
        # VR player configuration
        vr_player_config = {
            "stereo_mode": "side-by-side",
            "projection": "equirectangular",
            "controls": True,
            "autoplay": False,
            "loop": False,
            "muted": True
        }
        
        # Preview metadata
        metadata = {
            "title": video_info.title or video_info.filename,
            "duration": video_info.duration_seconds,
            "resolution": video_info.resolution,
            "frame_rate": video_info.frame_rate
        }
        
        return VideoPreview(
            preview_url=preview_url,
            thumbnail_url=thumbnail_url,
            metadata=metadata,
            vr_player_config=vr_player_config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate preview URLs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview URLs"
        )


@router.get("/user/{user_id}", response_model=VideoList)
async def get_user_videos(
    user_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Videos per page")
) -> VideoList:
    """
    Get paginated list of user's videos.
    
    Args:
        user_id: User ID
        page: Page number
        page_size: Videos per page
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Paginated list of user's videos
        
    Raises:
        HTTPException: If access denied or retrieval fails
    """
    try:
        logger.info(f"User videos request: {user_id} (page {page})")
        
        # Verify access (users can only access their own videos)
        if user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user's videos"
            )
        
        # Get user's videos
        result = await firestore_service.get_user_videos(
            user_id=user_id,
            page=page,
            page_size=page_size
        )
        
        return VideoList(
            videos=result['videos'],
            total_count=result['total_count'],
            page=result['page'],
            page_size=result['page_size'],
            has_next=result['has_next']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user videos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user videos"
        )


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Delete video and all associated files.
    
    Args:
        video_id: Video ID
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Deletion confirmation message
        
    Raises:
        HTTPException: If video not found or access denied
    """
    try:
        logger.info(f"Video deletion request: {video_id}")
        
        # Get video information
        video_info = await firestore_service.get_video_by_id(video_id)
        
        if not video_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )
        
        # Verify ownership
        if video_info.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this video"
            )
        
        # Delete files from GCS
        await gcs_service.delete_video_files(current_user.user_id, video_id)
        
        # Delete video record from Firestore
        # TODO: Implement video deletion in Firestore service
        
        logger.info(f"Video deleted successfully: {video_id}")
        
        return {"message": "Video deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete video: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete video"
        )


def _estimate_processing_time(file_size: int, settings: ConversionSettings) -> int:
    """
    Estimate video processing time based on file size and settings.
    
    Args:
        file_size: File size in bytes
        settings: Conversion settings
        
    Returns:
        Estimated processing time in minutes
    """
    # Base processing time in minutes per GB
    base_time_per_gb = 5
    
    # Quality multiplier
    quality_multipliers = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
        "ultra": 2.0
    }
    
    # Resolution multiplier
    resolution_multipliers = {
        "720p": 0.5,
        "1080p": 1.0,
        "1440p": 1.5,
        "4K": 2.5
    }
    
    # Calculate estimated time
    file_size_gb = file_size / (1024 ** 3)
    base_time = file_size_gb * base_time_per_gb
    quality_multiplier = quality_multipliers.get(settings.quality, 1.0)
    resolution_multiplier = resolution_multipliers.get(settings.resolution, 1.0)
    
    estimated_time = int(base_time * quality_multiplier * resolution_multiplier)
    
    # Minimum processing time
    return max(estimated_time, 2)
