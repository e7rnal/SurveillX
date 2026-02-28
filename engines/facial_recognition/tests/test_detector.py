"""
Tests for FaceDetector engine module.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from engines.facial_recognition.detector import (
    FaceDetector, DetectedFace, BoundingBox, INSIGHTFACE_AVAILABLE,
)


class TestBoundingBox:
    def test_properties(self):
        bbox = BoundingBox(left=10, top=20, right=110, bottom=120)
        assert bbox.width == 100
        assert bbox.height == 100
        assert bbox.area == 10000

    def test_to_dict(self):
        bbox = BoundingBox(left=5, top=10, right=50, bottom=60)
        d = bbox.to_dict()
        assert d == {'left': 5, 'top': 10, 'right': 50, 'bottom': 60}


class TestDetectedFace:
    def test_to_dict(self):
        face = DetectedFace(
            bbox=BoundingBox(0, 0, 100, 100),
            embedding=np.zeros(512),
            age=25,
            gender='M',
            det_score=0.95,
        )
        d = face.to_dict()
        assert d['age'] == 25
        assert d['gender'] == 'M'
        assert d['det_score'] == 0.95
        assert 'location' in d


class TestFaceDetector:
    def test_unavailable_returns_empty(self):
        """Detector should return empty list when model not loaded."""
        detector = FaceDetector.__new__(FaceDetector)
        detector.app = None
        assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) == []

    def test_validate_unavailable(self):
        detector = FaceDetector.__new__(FaceDetector)
        detector.app = None
        result = detector.validate(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result['valid'] is False
        assert 'not available' in result['error']

    def test_stats(self):
        detector = FaceDetector.__new__(FaceDetector)
        detector.app = None
        detector.model_name = 'buffalo_l'
        detector.gpu_id = 0
        detector.det_size = (640, 640)
        stats = detector.get_stats()
        assert stats['available'] is False
        assert stats['model'] == 'buffalo_l'
