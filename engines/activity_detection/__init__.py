"""
Activity Detection Engine
Provides pose detection and activity classification using YOLO11-pose.

Usage:
    from engines.activity_detection import PoseDetector, ActivityClassifier, ActivityRules

    detector   = PoseDetector(gpu_id=0)
    rules      = ActivityRules()
    classifier = ActivityClassifier(rules=rules)

    poses = detector.detect(frame)
    result = classifier.classify(poses)
"""

from engines.activity_detection.detector import PoseDetector, PersonPose
from engines.activity_detection.classifier import ActivityClassifier, ActivityResult
from engines.activity_detection.rules import ActivityRules, ACTIVITY_METADATA
from engines.activity_detection.tracker import PersonTracker

__all__ = [
    'PoseDetector', 'PersonPose',
    'ActivityClassifier', 'ActivityResult',
    'ActivityRules', 'ACTIVITY_METADATA',
    'PersonTracker',
]
