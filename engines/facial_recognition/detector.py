"""
Face Detector — InsightFace Buffalo_L wrapper.
Handles face detection in frames, returning structured DetectedFace objects.
GPU-accelerated via ONNX Runtime CUDA provider with CPU fallback.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Lazy import — InsightFace may not be installed in all environments
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logger.warning("InsightFace not installed — face detection unavailable")


@dataclass
class BoundingBox:
    """Axis-aligned bounding box in pixel coordinates."""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict:
        return {'left': self.left, 'top': self.top, 'right': self.right, 'bottom': self.bottom}


@dataclass
class DetectedFace:
    """A face detected in a frame."""
    bbox: BoundingBox
    embedding: np.ndarray        # 512-d normalized vector
    age: Optional[int] = None
    gender: Optional[str] = None  # 'M' or 'F'
    det_score: float = 0.0       # Detection confidence

    def to_dict(self) -> dict:
        return {
            'location': self.bbox.to_dict(),
            'age': self.age,
            'gender': self.gender,
            'det_score': round(self.det_score, 3),
        }


class FaceDetector:
    """
    Detects faces in images using InsightFace Buffalo_L model.

    Responsibilities:
        - Initialize InsightFace with GPU/CPU fallback
        - Detect faces and extract 512-d embeddings
        - Validate images for enrollment (single face check)

    Does NOT handle matching or encoding for storage — see FaceMatcher and FaceEncoder.
    """

    def __init__(self, model_name: str = 'buffalo_l', gpu_id: int = 0,
                 det_size: tuple = (640, 640)):
        self.model_name = model_name
        self.gpu_id = gpu_id
        self.det_size = det_size
        self.app = None

        if INSIGHTFACE_AVAILABLE:
            self._init_model()

    @property
    def available(self) -> bool:
        return INSIGHTFACE_AVAILABLE and self.app is not None

    def _init_model(self):
        """Initialize InsightFace — tries GPU first, falls back to CPU."""
        provider_options = [
            ['CUDAExecutionProvider', 'CPUExecutionProvider'],
            ['CPUExecutionProvider'],
        ]
        for providers in provider_options:
            try:
                self.app = FaceAnalysis(name=self.model_name, providers=providers)
                self.app.prepare(ctx_id=self.gpu_id, det_size=self.det_size)

                # Log which provider is actually active
                active_providers = []
                for model in self.app.models:
                    if hasattr(model, 'session'):
                        active_providers = model.session.get_providers()
                        break
                logger.info(
                    f"FaceDetector: {self.model_name} loaded with {providers} "
                    f"(active: {active_providers})"
                )
                return
            except Exception as e:
                logger.warning(f"FaceDetector init failed with {providers}: {e}")
                self.app = None
        logger.error("FaceDetector: could not initialize with any provider")

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        """
        Detect all faces in a BGR frame.

        Args:
            frame: BGR image (numpy array, OpenCV format)

        Returns:
            List of DetectedFace with bounding boxes, embeddings, age, gender
        """
        if not self.available:
            return []

        try:
            raw_faces = self.app.get(frame)
            results = []

            for face in raw_faces:
                bbox = face.bbox.astype(int)
                detected = DetectedFace(
                    bbox=BoundingBox(
                        left=int(bbox[0]),
                        top=int(bbox[1]),
                        right=int(bbox[2]),
                        bottom=int(bbox[3]),
                    ),
                    embedding=face.normed_embedding,
                    age=int(face.age) if hasattr(face, 'age') else None,
                    gender='M' if (hasattr(face, 'gender') and face.gender == 1) else 'F' if hasattr(face, 'gender') else None,
                    det_score=float(face.det_score) if hasattr(face, 'det_score') else 0.0,
                )
                results.append(detected)

            return results

        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []

    def validate(self, frame: np.ndarray) -> dict:
        """
        Check if a frame contains exactly one detectable face.
        Used during enrollment to validate photos.

        Returns:
            dict with 'valid' (bool), 'num_faces' (int), 'error' (str or None)
        """
        if not self.available:
            return {'valid': False, 'num_faces': 0, 'error': 'InsightFace not available'}

        try:
            faces = self.app.get(frame)
            if not faces:
                return {'valid': False, 'num_faces': 0, 'error': 'No face detected'}
            if len(faces) > 1:
                return {'valid': False, 'num_faces': len(faces),
                        'error': 'Multiple faces detected — only one person should be in frame'}
            return {'valid': True, 'num_faces': 1, 'error': None}
        except Exception as e:
            return {'valid': False, 'num_faces': 0, 'error': str(e)}

    def get_stats(self) -> dict:
        return {
            'available': self.available,
            'model': self.model_name,
            'gpu_id': self.gpu_id,
            'det_size': self.det_size,
        }
