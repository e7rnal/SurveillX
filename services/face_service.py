"""
Face Recognition Service — thin wrapper over engines/facial_recognition.
Maintains backward compatibility for api/enrollment.py, api/students.py, and ml_worker.py.
"""

import logging
import json
import numpy as np

from engines.facial_recognition import FaceDetector, FaceEncoder, FaceMatcher

logger = logging.getLogger(__name__)


class FaceService:
    """Face recognition service — delegates to engine modules."""

    def __init__(self, db_manager=None, threshold=0.4, gpu_id=0):
        self.db = db_manager
        self.threshold = threshold
        self.gpu_id = gpu_id

        # Engine components
        self._detector = FaceDetector(model_name='buffalo_l', gpu_id=gpu_id)
        self._encoder = FaceEncoder(self._detector)
        self._matcher = FaceMatcher(threshold=threshold)

        # For backward compat — expose known state directly
        self.known_embeddings = self._matcher._embeddings
        self.known_names = self._matcher._names

        # Proxy for checking model availability
        self.app = self._detector.app

        if self._detector.available and self.db:
            self.load_known_faces()

    def _init_model(self):
        """No-op — model initialized in FaceDetector."""
        pass

    def load_known_faces(self):
        """Load face embeddings from database into matcher cache."""
        if not self.db:
            logger.warning("No database manager — cannot load known faces")
            return
        try:
            students = self.db.get_all_students()
            loaded = 0
            for student in students:
                encoding_data = student.get('face_encoding')
                if encoding_data:
                    try:
                        if isinstance(encoding_data, str):
                            embedding_list = json.loads(encoding_data)
                        else:
                            embedding_list = encoding_data
                        embedding = np.array(embedding_list, dtype=np.float32)
                        if embedding.shape[0] == 512:
                            self._matcher.add_face(student['id'], student['name'], embedding)
                            loaded += 1
                        else:
                            logger.warning(f"Student {student['id']} has invalid embedding size: {embedding.shape}")
                    except Exception as e:
                        logger.warning(f"Failed to load embedding for student {student['id']}: {e}")
            logger.info(f"Loaded {loaded} face embeddings from database")
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")

    def detect_and_recognize(self, frame):
        """Detect faces and match against known students."""
        faces = self._detector.detect(frame)
        results = []
        for face in faces:
            face_data = face.to_dict()
            face_data['student_id'] = None
            face_data['student_name'] = None
            face_data['confidence'] = 0.0

            match = self._matcher.match(face.embedding)
            if match.matched:
                face_data['student_id'] = match.student_id
                face_data['student_name'] = match.student_name
                face_data['confidence'] = match.confidence

            results.append(face_data)

        if results:
            recognized = sum(1 for f in results if f['student_id'])
            logger.debug(f"Detected {len(results)} faces, {recognized} recognized")
        return results

    def encode_face(self, frame):
        """Generate face embedding from image."""
        return self._encoder.encode_single(frame)

    def validate_face(self, frame):
        """Check if an image contains a detectable face."""
        return self._detector.validate(frame)

    def encode_multiple(self, frames):
        """Generate robust embedding by averaging multiple photos."""
        result = self._encoder.encode_multiple(frames)
        return {
            'embedding': result.embedding,
            'valid_count': result.valid_count,
            'errors': result.errors,
        }

    def add_known_face(self, student_id, name, embedding):
        """Add a face embedding to the in-memory cache."""
        self._matcher.add_face(student_id, name, embedding)
        logger.info(f"Added known face for student {student_id}: {name}")

    def remove_known_face(self, student_id):
        """Remove a face from the in-memory cache."""
        self._matcher.remove_face(student_id)
        logger.info(f"Removed known face for student {student_id}")

    def get_stats(self):
        """Return face service statistics."""
        return {
            'available': self._detector.available,
            'model': 'buffalo_l',
            'known_faces': self._matcher.known_count,
            'threshold': self.threshold,
            'gpu_id': self.gpu_id,
        }


# ---------- Global Instance ----------
face_service = None


def init_face_service(db_manager, threshold=0.4, gpu_id=0):
    """Initialize global face service."""
    global face_service
    face_service = FaceService(db_manager, threshold, gpu_id)
    return face_service
