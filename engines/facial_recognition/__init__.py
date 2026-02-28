"""
Facial Recognition Engine
Provides face detection, encoding, and matching using InsightFace Buffalo_L.

Usage:
    from engines.facial_recognition import FaceDetector, FaceEncoder, FaceMatcher

    detector = FaceDetector(gpu_id=0)
    encoder  = FaceEncoder(detector)
    matcher  = FaceMatcher(threshold=0.4)
"""

from engines.facial_recognition.detector import FaceDetector, DetectedFace
from engines.facial_recognition.encoder import FaceEncoder, EncodingResult
from engines.facial_recognition.matcher import FaceMatcher, MatchResult

__all__ = [
    'FaceDetector', 'DetectedFace',
    'FaceEncoder', 'EncodingResult',
    'FaceMatcher', 'MatchResult',
]
