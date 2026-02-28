"""
Activity Rules — configurable thresholds and metadata for activity detection.
All tunable parameters live here for easy adjustment.

IMPORTANT: These thresholds are tuned for a fixed classroom/hallway camera
at ~15 fps on a T4 GPU. Adjust if your setup differs significantly.
"""

from dataclasses import dataclass, field
from typing import Dict


# Activity metadata — severity and abnormality flags
ACTIVITY_METADATA: Dict[str, dict] = {
    'normal':    {'severity': 'low',    'is_abnormal': False},
    'running':   {'severity': 'medium', 'is_abnormal': True},
    'fighting':  {'severity': 'high',   'is_abnormal': True},
    'falling':   {'severity': 'high',   'is_abnormal': True},
    'loitering': {'severity': 'low',    'is_abnormal': True},
}

# Activity priority for conflict resolution (higher = more important)
ACTIVITY_PRIORITY: Dict[str, int] = {
    'fighting': 4,
    'falling': 3,
    'running': 2,
    'loitering': 1,
    'normal': 0,
}


@dataclass
class ActivityRules:
    """
    Configurable thresholds for activity detection rules.
    Tuned to minimize false positives on classroom/office cameras.
    """

    # ── Falling detection ──
    falling_angle: float = 75.0           # degrees from vertical (raised from 65)
    falling_min_confidence: float = 0.50  # minimum confidence to flag (raised from 0.3)
    falling_hip_offset: float = 120.0     # px — hip below knees threshold (raised from 80)
    falling_hip_angle_req: float = 60.0   # degrees — torso tilt required for hip check
    falling_aspect_ratio: float = 1.3     # bbox width/height > this = horizontal body
    falling_persistence: int = 4          # frames out of window (raised from 3)
    falling_window: int = 8              # frame window for persistence check (raised from 5)

    # ── Fighting detection ──
    fighting_proximity: float = 80.0      # px — close enough for fighting (widened from 50 to catch more fights)
    fighting_arm_speed: float = 25.0      # px/frame arm movement (lowered from 30)
    fighting_min_frames: int = 3          # must see fight indicators for N frames (lowered from 5 for shorter clips)

    # ── Running detection ──
    running_velocity: float = 2200.0      # px/s speed threshold (raised from 1800 to reduce false positives)
    running_min_frames: int = 6           # sustained above threshold (raised from 5)

    # ── Loitering detection ──
    loiter_duration: float = 60.0         # seconds in same area
    loiter_radius: float = 50.0           # px — area considered "same place"

    # ── Global ──
    activity_cooldown: float = 5.0        # seconds — suppress repeat of same activity (lowered from 30 for test clips)
    global_confidence_floor: float = 0.45 # activities below this confidence are ignored (lowered from 0.50)
    min_keypoint_confidence: float = 0.3  # keypoints below this are unreliable
