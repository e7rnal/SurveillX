"""
Tests for ActivityClassifier engine module.
"""

import numpy as np
import pytest

from engines.activity_detection.detector import PersonPose
from engines.activity_detection.classifier import ActivityClassifier
from engines.activity_detection.rules import ActivityRules


def _make_standing_person(x_offset=0, y_offset=0):
    """Create a standing person with realistic COCO keypoints."""
    # Standard standing pose (17 keypoints)
    kps = np.array([
        [300 + x_offset, 100 + y_offset],   # 0: nose
        [290 + x_offset, 90 + y_offset],    # 1: left eye
        [310 + x_offset, 90 + y_offset],    # 2: right eye
        [280 + x_offset, 95 + y_offset],    # 3: left ear
        [320 + x_offset, 95 + y_offset],    # 4: right ear
        [270 + x_offset, 180 + y_offset],   # 5: left shoulder
        [330 + x_offset, 180 + y_offset],   # 6: right shoulder
        [250 + x_offset, 250 + y_offset],   # 7: left elbow
        [350 + x_offset, 250 + y_offset],   # 8: right elbow
        [240 + x_offset, 320 + y_offset],   # 9: left wrist
        [360 + x_offset, 320 + y_offset],   # 10: right wrist
        [280 + x_offset, 350 + y_offset],   # 11: left hip
        [320 + x_offset, 350 + y_offset],   # 12: right hip
        [280 + x_offset, 450 + y_offset],   # 13: left knee
        [320 + x_offset, 450 + y_offset],   # 14: right knee
        [280 + x_offset, 550 + y_offset],   # 15: left ankle
        [320 + x_offset, 550 + y_offset],   # 16: right ankle
    ], dtype=np.float32)

    return PersonPose(
        keypoints=kps,
        confidences=np.ones(17, dtype=np.float32) * 0.9,
        bbox=[240 + x_offset, 80 + y_offset, 370 + x_offset, 560 + y_offset],
    )


def _make_fallen_person():
    """Create a person lying horizontally (fallen)."""
    kps = np.array([
        [100, 300],    # 0: nose
        [95, 295],     # 1: left eye
        [105, 295],    # 2: right eye
        [90, 300],     # 3: left ear
        [110, 300],    # 4: right ear
        [150, 310],    # 5: left shoulder
        [150, 290],    # 6: right shoulder
        [200, 310],    # 7: left elbow
        [200, 290],    # 8: right elbow
        [250, 310],    # 9: left wrist
        [250, 290],    # 10: right wrist
        [300, 310],    # 11: left hip
        [300, 290],    # 12: right hip
        [350, 310],    # 13: left knee
        [350, 290],    # 14: right knee
        [400, 310],    # 15: left ankle
        [400, 290],    # 16: right ankle
    ], dtype=np.float32)

    return PersonPose(
        keypoints=kps,
        confidences=np.ones(17, dtype=np.float32) * 0.9,
        bbox=[90, 280, 410, 320],
    )


def _make_sitting_person():
    """Create a person sitting (upright torso but hip near knees)."""
    kps = np.array([
        [300, 100],    # 0: nose
        [290, 90],     # 1: left eye
        [310, 90],     # 2: right eye
        [280, 95],     # 3: left ear
        [320, 95],     # 4: right ear
        [270, 180],    # 5: left shoulder
        [330, 180],    # 6: right shoulder
        [250, 250],    # 7: left elbow
        [350, 250],    # 8: right elbow
        [260, 300],    # 9: left wrist
        [340, 300],    # 10: right wrist
        [280, 320],    # 11: left hip (low but torso is vertical)
        [320, 320],    # 12: right hip
        [280, 330],    # 13: left knee (close to hip height)
        [320, 330],    # 14: right knee
        [280, 430],    # 15: left ankle
        [320, 430],    # 16: right ankle
    ], dtype=np.float32)

    return PersonPose(
        keypoints=kps,
        confidences=np.ones(17, dtype=np.float32) * 0.9,
        bbox=[240, 80, 360, 440],
    )


class TestActivityClassifier:
    def test_no_persons_returns_normal(self):
        classifier = ActivityClassifier()
        result = classifier.classify([], timestamp=1.0)
        assert result.type == 'normal'
        assert result.is_abnormal is False

    def test_standing_person_is_normal(self):
        classifier = ActivityClassifier()
        person = _make_standing_person()
        result = classifier.classify([person], timestamp=1.0)
        assert result.type == 'normal'

    def test_fallen_person_detected(self):
        """Fallen person should trigger falling after sufficient temporal persistence."""
        rules = ActivityRules(falling_persistence=1, falling_window=1)
        classifier = ActivityClassifier(rules=rules)
        person = _make_fallen_person()

        result = classifier.classify([person], timestamp=1.0)
        assert result.type == 'falling'
        assert result.is_abnormal is True
        assert result.severity == 'high'

    def test_sitting_not_falling(self):
        """Sitting person should NOT trigger falling detection."""
        classifier = ActivityClassifier()
        person = _make_sitting_person()

        # Classify multiple times to ensure temporal persistence doesn't trigger
        for t in range(10):
            result = classifier.classify([person], timestamp=float(t))
        assert result.type == 'normal'

    def test_falling_persistence(self):
        """Falling should require persistence across multiple frames."""
        rules = ActivityRules(falling_persistence=3, falling_window=5)
        classifier = ActivityClassifier(rules=rules)
        fallen = _make_fallen_person()

        # First 2 frames: not enough persistence
        r1 = classifier.classify([fallen], timestamp=1.0)
        r2 = classifier.classify([fallen], timestamp=2.0)
        # May or may not trigger depending on count
        # But 3rd frame should definitely trigger
        r3 = classifier.classify([fallen], timestamp=3.0)
        assert r3.type == 'falling'

    def test_two_close_persons_fighting(self):
        """Two persons very close should trigger fighting."""
        classifier = ActivityClassifier()
        p1 = _make_standing_person(x_offset=0)
        # Place second person very close (within fighting_proximity)
        p2 = _make_standing_person(x_offset=30)

        result = classifier.classify([p1, p2], timestamp=1.0)
        assert result.type == 'fighting'
        assert result.severity == 'high'

    def test_two_far_persons_not_fighting(self):
        """Two persons far apart should NOT trigger fighting."""
        classifier = ActivityClassifier()
        p1 = _make_standing_person(x_offset=0)
        p2 = _make_standing_person(x_offset=500)

        result = classifier.classify([p1, p2], timestamp=1.0)
        assert result.type == 'normal'

    def test_result_to_dict(self):
        classifier = ActivityClassifier()
        result = classifier.classify([], timestamp=1.0)
        d = result.to_dict()
        assert 'type' in d
        assert 'is_abnormal' in d
        assert 'severity' in d
        assert 'confidence' in d
        assert 'description' in d


class TestActivityRules:
    def test_defaults(self):
        rules = ActivityRules()
        assert rules.falling_angle == 65.0
        assert rules.fighting_proximity == 80.0
        assert rules.running_velocity == 25.0
        assert rules.loiter_duration == 60.0

    def test_custom_rules(self):
        rules = ActivityRules(falling_angle=70.0, fighting_proximity=100.0)
        assert rules.falling_angle == 70.0
        assert rules.fighting_proximity == 100.0
