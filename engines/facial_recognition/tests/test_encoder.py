"""
Tests for FaceEncoder engine module.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from engines.facial_recognition.detector import DetectedFace, BoundingBox
from engines.facial_recognition.encoder import FaceEncoder, EncodingResult


class TestEncodingResult:
    def test_success_property(self):
        result = EncodingResult(embedding=[1.0] * 512, valid_count=5, total_count=5)
        assert result.success is True

    def test_failure_property(self):
        result = EncodingResult(embedding=None, valid_count=1, total_count=5,
                                errors=['Not enough photos'])
        assert result.success is False


class TestFaceEncoder:
    def _make_encoder(self, faces=None):
        """Create encoder with mocked detector."""
        detector = MagicMock()
        detector.available = True
        if faces is not None:
            detector.detect.return_value = faces
        encoder = FaceEncoder(detector)
        return encoder

    def test_encode_single_no_faces(self):
        encoder = self._make_encoder(faces=[])
        result = encoder.encode_single(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result is None

    def test_encode_single_success(self):
        emb = np.random.randn(512).astype(np.float32)
        face = DetectedFace(
            bbox=BoundingBox(0, 0, 100, 100),
            embedding=emb,
        )
        encoder = self._make_encoder(faces=[face])
        result = encoder.encode_single(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result is not None
        assert len(result) == 512

    def test_encode_single_picks_largest(self):
        small_face = DetectedFace(
            bbox=BoundingBox(0, 0, 50, 50),
            embedding=np.ones(512, dtype=np.float32),
        )
        big_face = DetectedFace(
            bbox=BoundingBox(0, 0, 200, 200),
            embedding=np.ones(512, dtype=np.float32) * 2,
        )
        encoder = self._make_encoder(faces=[small_face, big_face])
        result = encoder.encode_single(np.zeros((200, 200, 3), dtype=np.uint8))
        # Should pick the big face
        assert result is not None
        assert result[0] == 2.0

    def test_encode_multiple_not_enough(self):
        encoder = self._make_encoder(faces=[])
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
        result = encoder.encode_multiple(frames, min_valid=3)
        assert result.success is False
        assert result.valid_count == 0

    def test_encode_multiple_success(self):
        emb = np.random.randn(512).astype(np.float32)
        emb /= np.linalg.norm(emb)
        face = DetectedFace(bbox=BoundingBox(0, 0, 100, 100), embedding=emb)
        encoder = self._make_encoder(faces=[face])
        frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
        result = encoder.encode_multiple(frames, min_valid=3)
        assert result.success is True
        assert result.valid_count == 5
        assert len(result.embedding) == 512

    def test_encoder_unavailable(self):
        detector = MagicMock()
        detector.available = False
        encoder = FaceEncoder(detector)
        assert encoder.encode_single(np.zeros((100, 100, 3))) is None
