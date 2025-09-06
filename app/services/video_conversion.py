"""
Video processing service for 2D to VR 180° conversion using MiDaS and FFmpeg.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import tempfile
import shutil

try:
    import cv2
    import numpy as np
    import torch
    import ffmpeg
    from PIL import Image
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    # Create dummy classes for when dependencies are not available
    class cv2:
        VideoCapture = None
        CAP_PROP_FRAME_COUNT = None
        CAP_PROP_FPS = None
        imread = None
        imwrite = None
        cvtColor = None
        COLOR_BGR2RGB = None
        COLOR_RGB2BGR = None
    class np:
        array = None
        ndarray = None
    class torch:
        hub = None
        cuda = None
        nn = None
    class ffmpeg:
        input = None
        run = None
        probe = None
    class Image:
        pass

from app.config import get_settings
from app.models.video import VideoStatusEnum, ConversionSettings

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """Video processing service for VR 180° conversion."""
    
    def __init__(self):
        """Initialize video processing service."""
        self.settings = get_settings()
        self._midas_model = None
        self._device = None
        
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Video processing dependencies not available. Service will be limited.")
    
    @property
    def device(self) -> str:
        """Get processing device (CPU or GPU)."""
        if self._device is None:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self._device}")
        return self._device
    
    @property
    def midas_model(self):
        """Get MiDaS depth estimation model."""
        if self._midas_model is None:
            try:
                # Load MiDaS model
                model_type = "MiDaS_small"  # Use small model for faster processing
                self._midas_model = torch.hub.load("intel-isl/MiDaS", model_type)
                self._midas_model.to(self.device)
                self._midas_model.eval()
                
                # Load transforms
                midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
                self._midas_transforms = midas_transforms.small_transform
                
                logger.info("MiDaS model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load MiDaS model: {e}")
                raise
        return self._midas_model
    
    async def process_video(
        self,
        input_path: str,
        output_path: str,
        conversion_settings: ConversionSettings,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Process video from 2D to VR 180° format.
        
        Args:
            input_path: Path to input video file
            output_path: Path to output VR 180° video file
            conversion_settings: Conversion settings
            progress_callback: Callback function for progress updates
            
        Returns:
            Dictionary containing processing results
        """
        if not DEPENDENCIES_AVAILABLE:
            return {
                'success': False,
                'error': 'Video processing dependencies not available'
            }
        
        try:
            logger.info(f"Starting video processing: {input_path}")
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract frames
                frames_dir = os.path.join(temp_dir, "frames")
                os.makedirs(frames_dir, exist_ok=True)
                
                await self._extract_frames(input_path, frames_dir, progress_callback)
                
                # Process frames for depth estimation and stereo generation
                processed_frames_dir = os.path.join(temp_dir, "processed_frames")
                os.makedirs(processed_frames_dir, exist_ok=True)
                
                await self._process_frames_for_vr180(
                    frames_dir, 
                    processed_frames_dir, 
                    conversion_settings,
                    progress_callback
                )
                
                # Generate VR 180° video
                await self._generate_vr180_video(
                    processed_frames_dir, 
                    output_path, 
                    conversion_settings,
                    progress_callback
                )
                
                # Generate thumbnail
                thumbnail_path = await self._generate_thumbnail(input_path, temp_dir)
                
                # Get video metadata
                metadata = await self._get_video_metadata(input_path)
                
                logger.info(f"Video processing completed: {output_path}")
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'thumbnail_path': thumbnail_path,
                    'metadata': metadata
                }
                
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_frames(
        self, 
        video_path: str, 
        frames_dir: str, 
        progress_callback=None
    ) -> None:
        """Extract frames from video."""
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Extracting {frame_count} frames at {fps} FPS")
            
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Save frame
                frame_path = os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg")
                cv2.imwrite(frame_path, frame)
                
                frame_idx += 1
                
                # Update progress
                if progress_callback:
                    progress = (frame_idx / frame_count) * 20  # 20% of total progress
                    await progress_callback(progress, "Extracting frames")
            
            cap.release()
            logger.info(f"Extracted {frame_idx} frames")
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            raise
    
    async def _process_frames_for_vr180(
        self,
        frames_dir: str,
        output_dir: str,
        conversion_settings: ConversionSettings,
        progress_callback=None
    ) -> None:
        """Process frames for VR 180° conversion."""
        try:
            frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
            total_frames = len(frame_files)
            
            logger.info(f"Processing {total_frames} frames for VR 180°")
            
            for idx, frame_file in enumerate(frame_files):
                frame_path = os.path.join(frames_dir, frame_file)
                output_path = os.path.join(output_dir, frame_file)
                
                # Load frame
                frame = cv2.imread(frame_path)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Estimate depth
                depth_map = await self._estimate_depth(frame_rgb)
                
                # Generate stereo pair
                stereo_frame = await self._generate_stereo_pair(frame_rgb, depth_map, conversion_settings)
                
                # Save processed frame
                stereo_bgr = cv2.cvtColor(stereo_frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(output_path, stereo_bgr)
                
                # Update progress
                if progress_callback:
                    progress = 20 + (idx / total_frames) * 60  # 60% of total progress
                    await progress_callback(progress, "Processing frames for VR 180°")
            
            logger.info("Frame processing completed")
            
        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            raise
    
    async def _estimate_depth(self, frame: np.ndarray) -> np.ndarray:
        """Estimate depth map using MiDaS."""
        try:
            # Preprocess frame for MiDaS
            input_tensor = self._midas_transforms(frame).to(self.device)
            
            # Estimate depth
            with torch.no_grad():
                depth = self.midas_model(input_tensor)
                depth = torch.nn.functional.interpolate(
                    depth.unsqueeze(1),
                    size=frame.shape[:2],
                    mode="bicubic",
                    align_corners=False
                ).squeeze()
            
            # Convert to numpy
            depth_map = depth.cpu().numpy()
            
            # Normalize depth map
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min())
            
            return depth_map
            
        except Exception as e:
            logger.error(f"Depth estimation failed: {e}")
            raise
    
    async def _generate_stereo_pair(
        self, 
        frame: np.ndarray, 
        depth_map: np.ndarray, 
        settings: ConversionSettings
    ) -> np.ndarray:
        """Generate stereo pair for VR 180°."""
        try:
            height, width = frame.shape[:2]
            
            # Create left and right views
            left_view = frame.copy()
            right_view = frame.copy()
            
            # Apply horizontal shift based on depth
            max_shift = int(width * 0.05)  # Maximum 5% shift
            
            for y in range(height):
                for x in range(width):
                    depth_value = depth_map[y, x]
                    shift = int(depth_value * max_shift)
                    
                    # Left view: shift pixels to the right
                    if x + shift < width:
                        right_view[y, x + shift] = frame[y, x]
                    
                    # Right view: shift pixels to the left
                    if x - shift >= 0:
                        left_view[y, x - shift] = frame[y, x]
            
            # Combine into side-by-side stereo
            if settings.stereo_mode == "side-by-side":
                stereo_frame = np.hstack([left_view, right_view])
            else:  # top-bottom
                stereo_frame = np.vstack([left_view, right_view])
            
            return stereo_frame
            
        except Exception as e:
            logger.error(f"Stereo pair generation failed: {e}")
            raise
    
    async def _generate_vr180_video(
        self,
        frames_dir: str,
        output_path: str,
        conversion_settings: ConversionSettings,
        progress_callback=None
    ) -> None:
        """Generate VR 180° video from processed frames."""
        try:
            frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
            
            if not frame_files:
                raise ValueError("No processed frames found")
            
            # Get frame dimensions
            first_frame = cv2.imread(os.path.join(frames_dir, frame_files[0]))
            height, width = first_frame.shape[:2]
            
            # Set up FFmpeg
            input_pattern = os.path.join(frames_dir, "frame_%06d.jpg")
            
            # Configure output settings based on conversion settings
            output_width, output_height = self._get_output_resolution(conversion_settings.resolution)
            bitrate = self._get_bitrate(conversion_settings.quality, output_width, output_height)
            
            # Build FFmpeg command
            stream = ffmpeg.input(input_pattern, framerate=conversion_settings.frame_rate)
            
            # Apply video filters
            stream = ffmpeg.filter(stream, 'scale', output_width, output_height)
            
            # Set output parameters
            stream = ffmpeg.output(
                stream,
                output_path,
                vcodec='libx264',
                video_bitrate=bitrate,
                preset='medium',
                crf=23,
                pix_fmt='yuv420p'
            )
            
            # Run FFmpeg
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            if progress_callback:
                await progress_callback(100, "Video generation completed")
            
            logger.info(f"VR 180° video generated: {output_path}")
            
        except Exception as e:
            logger.error(f"VR 180° video generation failed: {e}")
            raise
    
    async def _generate_thumbnail(self, video_path: str, temp_dir: str) -> str:
        """Generate video thumbnail."""
        try:
            thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
            
            # Extract frame at 10% of video duration
            stream = ffmpeg.input(video_path, ss='10%')
            stream = ffmpeg.output(stream, thumbnail_path, vframes=1, format='image2')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise
    
    async def _get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata."""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'bitrate': int(probe['format'].get('bit_rate', 0)),
                'codec': video_stream['codec_name']
            }
            
        except Exception as e:
            logger.error(f"Failed to get video metadata: {e}")
            return {}
    
    def _get_output_resolution(self, resolution: str) -> Tuple[int, int]:
        """Get output resolution dimensions."""
        resolutions = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "1440p": (2560, 1440),
            "4K": (3840, 2160)
        }
        return resolutions.get(resolution, (1920, 1080))
    
    def _get_bitrate(self, quality: str, width: int, height: int) -> str:
        """Get bitrate based on quality and resolution."""
        base_bitrates = {
            "low": 1000,
            "medium": 2500,
            "high": 5000,
            "ultra": 10000
        }
        
        base_bitrate = base_bitrates.get(quality, 2500)
        resolution_factor = (width * height) / (1920 * 1080)  # Normalize to 1080p
        
        return f"{int(base_bitrate * resolution_factor)}k"


# Global video processing service instance
video_processing_service = VideoProcessingService()
