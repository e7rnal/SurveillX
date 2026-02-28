"""
Face Recognition Handler for Live Streams

Processes frames for face detection and recognition, marks attendance,
and returns recognition results for display.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class RecognitionHandler:
    """Handles face recognition on live stream frames using FaceService."""
    
    def __init__(self, face_service, db):
        """
        Args:
            face_service: FaceService instance (services/face_service.py)
            db: DBManager instance
        """
        self.face_service = face_service
        self.db = db
        self.frame_count = 0
        self.recognition_interval = 3  # Process every Nth frame
        self.loaded_student_ids = set()
        # Per-person beep/attendance dedup: student_id → last seen timestamp
        self._last_seen = {}
        
    def reload_students(self):
        """
        Reload students from database and add any new ones to face service.
        Returns number of newly loaded students.
        """
        try:
            students = self.db.get_all_students()
            new_count = 0
            
            for student in students:
                student_id = student['id']
                if student_id in self.loaded_student_ids:
                    continue
                if student.get('face_encoding'):
                    import json
                    import numpy as np
                    encoding_data = student['face_encoding']
                    if isinstance(encoding_data, str):
                        embedding_list = json.loads(encoding_data)
                    else:
                        embedding_list = encoding_data
                    embedding = np.array(embedding_list, dtype=np.float32)
                    self.face_service.add_known_face(student_id, student['name'], embedding)
                    self.loaded_student_ids.add(student_id)
                    new_count += 1
                    logger.info(f"Loaded new student: {student['name']} (ID: {student_id})")
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error reloading students: {e}")
            return 0
        
    def process_frame(self, frame):
        """
        Process a frame for face recognition.
        
        Returns dict with recognition results or None if skipped:
        {
            'recognitions': [
                {
                    'student_id': int | None,
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
            
        if self.face_service is None:
            return None
            
        try:
            # Use FaceService.detect_and_recognize which returns face dicts
            results = self.face_service.detect_and_recognize(frame)
            
            if not results:
                return {'recognitions': [], 'faces_detected': 0}
                
            recognitions = []
            
            for face_data in results:
                student_id = face_data.get('student_id')
                name = face_data.get('student_name') or 'Unknown'
                confidence = float(face_data.get('confidence', 0.0))
                
                # Get bounding box — detect_and_recognize returns bbox as [x1,y1,x2,y2]
                bbox = face_data.get('bbox', [0, 0, 0, 0])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    bbox_xywh = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
                else:
                    bbox_xywh = bbox
                    
                recognitions.append({
                    'student_id': student_id,
                    'name': name,
                    'confidence': confidence,
                    'bbox': bbox_xywh,
                })
                
                # Mark attendance for recognized students
                if student_id:
                    self._mark_attendance(student_id)
                    
            return {
                'recognitions': recognitions,
                'faces_detected': len(results),
            }
            
        except Exception as e:
            logger.error(f"Recognition error: {e}", exc_info=True)
            return None
            
    def _mark_attendance(self, student_id):
        """
        Mark attendance for a student, deduplicating within 24 hours.
        """
        try:
            recent = self.db.check_recent_attendance(student_id, minutes=1440)
            if not recent:
                self.db.mark_attendance(student_id)
                logger.info(f"✅ Attendance marked for student {student_id}")
        except Exception as e:
            logger.error(f"Attendance marking error: {e}")
