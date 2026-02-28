"""
Activity Detection Service — thin wrapper over engines/activity_detection.
Maintains backward compatibility for ml_worker.py.
"""

import logging
import time
from typing import Optional

import numpy as np

from engines.activity_detection import (
    PoseDetector, ActivityClassifier, ActivityRules, PersonTracker,
)
from engines.activity_detection.detector import PersonPose

logger = logging.getLogger(__name__)


class ActivityDetector:
    """Activity detection service — delegates to engine modules."""

    ACTIVITIES = {
        'normal':    {'severity': 'low',    'is_abnormal': False},
        'running':   {'severity': 'medium', 'is_abnormal': True},
        'fighting':  {'severity': 'high',   'is_abnormal': True},
        'falling':   {'severity': 'high',   'is_abnormal': True},
        'loitering': {'severity': 'low',    'is_abnormal': True},
    }

    def __init__(self, model_name='yolov8s-pose.pt', gpu_id=0, conf_threshold=0.5):
        # Engine components
        self._pose_detector = PoseDetector(
            model_name=model_name,
            gpu_id=gpu_id,
            conf_threshold=conf_threshold,
            use_half=True,
        )
        self._classifier = ActivityClassifier(rules=ActivityRules())

        # Expose for backward compat
        self.model = self._pose_detector.model
        self.gpu_id = gpu_id
        self.conf_threshold = conf_threshold
        self.tracker = self._classifier.tracker

        # Expose threshold attributes for backward compat
        self.running_velocity = self._classifier.rules.running_velocity
        self.fighting_proximity = self._classifier.rules.fighting_proximity
        self.falling_angle = self._classifier.rules.falling_angle
        self.loiter_duration = self._classifier.rules.loiter_duration

    def detect(self, frame):
        """
        Detect activities in a frame.

        Returns:
            dict with keys: type, is_abnormal, severity, confidence, description, persons
        """
        # Detect poses
        poses = self._pose_detector.detect(frame)

        if not poses:
            return self._result('normal', 0, '')

        # Classify activity with temporal voting
        result = self._classifier.classify(poses)

        # Convert poses to legacy dict format
        persons = [p.to_dict() for p in poses]

        return {
            'type': result.type,
            'is_abnormal': result.is_abnormal,
            'severity': result.severity,
            'confidence': result.confidence,
            'description': result.description,
            'persons': persons,
        }

    def _result(self, activity_type, confidence, description, persons=None):
        meta = self.ACTIVITIES.get(activity_type, self.ACTIVITIES['normal'])
        return {
            'type': activity_type,
            'is_abnormal': meta['is_abnormal'],
            'severity': meta['severity'],
            'confidence': round(confidence, 2),
            'description': description,
            'persons': persons or [],
        }

    def get_stats(self):
        """Return detector statistics."""
        return {
            'available': self._pose_detector.available,
            'model': self._pose_detector.model_name,
            'device': self._pose_detector.device,
            'half': self._pose_detector.use_half,
            'tracked_persons': self._classifier.tracker.get_stats()['active_tracks'],
            'conf_threshold': self.conf_threshold,
            'classifier': self._classifier.get_stats(),
        }


# ---------- Global Instance ----------
activity_detector = None


def init_activity_detector(model_name='yolov8s-pose.pt', gpu_id=0):
    """Initialize global activity detector."""
    global activity_detector
    activity_detector = ActivityDetector(model_name=model_name, gpu_id=gpu_id)
    return activity_detector
