"""
Face Recognition Handler for Live Streams

Processes frames for face detection and recognition, marks attendance,
and returns recognition results for display.
"""

import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class RecognitionHandler:
    """Handles face recognition on live stream frames"""
    
    def __init__(self, face_service, db):
        """
        Initialize recognition handler
        
        Args:
            face_service: FaceRecognitionService instance
            db: DBManager instance
        """
        self.face_service = face_service
        self.db = db
        self.frame_count = 0
        self.recognition_interval = 3  # Process every Nth frame to save CPU
        self.loaded_student_ids = set()  # Track loaded students for hot-reload
        
    def reload_students(self):
        """
        Reload students from database and add any new ones to face service
        
        This enables dynamic face registration when admin approves enrollments
        without requiring server restart.
        
        Returns:
            int: Number of newly loaded students
        """
        try:
            students = self.db.get_all_students()
            new_count = 0
            
            for student in students:
                student_id = student['id']
                
                # Skip if already loaded
                if student_id in self.loaded_student_ids:
                    continue
                    
                # Add new student to face service
                if student.get('face_encoding'):
                    self.face_service.add_known_face(
                        student_id,
                        student['name'],
                        student['face_encoding']
                    )
                    self.loaded_student_ids.add(student_id)
                    new_count += 1
                    logger.info(f"Loaded new student: {student['name']} (ID: {student_id})")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error reloading students: {e}")
            return 0
        
    def process_frame(self, frame):
        """
        Process a frame for face recognition
        
        Args:
            frame: numpy array (BGR image from camera)
            
        Returns:
            dict with recognition results or None if skipped
            {
                'recognitions': [
                    {
                        'student_id': int,
                        'name': str,
                        'confidence': float,
                        'bbox': [x, y, w, h]
                    },
                    ...
                ],
                'faces_detected': int
            }
        """
        self.frame_count += 1
        
        # Throttle: only process every Nth frame
        if self.frame_count % self.recognition_interval != 0:
            return None
            
        if self.face_service is None or self.face_service.app is None:
            return None
            
        try:
            # Detect faces in frame
            faces = self.face_service.app.get(frame)
            
            if not faces:
                return {'recognitions': [], 'faces_detected': 0}
                
            recognitions = []
            
            for face in faces:
                # Get embedding
                embedding = face.normed_embedding.tolist()
                
                # Match against enrolled students
                match = self.face_service.match_face(embedding)
                
                if match:
                    student_id = match['student_id']
                    name = match['name']
                    confidence = match['similarity']
                    
                    # Get bounding box
                    bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]
                    
                    # Convert bbox to [x, y, w, h] format for easier drawing
                    x1, y1, x2, y2 = bbox
                    bbox_xywh = [x1, y1, x2 - x1, y2 - y1]
                    
                    recognitions.append({
                        'student_id': student_id,
                        'name': name,
                        'confidence': float(confidence),
                        'bbox': bbox_xywh
                    })
                    
                    # Mark attendance (with deduplication)
                    self._mark_attendance(student_id)
                    
            return {
                'recognitions': recognitions,
                'faces_detected': len(faces)
            }
            
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return None
            
    def _mark_attendance(self, student_id):
        """
        Mark attendance for a student with deduplication
        
        Only marks if student hasn't been marked in the last 30 minutes
        
        Args:
            student_id: ID of the recognized student
        """
        try:
            # Check if already marked recently (30 minutes)
            recent = self.db.check_recent_attendance(student_id, minutes=30)
            
            if not recent:
                # Mark new attendance
                self.db.mark_attendance(student_id)
                logger.info(f"Attendance marked for student {student_id}")
            
        except Exception as e:
            logger.error(f"Attendance marking error: {e}")
