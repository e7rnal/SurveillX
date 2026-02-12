"""
Face Recognition Service — InsightFace (Buffalo_L)
Handles face detection, 512-dim embedding extraction, and matching for attendance.
GPU-accelerated on Tesla T4 via ONNX Runtime CUDA provider.
"""

import logging
import json
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------- InsightFace Setup ----------
INSIGHTFACE_AVAILABLE = False
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
    logger.info("InsightFace library loaded successfully")
except ImportError:
    logger.warning("InsightFace not available — install with: pip install insightface onnxruntime-gpu")


class FaceService:
    """Face recognition service using InsightFace Buffalo_L model."""

    def __init__(self, db_manager=None, threshold=0.4, gpu_id=0):
        """
        Args:
            db_manager: DBManager instance for student lookups
            threshold: Cosine similarity threshold for face matching (0.0-1.0, default 0.4)
            gpu_id: GPU device ID (0 for first GPU)
        """
        self.db = db_manager
        self.threshold = threshold
        self.gpu_id = gpu_id
        self.app = None

        # In-memory cache of known face embeddings
        self.known_embeddings = {}   # student_id -> np.ndarray (512-d)
        self.known_names = {}        # student_id -> name

        if INSIGHTFACE_AVAILABLE:
            self._init_model()
            self.load_known_faces()

    def _init_model(self):
        """Initialize the InsightFace Buffalo_L model with GPU."""
        try:
            self.app = FaceAnalysis(
                name='buffalo_l',
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            # det_size controls the input size for detection (larger = more accurate but slower)
            self.app.prepare(ctx_id=self.gpu_id, det_size=(640, 640))
            logger.info(f"InsightFace Buffalo_L loaded on GPU {self.gpu_id}")
        except Exception as e:
            logger.error(f"Failed to init InsightFace: {e}")
            self.app = None

    def load_known_faces(self):
        """Load face embeddings from database into memory cache."""
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
                        # Stored as JSON list of 512 floats
                        if isinstance(encoding_data, str):
                            embedding_list = json.loads(encoding_data)
                        else:
                            embedding_list = encoding_data

                        embedding = np.array(embedding_list, dtype=np.float32)

                        if embedding.shape[0] == 512:
                            self.known_embeddings[student['id']] = embedding
                            self.known_names[student['id']] = student['name']
                            loaded += 1
                        else:
                            logger.warning(
                                f"Student {student['id']} has invalid embedding size: {embedding.shape}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to load embedding for student {student['id']}: {e}")

            logger.info(f"Loaded {loaded} face embeddings from database")

        except Exception as e:
            logger.error(f"Error loading known faces: {e}")

    def detect_and_recognize(self, frame):
        """
        Detect faces in frame and recognize known students.

        Args:
            frame: BGR image (numpy array from OpenCV)

        Returns:
            List of dicts with keys:
                location: {top, right, bottom, left}
                student_id: int or None
                student_name: str or None
                confidence: float (cosine similarity)
                embedding: list (512 floats) — only if no match (for enrollment UI)
        """
        if not INSIGHTFACE_AVAILABLE or self.app is None:
            return []

        results = []

        try:
            # InsightFace expects BGR (OpenCV default) — no conversion needed
            faces = self.app.get(frame)

            for face in faces:
                bbox = face.bbox.astype(int)  # [x1, y1, x2, y2]
                embedding = face.normed_embedding  # 512-d normalized vector

                face_data = {
                    'location': {
                        'left': int(bbox[0]),
                        'top': int(bbox[1]),
                        'right': int(bbox[2]),
                        'bottom': int(bbox[3]),
                    },
                    'student_id': None,
                    'student_name': None,
                    'confidence': 0.0,
                    'age': int(face.age) if hasattr(face, 'age') else None,
                    'gender': 'M' if (hasattr(face, 'gender') and face.gender == 1) else 'F' if hasattr(face, 'gender') else None,
                }

                # Match against known faces using cosine similarity
                if self.known_embeddings:
                    best_id = None
                    best_sim = -1.0

                    for student_id, known_emb in self.known_embeddings.items():
                        sim = float(np.dot(embedding, known_emb))
                        if sim > best_sim:
                            best_sim = sim
                            best_id = student_id

                    if best_id and best_sim >= self.threshold:
                        face_data['student_id'] = best_id
                        face_data['student_name'] = self.known_names.get(best_id, 'Unknown')
                        face_data['confidence'] = round(best_sim, 3)

                results.append(face_data)

            if results:
                recognized = sum(1 for f in results if f['student_id'])
                logger.debug(f"Detected {len(results)} faces, {recognized} recognized")

        except Exception as e:
            logger.error(f"Face detection error: {e}")

        return results

    def encode_face(self, frame):
        """
        Generate face embedding from image.

        Args:
            frame: BGR image with a face

        Returns:
            List of 512 floats (JSON-serializable), or None if no face found
        """
        if not INSIGHTFACE_AVAILABLE or self.app is None:
            logger.warning("InsightFace not available for encoding")
            return None

        try:
            faces = self.app.get(frame)

            if not faces:
                return None

            # Use the largest face (most prominent)
            largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            embedding = largest.normed_embedding

            # Return as list of floats for JSON storage
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Face encoding error: {e}")
            return None

    def add_known_face(self, student_id, name, embedding):
        """Add a face embedding to the in-memory cache."""
        if isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float32)
        elif isinstance(embedding, str):
            embedding = np.array(json.loads(embedding), dtype=np.float32)

        self.known_embeddings[student_id] = embedding
        self.known_names[student_id] = name
        logger.info(f"Added known face for student {student_id}: {name}")

    def remove_known_face(self, student_id):
        """Remove a face from the in-memory cache."""
        self.known_embeddings.pop(student_id, None)
        self.known_names.pop(student_id, None)
        logger.info(f"Removed known face for student {student_id}")

    def get_stats(self):
        """Return face service statistics."""
        return {
            'available': INSIGHTFACE_AVAILABLE and self.app is not None,
            'model': 'buffalo_l',
            'known_faces': len(self.known_embeddings),
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
