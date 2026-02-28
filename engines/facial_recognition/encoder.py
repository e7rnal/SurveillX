"""
Face Encoder — generates face embeddings for database storage.
Uses FaceDetector internally to extract faces, then produces
JSON-serializable 512-d embedding vectors.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from engines.facial_recognition.detector import FaceDetector

logger = logging.getLogger(__name__)


@dataclass
class EncodingResult:
    """Result of multi-photo face encoding."""
    embedding: Optional[List[float]]  # 512 floats or None
    valid_count: int = 0
    total_count: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.embedding is not None


class FaceEncoder:
    """
    Generates face embeddings for storage and enrollment.

    Responsibilities:
        - Single-frame encoding (largest face)
        - Multi-photo averaged encoding (enrollment flow)
        - L2-normalization of averaged embeddings

    Uses FaceDetector for the actual face detection.
    """

    def __init__(self, detector: FaceDetector):
        self.detector = detector

    @property
    def available(self) -> bool:
        return self.detector.available

    def encode_single(self, frame: np.ndarray) -> Optional[List[float]]:
        """
        Generate face embedding from a single image.
        Uses the largest face if multiple are found.

        Args:
            frame: BGR image containing a face

        Returns:
            List of 512 floats (JSON-serializable), or None if no face found
        """
        if not self.available:
            logger.warning("FaceEncoder: detector not available")
            return None

        try:
            faces = self.detector.detect(frame)
            if not faces:
                return None

            # Pick largest face by bounding box area
            largest = max(faces, key=lambda f: f.bbox.area)
            return largest.embedding.tolist()

        except Exception as e:
            logger.error(f"Face encoding error: {e}")
            return None

    def encode_multiple(self, frames: List[np.ndarray],
                        min_valid: int = 3) -> EncodingResult:
        """
        Generate robust face embedding by averaging embeddings from multiple images.
        Used during enrollment to create a stronger representation from 5 pose photos.

        Args:
            frames: list of BGR images, each containing one face
            min_valid: minimum number of valid face detections required (default 3)

        Returns:
            EncodingResult with averaged, normalized embedding or None
        """
        if not self.available:
            return EncodingResult(
                embedding=None, total_count=len(frames),
                errors=['FaceEncoder: detector not available']
            )

        embeddings = []
        errors = []

        for i, frame in enumerate(frames):
            try:
                faces = self.detector.detect(frame)
                if not faces:
                    errors.append(f"Photo {i+1}: No face detected")
                    continue

                largest = max(faces, key=lambda f: f.bbox.area)
                embeddings.append(largest.embedding)
            except Exception as e:
                errors.append(f"Photo {i+1}: {str(e)}")

        if len(embeddings) < min_valid:
            errors.append(f"Need at least {min_valid} valid face photos, got {len(embeddings)}")
            return EncodingResult(
                embedding=None,
                valid_count=len(embeddings),
                total_count=len(frames),
                errors=errors,
            )

        # Average all embeddings and L2-normalize
        avg = np.mean(embeddings, axis=0).astype(np.float32)
        avg /= np.linalg.norm(avg)

        logger.info(f"Encoded face from {len(embeddings)}/{len(frames)} photos")
        return EncodingResult(
            embedding=avg.tolist(),
            valid_count=len(embeddings),
            total_count=len(frames),
            errors=errors,
        )
