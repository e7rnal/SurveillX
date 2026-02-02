"""Video Buffer Service - Manages video frame buffering and clip saving"""
import cv2
import os
import time
from collections import deque
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class VideoBuffer:
    def __init__(self, clips_dir, max_buffer_seconds=15, fps=30):
        self.clips_dir = clips_dir
        self.max_buffer_seconds = max_buffer_seconds
        self.fps = fps
        self.max_frames = max_buffer_seconds * fps
        
        # Buffer for each camera
        self.buffers = {}
        self.locks = {}
        
        os.makedirs(clips_dir, exist_ok=True)
        logger.info(f"Video buffer initialized: {max_buffer_seconds}s @ {fps} FPS")
    
    def add_frame(self, camera_id, frame, timestamp=None):
        """Add frame to buffer"""
        if timestamp is None:
            timestamp = time.time()
        
        if camera_id not in self.buffers:
            self.buffers[camera_id] = deque(maxlen=self.max_frames)
            self.locks[camera_id] = Lock()
        
        with self.locks[camera_id]:
            self.buffers[camera_id].append((frame.copy(), timestamp))
    
    def save_clip(self, camera_id, event_type, duration=10, pre_event_seconds=5):
        """Save video clip from buffer"""
        if camera_id not in self.buffers:
            logger.warning(f"No buffer for camera {camera_id}")
            return None
        
        try:
            with self.locks[camera_id]:
                buffer_frames = list(self.buffers[camera_id])
            
            if not buffer_frames:
                return None
            
            # Generate clip path
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            clip_path = os.path.join(
                self.clips_dir,
                f"cam{camera_id}_{event_type}_{timestamp}.mp4"
            )
            
            # Write video
            if buffer_frames:
                height, width = buffer_frames[0][0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(clip_path, fourcc, self.fps, (width, height))
                
                for frame, _ in buffer_frames:
                    out.write(frame)
                
                out.release()
                logger.info(f"Saved clip: {clip_path}")
                return clip_path
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to save clip: {e}")
            return None
