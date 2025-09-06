"""
Google Cloud Storage integration for video file management.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlparse

from google.cloud import storage
from google.cloud.exceptions import NotFound
from google.auth.exceptions import DefaultCredentialsError

from app.config import get_settings

logger = logging.getLogger(__name__)


class GCSService:
    """Google Cloud Storage service for file operations."""
    
    def __init__(self):
        """Initialize GCS service."""
        self.settings = get_settings()
        self._client = None
        self._bucket = None
    
    @property
    def client(self) -> storage.Client:
        """Get GCS client."""
        if self._client is None:
            try:
                self._client = storage.Client(project=self.settings.google_cloud_project_id)
            except DefaultCredentialsError:
                logger.warning("GCS credentials not found. Service will be limited.")
                # Create a dummy client for testing
                self._client = None
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Get GCS bucket."""
        if self._bucket is None:
            if self.client is None:
                logger.warning("GCS client not available. Service will be limited.")
                return None
            try:
                self._bucket = self.client.bucket(self.settings.google_cloud_storage_bucket)
            except NotFound:
                logger.error(f"Bucket not found: {self.settings.google_cloud_storage_bucket}")
                raise
        return self._bucket
    
    def _get_file_path(self, user_id: str, video_id: str, filename: str) -> str:
        """
        Generate standardized file path.
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Original filename
            
        Returns:
            Standardized file path
        """
        return f"users/{user_id}/videos/{video_id}/{filename}"
    
    def _get_thumbnail_path(self, user_id: str, video_id: str) -> str:
        """
        Generate thumbnail file path.
        
        Args:
            user_id: User ID
            video_id: Video ID
            
        Returns:
            Thumbnail file path
        """
        return f"users/{user_id}/videos/{video_id}/thumbnail.jpg"
    
    def _get_converted_path(self, user_id: str, video_id: str, format_type: str = "vr180") -> str:
        """
        Generate converted video file path.
        
        Args:
            user_id: User ID
            video_id: Video ID
            format_type: Format type (vr180, preview, etc.)
            
        Returns:
            Converted file path
        """
        return f"users/{user_id}/videos/{video_id}/converted_{format_type}.mp4"
    
    async def generate_signed_upload_url(
        self,
        user_id: str,
        video_id: str,
        filename: str,
        content_type: str,
        expiration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Generate signed URL for direct file upload.
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Original filename
            content_type: MIME type
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Dictionary containing signed URL and metadata
        """
        try:
            # Generate file path
            file_path = self._get_file_path(user_id, video_id, filename)
            
            # Create blob
            blob = self.bucket.blob(file_path)
            
            # Set content type
            blob.content_type = content_type
            
            # Generate signed URL for upload
            expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="PUT",
                content_type=content_type
            )
            
            # Prepare metadata
            upload_metadata = {
                'file_path': file_path,
                'content_type': content_type,
                'expires_at': expiration.isoformat(),
                'bucket_name': self.settings.google_cloud_storage_bucket
            }
            
            logger.info(f"Generated upload URL for: {file_path}")
            
            return {
                'signed_upload_url': signed_url,
                'upload_metadata': upload_metadata,
                'expires_at': expiration
            }
            
        except Exception as e:
            logger.error(f"Failed to generate upload URL: {e}")
            raise
    
    async def generate_signed_download_url(
        self,
        user_id: str,
        video_id: str,
        filename: str,
        expiration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Generate signed URL for file download.
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Filename to download
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            Dictionary containing signed URL and metadata
        """
        try:
            # Generate file path
            file_path = self._get_file_path(user_id, video_id, filename)
            
            # Get blob
            blob = self.bucket.blob(file_path)
            
            # Check if file exists
            if not blob.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Generate signed URL for download
            expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
            
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=expiration,
                method="GET"
            )
            
            # Get file metadata
            blob.reload()
            
            download_metadata = {
                'file_path': file_path,
                'content_type': blob.content_type,
                'file_size': blob.size,
                'expires_at': expiration.isoformat(),
                'bucket_name': self.settings.google_cloud_storage_bucket
            }
            
            logger.info(f"Generated download URL for: {file_path}")
            
            return {
                'download_url': signed_url,
                'filename': filename,
                'content_type': blob.content_type,
                'file_size': blob.size,
                'expires_at': expiration
            }
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {e}")
            raise
    
    async def get_file_metadata(
        self,
        user_id: str,
        video_id: str,
        filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from GCS.
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Filename
            
        Returns:
            File metadata dictionary or None if not found
        """
        try:
            file_path = self._get_file_path(user_id, video_id, filename)
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                return None
            
            blob.reload()
            
            return {
                'file_path': file_path,
                'content_type': blob.content_type,
                'file_size': blob.size,
                'created': blob.time_created,
                'updated': blob.updated,
                'md5_hash': blob.md5_hash,
                'etag': blob.etag
            }
            
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise
    
    async def delete_file(
        self,
        user_id: str,
        video_id: str,
        filename: str
    ) -> bool:
        """
        Delete file from GCS.
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Filename to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            file_path = self._get_file_path(user_id, video_id, filename)
            blob = self.bucket.blob(file_path)
            
            if blob.exists():
                blob.delete()
                logger.info(f"File deleted: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def delete_video_files(self, user_id: str, video_id: str) -> Dict[str, bool]:
        """
        Delete all files associated with a video.
        
        Args:
            user_id: User ID
            video_id: Video ID
            
        Returns:
            Dictionary with deletion results for each file type
        """
        try:
            results = {}
            
            # List all files in the video directory
            prefix = f"users/{user_id}/videos/{video_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                try:
                    blob.delete()
                    results[blob.name] = True
                    logger.info(f"Deleted file: {blob.name}")
                except Exception as e:
                    results[blob.name] = False
                    logger.error(f"Failed to delete file {blob.name}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to delete video files: {e}")
            raise
    
    async def copy_file(
        self,
        source_user_id: str,
        source_video_id: str,
        source_filename: str,
        dest_user_id: str,
        dest_video_id: str,
        dest_filename: str
    ) -> bool:
        """
        Copy file within GCS.
        
        Args:
            source_user_id: Source user ID
            source_video_id: Source video ID
            source_filename: Source filename
            dest_user_id: Destination user ID
            dest_video_id: Destination video ID
            dest_filename: Destination filename
            
        Returns:
            True if copy successful, False otherwise
        """
        try:
            source_path = self._get_file_path(source_user_id, source_video_id, source_filename)
            dest_path = self._get_file_path(dest_user_id, dest_video_id, dest_filename)
            
            source_blob = self.bucket.blob(source_path)
            dest_blob = self.bucket.copy_blob(source_blob, self.bucket, dest_path)
            
            logger.info(f"File copied: {source_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return False
    
    async def get_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage usage for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing storage usage statistics
        """
        try:
            prefix = f"users/{user_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            total_size = 0
            file_count = 0
            video_count = 0
            
            for blob in blobs:
                total_size += blob.size
                file_count += 1
                
                # Count videos (directories with video files)
                if blob.name.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                    video_count += 1
            
            return {
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count,
                'video_count': video_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            raise
    
    async def generate_public_url(
        self,
        user_id: str,
        video_id: str,
        filename: str
    ) -> str:
        """
        Generate public URL for a file (if bucket allows public access).
        
        Args:
            user_id: User ID
            video_id: Video ID
            filename: Filename
            
        Returns:
            Public URL
        """
        try:
            file_path = self._get_file_path(user_id, video_id, filename)
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            return f"https://storage.googleapis.com/{self.settings.google_cloud_storage_bucket}/{file_path}"
            
        except Exception as e:
            logger.error(f"Failed to generate public URL: {e}")
            raise


# Global GCS service instance
gcs_service = GCSService()
