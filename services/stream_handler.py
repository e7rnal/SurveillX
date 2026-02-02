"""
Video Stream Handler - Server-side WebSocket streaming and ML processing
"""
import base64
import logging
import numpy as np
from flask import current_app
from flask_socketio import Namespace, emit
from datetime import datetime
import cv2
import threading
import queue

logger = logging.getLogger(__name__)

class StreamHandler(Namespace):
    """SocketIO namespace for video streaming and ML processing"""
    
    def __init__(self, namespace='/stream'):
        super().__init__(namespace)
        self.connected_clients = set()
        self.frame_queue = queue.Queue(maxsize=10)
        self.face_service = None
        self.activity_detector = None
        self.last_attendance_check = {}
        self.attendance_cooldown = 60  # seconds between same student attendance marks
        
    def on_connect(self):
        """Client connected"""
        logger.info(f"Stream client connected: {self.namespace}")
        self.connected_clients.add(1)
        emit('status', {'connected': True, 'message': 'Connected to stream server'})
    
    def on_disconnect(self, reason=None):
        """Client disconnected"""
        logger.info(f"Stream client disconnected: {self.namespace} (reason: {reason})")
        self.connected_clients.discard(1)
    
    def on_frame(self, data):
        """
        Receive video frame from client
        data: {
            'frame': base64 encoded JPEG image,
            'camera_id': optional camera identifier,
            'timestamp': optional timestamp
        }
        """
        try:
            frame_data = data.get('frame')
            camera_id = data.get('camera_id', 1)
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            if not frame_data:
                return
            
            # Decode frame
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("Failed to decode frame")
                return
            
            # Process frame for detections
            detections = self.process_frame(frame, camera_id)
            
            # Broadcast frame to ALL connected clients (including /stream namespace)
            emit('frame', {
                'frame': frame_data,
                'timestamp': timestamp,
                'camera_id': camera_id
            }, broadcast=True)
            
            # Broadcast detections
            if detections:
                emit('detection', detections, broadcast=True)
                
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    def process_frame(self, frame, camera_id):
        """
        Process frame through ML pipeline
        Returns detection results
        """
        detections = {
            'faces': [],
            'activity': 'Normal',
            'alerts': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Face Recognition (if service available)
        if self.face_service:
            try:
                faces = self.face_service.detect_and_recognize(frame)
                detections['faces'] = faces
                
                # Mark attendance for recognized faces
                self.process_attendance(faces)
                
            except Exception as e:
                logger.error(f"Face recognition error: {e}")
        
        # Activity Detection (if service available)
        if self.activity_detector:
            try:
                activity = self.activity_detector.detect(frame)
                detections['activity'] = activity.get('type', 'Normal')
                
                # Create alerts for abnormal activity
                if activity.get('is_abnormal'):
                    self.create_alert(activity, camera_id, frame)
                    detections['alerts'].append(activity)
                    
            except Exception as e:
                logger.error(f"Activity detection error: {e}")
        
        return detections
    
    def process_attendance(self, faces):
        """Mark attendance for recognized faces"""
        try:
            db = current_app.db
            now = datetime.now()
            
            for face in faces:
                if not face.get('student_id'):
                    continue
                    
                student_id = face['student_id']
                
                # Check cooldown
                last_check = self.last_attendance_check.get(student_id)
                if last_check and (now - last_check).seconds < self.attendance_cooldown:
                    continue
                
                # Mark attendance
                db.mark_attendance(student_id, now)
                self.last_attendance_check[student_id] = now
                logger.info(f"Marked attendance for student {student_id}")
                
        except Exception as e:
            logger.error(f"Attendance marking error: {e}")
    
    def create_alert(self, activity, camera_id, frame):
        """Create alert for abnormal activity"""
        try:
            db = current_app.db
            
            # Save alert to database
            alert_id = db.create_alert(
                event_type=activity.get('type', 'suspicious_activity'),
                camera_id=camera_id,
                clip_path=None,  # Clip saved separately
                severity=activity.get('severity', 'medium'),
                metadata={
                    'description': activity.get('description', ''),
                    'confidence': activity.get('confidence', 0),
                    'location': activity.get('location', 'Unknown')
                }
            )
            
            logger.info(f"Created alert {alert_id} for {activity.get('type')}")
            
            # Emit alert to dashboard
            emit('new_alert', {
                'id': alert_id,
                'type': activity.get('type'),
                'severity': activity.get('severity', 'medium'),
                'timestamp': datetime.now().isoformat()
            }, broadcast=True, namespace='/')
            
        except Exception as e:
            logger.error(f"Alert creation error: {e}")
    
    def set_face_service(self, service):
        """Set face recognition service"""
        self.face_service = service
        logger.info("Face recognition service attached to stream handler")
    
    def set_activity_detector(self, detector):
        """Set activity detection service"""
        self.activity_detector = detector
        logger.info("Activity detector attached to stream handler")


# Global stream handler instance
stream_handler = StreamHandler('/stream')
