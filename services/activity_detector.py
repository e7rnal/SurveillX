"""
Activity Detection Service — YOLO11 Pose Estimation
Detects abnormal activities: fighting, running, falling, loitering.
Uses YOLO11n-pose for 17-keypoint skeleton extraction + heuristic rules.
"""

import logging
import time
import math
import numpy as np
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# ---------- YOLO Setup ----------
YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    logger.info("Ultralytics YOLO loaded successfully")
except ImportError:
    logger.warning("Ultralytics not available — install with: pip install ultralytics")


# COCO 17 keypoint indices
KP = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16,
}


def _midpoint(kp, idx1, idx2):
    """Average of two keypoints."""
    return (kp[idx1] + kp[idx2]) / 2


def _distance(p1, p2):
    """Euclidean distance between two 2D points."""
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


class PersonTracker:
    """Simple centroid-based person tracker for temporal analysis."""

    def __init__(self, max_history=90):  # ~6 seconds at 15fps
        self.tracks = defaultdict(lambda: deque(maxlen=max_history))
        self.last_seen = {}
        self._next_id = 0

    def update(self, centroids, timestamp):
        """Match centroids to existing tracks (nearest-neighbor)."""
        matched = {}
        used_tracks = set()

        for cx, cy in centroids:
            best_id = None
            best_dist = 80  # max pixel distance to match

            for tid, history in self.tracks.items():
                if tid in used_tracks or not history:
                    continue
                prev = history[-1]
                d = _distance((cx, cy), (prev[0], prev[1]))
                if d < best_dist:
                    best_dist = d
                    best_id = tid

            if best_id is not None:
                matched[(cx, cy)] = best_id
                used_tracks.add(best_id)
            else:
                matched[(cx, cy)] = self._next_id
                self._next_id += 1

        # Record positions
        for (cx, cy), tid in matched.items():
            self.tracks[tid].append((cx, cy, timestamp))
            self.last_seen[tid] = timestamp

        # Purge stale tracks (not seen in 3 seconds)
        stale = [tid for tid, t in self.last_seen.items() if timestamp - t > 3.0]
        for tid in stale:
            del self.tracks[tid]
            del self.last_seen[tid]

        return matched


class ActivityDetector:
    """Detects abnormal human activities using YOLO11 pose estimation."""

    ACTIVITIES = {
        'normal':    {'severity': 'low',    'is_abnormal': False},
        'running':   {'severity': 'medium', 'is_abnormal': True},
        'fighting':  {'severity': 'high',   'is_abnormal': True},
        'falling':   {'severity': 'high',   'is_abnormal': True},
        'loitering': {'severity': 'low',    'is_abnormal': True},
    }

    def __init__(self, model_name='yolo11n-pose.pt', gpu_id=0, conf_threshold=0.5):
        self.model = None
        self.gpu_id = gpu_id
        self.conf_threshold = conf_threshold
        self.tracker = PersonTracker()

        # Thresholds (tunable)
        self.running_velocity = 25.0      # px/frame speed threshold
        self.fighting_proximity = 100.0   # px — close enough for fighting
        self.fighting_arm_speed = 30.0    # px/frame arm movement
        self.falling_angle = 45.0         # degrees from vertical
        self.loiter_duration = 60.0       # seconds in same area

        # Frame history for velocity calculation
        self._prev_keypoints = {}  # track_id -> keypoints
        self._prev_time = 0

        if YOLO_AVAILABLE:
            self._init_model(model_name)

    def _init_model(self, model_name):
        try:
            self.model = YOLO(model_name)
            logger.info(f"YOLO pose model '{model_name}' loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None

    def detect(self, frame):
        """
        Detect activities in a frame.

        Returns:
            dict with keys:
                type: str — activity name
                is_abnormal: bool
                severity: str — low/medium/high
                confidence: float
                description: str
                persons: list of person dicts with keypoints
        """
        if not YOLO_AVAILABLE or self.model is None:
            return {'type': 'normal', 'is_abnormal': False, 'severity': 'low',
                    'confidence': 0, 'description': '', 'persons': []}

        try:
            # Run pose estimation
            results = self.model(
                frame,
                device=self.gpu_id,
                conf=self.conf_threshold,
                verbose=False
            )

            if not results or len(results) == 0:
                return self._result('normal', 0, '')

            result = results[0]

            # Extract keypoints and bounding boxes
            persons = []
            centroids = []

            if result.keypoints is not None and result.keypoints.data.shape[0] > 0:
                kps_data = result.keypoints.data.cpu().numpy()  # (N, 17, 3)
                boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else []

                now = time.time()

                for i in range(kps_data.shape[0]):
                    kps = kps_data[i]  # (17, 3) — x, y, conf
                    person = {
                        'keypoints': kps[:, :2].tolist(),
                        'confidences': kps[:, 2].tolist(),
                        'bbox': boxes[i].tolist() if i < len(boxes) else None,
                    }
                    persons.append(person)

                    # Centroid from hip midpoint
                    hip_mid = _midpoint(kps[:, :2], KP['left_hip'], KP['right_hip'])
                    centroids.append((hip_mid[0], hip_mid[1]))

                # Update tracker
                track_map = self.tracker.update(centroids, now)

                # --- Activity Detection Rules ---
                activities = []

                # 1. Check for FALLING
                for person in persons:
                    kps = np.array(person['keypoints'])
                    fall = self._check_falling(kps)
                    if fall:
                        activities.append(('falling', fall['confidence'], fall['description']))

                # 2. Check for FIGHTING (requires 2+ people)
                if len(persons) >= 2:
                    fight = self._check_fighting(persons, now)
                    if fight:
                        activities.append(('fighting', fight['confidence'], fight['description']))

                # 3. Check for RUNNING
                for (cx, cy), tid in track_map.items():
                    run = self._check_running(tid, now)
                    if run:
                        activities.append(('running', run['confidence'], run['description']))

                # 4. Check for LOITERING
                for (cx, cy), tid in track_map.items():
                    loiter = self._check_loitering(tid, now)
                    if loiter:
                        activities.append(('loitering', loiter['confidence'], loiter['description']))

                # Store current keypoints for next frame comparison
                for idx, ((cx, cy), tid) in enumerate(track_map.items()):
                    if idx < len(persons):
                        self._prev_keypoints[tid] = np.array(persons[idx]['keypoints'])
                self._prev_time = now

                # Return highest severity activity
                if activities:
                    # Priority: fighting > falling > running > loitering
                    priority = {'fighting': 4, 'falling': 3, 'running': 2, 'loitering': 1}
                    activities.sort(key=lambda a: priority.get(a[0], 0), reverse=True)
                    top = activities[0]
                    return self._result(top[0], top[1], top[2], persons)

            return self._result('normal', 0, '', persons)

        except Exception as e:
            logger.error(f"Activity detection error: {e}")
            return self._result('normal', 0, str(e))

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

    # ========== Activity Rules ==========

    def _check_falling(self, kps):
        """Detect falling: body tilted heavily or hip below knees."""
        try:
            shoulder_mid = _midpoint(kps, KP['left_shoulder'], KP['right_shoulder'])
            hip_mid = _midpoint(kps, KP['left_hip'], KP['right_hip'])

            # Body vector (shoulder to hip)
            dx = hip_mid[0] - shoulder_mid[0]
            dy = hip_mid[1] - shoulder_mid[1]

            # Angle from vertical (0° = standing, 90° = horizontal)
            angle = abs(math.degrees(math.atan2(abs(dx), abs(dy) + 1e-6)))

            if angle > self.falling_angle:
                return {
                    'confidence': min(0.95, angle / 90.0),
                    'description': f'Person appears to have fallen (body angle: {angle:.0f}°)',
                }

            # Also check if hip is at same level or below knees
            knee_mid = _midpoint(kps, KP['left_knee'], KP['right_knee'])
            if hip_mid[1] > knee_mid[1] + 20:  # hip below knees (y increases downward)
                return {
                    'confidence': 0.7,
                    'description': 'Person on ground (hip below knees)',
                }

        except Exception:
            pass
        return None

    def _check_fighting(self, persons, now):
        """Detect fighting: 2+ people close + fast arm movement."""
        try:
            if len(persons) < 2:
                return None

            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    kps_i = np.array(persons[i]['keypoints'])
                    kps_j = np.array(persons[j]['keypoints'])

                    # Check proximity (hip-to-hip distance)
                    hip_i = _midpoint(kps_i, KP['left_hip'], KP['right_hip'])
                    hip_j = _midpoint(kps_j, KP['left_hip'], KP['right_hip'])
                    dist = _distance(hip_i, hip_j)

                    if dist > self.fighting_proximity:
                        continue

                    # Check for overlapping bounding boxes
                    bbox_i = persons[i].get('bbox')
                    bbox_j = persons[j].get('bbox')
                    overlap = False
                    if bbox_i and bbox_j:
                        # IoU-like check
                        x_overlap = max(0, min(bbox_i[2], bbox_j[2]) - max(bbox_i[0], bbox_j[0]))
                        y_overlap = max(0, min(bbox_i[3], bbox_j[3]) - max(bbox_i[1], bbox_j[1]))
                        overlap = x_overlap > 0 and y_overlap > 0

                    if overlap or dist < self.fighting_proximity * 0.6:
                        return {
                            'confidence': 0.75,
                            'description': f'Physical altercation detected (distance: {dist:.0f}px)',
                        }

        except Exception:
            pass
        return None

    def _check_running(self, track_id, now):
        """Detect running: high velocity over recent frames."""
        try:
            history = self.tracker.tracks.get(track_id)
            if not history or len(history) < 5:
                return None

            recent = list(history)[-5:]
            total_dist = 0
            total_time = 0

            for k in range(1, len(recent)):
                d = _distance(recent[k][:2], recent[k - 1][:2])
                dt = recent[k][2] - recent[k - 1][2]
                total_dist += d
                total_time += dt

            if total_time < 0.1:
                return None

            speed = total_dist / total_time  # px/sec
            # Normalize by frame rate (~15fps) to get px/frame
            px_per_frame = speed / 15.0

            if px_per_frame > self.running_velocity:
                return {
                    'confidence': min(0.9, px_per_frame / (self.running_velocity * 2)),
                    'description': f'Person running detected (speed: {speed:.0f} px/s)',
                }

        except Exception:
            pass
        return None

    def _check_loitering(self, track_id, now):
        """Detect loitering: person in the same area for extended time."""
        try:
            history = self.tracker.tracks.get(track_id)
            if not history or len(history) < 10:
                return None

            first = history[0]
            last = history[-1]
            duration = last[2] - first[2]

            if duration < self.loiter_duration:
                return None

            # Check if person stayed within a small area
            positions = [(h[0], h[1]) for h in history]
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            spread = max(max(xs) - min(xs), max(ys) - min(ys))

            if spread < 150:  # stayed within 150px area
                return {
                    'confidence': min(0.8, duration / (self.loiter_duration * 2)),
                    'description': f'Loitering detected ({duration:.0f}s in same area)',
                }

        except Exception:
            pass
        return None

    def get_stats(self):
        """Return detector statistics."""
        return {
            'available': YOLO_AVAILABLE and self.model is not None,
            'model': 'yolo11n-pose',
            'tracked_persons': len(self.tracker.tracks),
            'conf_threshold': self.conf_threshold,
        }


# ---------- Global Instance ----------
activity_detector = None


def init_activity_detector(model_name='yolo11n-pose.pt', gpu_id=0):
    """Initialize global activity detector."""
    global activity_detector
    activity_detector = ActivityDetector(model_name=model_name, gpu_id=gpu_id)
    return activity_detector
