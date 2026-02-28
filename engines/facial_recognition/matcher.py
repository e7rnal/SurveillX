"""
Face Matcher — in-memory face cache + cosine similarity matching.
Manages known face embeddings and finds the best match for a query embedding.
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of face matching against known faces."""
    student_id: Optional[int] = None
    student_name: Optional[str] = None
    confidence: float = 0.0

    @property
    def matched(self) -> bool:
        return self.student_id is not None

    def to_dict(self) -> dict:
        return {
            'student_id': self.student_id,
            'student_name': self.student_name,
            'confidence': round(self.confidence, 3),
        }


class FaceMatcher:
    """
    Matches face embeddings against a cache of known faces using cosine similarity.

    Responsibilities:
        - Maintain in-memory cache of known face embeddings
        - Add/remove faces dynamically
        - Find best match for a query embedding above threshold

    Thread-safe for concurrent reads; writes (add/remove) replace dict references.
    """

    def __init__(self, threshold: float = 0.4):
        self.threshold = threshold
        self._embeddings: Dict[int, np.ndarray] = {}  # student_id → 512-d vector
        self._names: Dict[int, str] = {}               # student_id → name

    @property
    def known_count(self) -> int:
        return len(self._embeddings)

    def add_face(self, student_id: int, name: str, embedding) -> None:
        """
        Add a face embedding to the known faces cache.

        Args:
            student_id: unique identifier
            name: display name
            embedding: 512-d vector as list, JSON string, or numpy array
        """
        if isinstance(embedding, str):
            embedding = np.array(json.loads(embedding), dtype=np.float32)
        elif isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float32)
        elif not isinstance(embedding, np.ndarray):
            raise ValueError(f"Unsupported embedding type: {type(embedding)}")

        if embedding.shape != (512,):
            raise ValueError(f"Expected 512-d embedding, got shape {embedding.shape}")

        self._embeddings[student_id] = embedding.astype(np.float32)
        self._names[student_id] = name
        logger.debug(f"FaceMatcher: added face for {name} (ID: {student_id})")

    def remove_face(self, student_id: int) -> None:
        """Remove a face from the cache."""
        self._embeddings.pop(student_id, None)
        self._names.pop(student_id, None)
        logger.debug(f"FaceMatcher: removed face for student {student_id}")

    def clear(self) -> None:
        """Remove all known faces."""
        self._embeddings.clear()
        self._names.clear()

    def match(self, embedding: np.ndarray) -> MatchResult:
        """
        Find the best matching known face for a query embedding.

        Args:
            embedding: 512-d normalized face embedding

        Returns:
            MatchResult with student_id, name, and confidence if a match is found
            above the threshold, otherwise an empty MatchResult.
        """
        if not self._embeddings:
            return MatchResult()

        best_id = None
        best_sim = -1.0

        for student_id, known_emb in self._embeddings.items():
            sim = float(np.dot(embedding, known_emb))
            if sim > best_sim:
                best_sim = sim
                best_id = student_id

        if best_id is not None and best_sim >= self.threshold:
            return MatchResult(
                student_id=best_id,
                student_name=self._names.get(best_id, 'Unknown'),
                confidence=best_sim,
            )

        return MatchResult()

    def match_all(self, embedding: np.ndarray, top_k: int = 5) -> list:
        """
        Return top-K matches sorted by similarity (for debugging/analysis).

        Returns:
            List of (student_id, name, similarity) tuples
        """
        if not self._embeddings:
            return []

        scores = []
        for student_id, known_emb in self._embeddings.items():
            sim = float(np.dot(embedding, known_emb))
            scores.append((student_id, self._names.get(student_id, '?'), sim))

        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:top_k]

    def get_stats(self) -> dict:
        return {
            'known_faces': self.known_count,
            'threshold': self.threshold,
            'face_ids': list(self._embeddings.keys()),
        }
