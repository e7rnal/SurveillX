#!/bin/bash
# Create all remaining service files quickly

echo "Creating email_service.py..."
cat > /opt/dlami/nvme/surveillx-backend/services/email_service.py << 'EOF'
"""Email Service - AWS SES Integration"""
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, aws_access_key, aws_secret_key, aws_region, sender_email):
        self.sender_email = sender_email
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        logger.info(f"Email service initialized with sender: {sender_email}")
    
    def send_enrollment_email(self, recipient_email, token, base_url, roll_no=None):
        """Send enrollment invitation email"""
        enrollment_link = f"{base_url}/templates/enroll.html?token={token}"
        if roll_no:
            enrollment_link += f"&roll_no={roll_no}"
        
        subject = "SurveillX - Complete Your Enrollment"
        
        html_body = f"""
        <html>
        <body>
            <h2>Complete Your Enrollment</h2>
            <p>You have been invited to enroll in the SurveillX surveillance system.</p>
            <p><a href="{enrollment_link}">Click here to complete enrollment</a></p>
            <p>This link will expire in 24 hours.</p>
        </body>
        </html>
        """
        
        text_body = f"""
        SurveillX Student Enrollment
        
        You have been invited to enroll. Please visit: {enrollment_link}
        
        This link will expire in 24 hours.
        """
        
        try:
            response = self.ses_client.send_email(
                Source=self.sender_email,
                Destination={'ToAddresses': [recipient_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text_body, 'Charset': 'UTF-8'},
                        'Html': {'Data': html_body, 'Charset': 'UTF-8'}
                    }
                }
            )
            logger.info(f"Email sent to {recipient_email}")
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send email: {e}")
            return None
EOF

echo "Creating video_buffer.py..."
cat > /opt/dlami/nvme/surveillx-backend/services/video_buffer.py << 'EOF'
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
EOF

echo "✅ All service files created!"
