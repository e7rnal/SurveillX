"""
Face Recognition Service
Handles face detection, encoding, and matching for attendance
"""

import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import face_recognition (requires dlib)
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    logger.info("face_recognition library loaded successfully")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition library not available - using mock detection")


class FaceService:
    """Face recognition service for student identification"""
    
    def __init__(self, db_manager=None, threshold=0.6):
        self.db = db_manager
        self.threshold = threshold
        self.known_encodings = {}  # student_id -> encoding
        self.known_names = {}  # student_id -> name
        
        if FACE_RECOGNITION_AVAILABLE:
            self.load_known_faces()
    
    def load_known_faces(self):
        """Load face encodings from database"""
        if not self.db:
            logger.warning("No database manager - cannot load known faces")
            return
        
        try:
            students = self.db.get_all_students()
            loaded = 0
            
            for student in students:
                if student.get('face_encoding'):
                    try:
                        # Decode stored encoding
                        encoding = np.frombuffer(
                            bytes.fromhex(student['face_encoding']),
                            dtype=np.float64
                        )
                        self.known_encodings[student['id']] = encoding
                        self.known_names[student['id']] = student['name']
                        loaded += 1
                    except Exception as e:
                        logger.warning(f"Failed to load encoding for student {student['id']}: {e}")
            
            logger.info(f"Loaded {loaded} face encodings from database")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def detect_and_recognize(self, frame):
        """
        Detect faces in frame and recognize known students
        
        Args:
            frame: BGR image (numpy array from OpenCV)
        
        Returns:
            List of detected faces with student info if matched
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return self._mock_detection(frame)
        
        results = []
        
        try:
            # Convert BGR to RGB
            rgb_frame = frame[:, :, ::-1]
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame, model='hog')
            
            if not face_locations:
                return results
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
                face_data = {
                    'location': {
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left
                    },
                    'student_id': None,
                    'student_name': None,
                    'confidence': 0.0
                }
                
                # Try to match with known faces
                if self.known_encodings:
                    best_match_id = None
                    best_distance = 1.0
                    
                    for student_id, known_encoding in self.known_encodings.items():
                        distance = face_recognition.face_distance([known_encoding], encoding)[0]
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_match_id = student_id
                    
                    # Check if match is good enough
                    if best_match_id and best_distance < (1 - self.threshold):
                        face_data['student_id'] = best_match_id
                        face_data['student_name'] = self.known_names.get(best_match_id, 'Unknown')
                        face_data['confidence'] = round(1 - best_distance, 3)
                
                results.append(face_data)
            
            logger.debug(f"Detected {len(results)} faces, {sum(1 for f in results if f['student_id'])} recognized")
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
        
        return results
    
    def _mock_detection(self, frame):
        """Mock detection when face_recognition not available"""
        # Return empty for now - no faces detected without library
        return []
    
    def encode_face(self, frame):
        """
        Generate face encoding from image
        
        Args:
            frame: BGR image with a single face
        
        Returns:
            Face encoding as hex string, or None if no face found
        """
        if not FACE_RECOGNITION_AVAILABLE:
            logger.warning("face_recognition not available for encoding")
            return None
        
        try:
            rgb_frame = frame[:, :, ::-1]
            
            face_locations = face_recognition.face_locations(rgb_frame)
            if not face_locations:
                return None
            
            encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if not encodings:
                return None
            
            # Return first face encoding as hex string
            return encodings[0].tobytes().hex()
            
        except Exception as e:
            logger.error(f"Face encoding error: {e}")
            return None
    
    def add_known_face(self, student_id, name, encoding):
        """Add a face encoding to the known faces cache"""
        if isinstance(encoding, str):
            # Convert from hex string
            encoding = np.frombuffer(bytes.fromhex(encoding), dtype=np.float64)
        
        self.known_encodings[student_id] = encoding
        self.known_names[student_id] = name
        logger.info(f"Added known face for student {student_id}: {name}")
    
    def remove_known_face(self, student_id):
        """Remove a face from known faces cache"""
        self.known_encodings.pop(student_id, None)
        self.known_names.pop(student_id, None)
        logger.info(f"Removed known face for student {student_id}")


# Global face service instance (will be initialized with db_manager)
face_service = None

def init_face_service(db_manager, threshold=0.6):
    """Initialize face service with database manager"""
    global face_service
    face_service = FaceService(db_manager, threshold)
    return face_service
