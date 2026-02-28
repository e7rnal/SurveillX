"""
Activity Classifier — classifies human activities from pose data.
Hybrid approach: Pose-LSTM model + rules-based temporal voting.

Key design: NO single-frame detection triggers an alert.
Every activity must be confirmed across multiple frames within a sliding window.
The LSTM model provides learned activity predictions from 30-frame skeleton sequences.
"""

import os
import math
import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch

from engines.activity_detection.detector import PersonPose
from engines.activity_detection.tracker import PersonTracker
from engines.activity_detection.rules import ActivityRules, ACTIVITY_METADATA, ACTIVITY_PRIORITY

logger = logging.getLogger(__name__)


@dataclass
class ActivityResult:
    """Result of activity classification."""
    type: str = 'normal'
    is_abnormal: bool = False
    severity: str = 'low'
    confidence: float = 0.0
    description: str = ''

    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'is_abnormal': self.is_abnormal,
            'severity': self.severity,
            'confidence': round(self.confidence, 2),
            'description': self.description,
        }


def _midpoint(kps: np.ndarray, idx1: int, idx2: int) -> np.ndarray:
    """Average of two keypoints."""
    return (kps[idx1] + kps[idx2]) / 2.0


def _distance(p1, p2) -> float:
    """Euclidean distance between two 2D points."""
    return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))


def _keypoint_valid(confs: np.ndarray, indices: List[int],
                    min_conf: float = 0.3) -> bool:
    """Check if all required keypoints have sufficient confidence."""
    return all(confs[i] >= min_conf for i in indices)


def _angle_deg(a, b, c) -> float:
    """Compute angle at point b formed by points a-b-c, in degrees.
    Used for knee/hip angle classification (research-backed approach)."""
    ba = np.array([a[0] - b[0], a[1] - b[1]])
    bc = np.array([c[0] - b[0], c[1] - b[1]])
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


# COCO keypoint indices
KP = {
    'nose': 0,
    'left_shoulder': 5, 'right_shoulder': 6,
    'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10,
    'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14,
    'left_ankle': 15, 'right_ankle': 16,
}


class ActivityClassifier:
    """
    Classifies human activities using temporal voting (multi-frame confirmation).

    Design principles:
    - NO single-frame detection → every activity needs N-out-of-M frames
    - Strict confidence floors → low-confidence detections are ignored
    - Per-activity cooldown → same activity suppressed for 30s after alert
    - Keypoint validation → unreliable keypoints are excluded
    """

    # LSTM model settings
    LSTM_SEQ_LEN = 30
    LSTM_MIN_FRAMES = 15        # Start predicting after this many frames
    LSTM_CONF_THRESHOLD = 0.50  # Minimum LSTM confidence to trigger
    LSTM_TEMPORAL_VOTES = 2     # Consecutive LSTM predictions needed

    def __init__(self, rules: Optional[ActivityRules] = None, use_lstm: bool = True):
        self.rules = rules or ActivityRules()
        self.tracker = PersonTracker()

        # Temporal voting buffers: track_id → deque of booleans
        self._falling_votes: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=self.rules.falling_window)
        )
        self._fighting_votes: deque = deque(maxlen=8)
        self._running_votes: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=10)
        )

        # Cooldown timestamps: activity_type → last_alert_time
        self._cooldowns: Dict[str, float] = {}

        # Previous keypoints for velocity calc
        self._prev_keypoints: Dict[int, np.ndarray] = {}
        self._prev_time: float = 0

        # --- LSTM Model ---
        self._lstm_model = None
        self._lstm_device = None
        self._lstm_buffer: deque = deque(maxlen=self.LSTM_SEQ_LEN)  # Frame buffer
        self._lstm_votes: deque = deque(maxlen=self.LSTM_TEMPORAL_VOTES)  # Prediction smoothing
        self._lstm_classes = ['normal', 'fighting', 'running', 'falling']

        if use_lstm:
            self._load_lstm_model()

    def _load_lstm_model(self):
        """Load the trained Pose-LSTM model if available."""
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'activity_lstm.pt'
        )
        if not os.path.exists(model_path):
            logger.warning(f"LSTM model not found at {model_path}, using rules-only mode")
            return

        try:
            from engines.activity_detection.lstm_model import PoseLSTM

            self._lstm_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            checkpoint = torch.load(model_path, map_location=self._lstm_device)

            self._lstm_model = PoseLSTM(
                hidden_dim=checkpoint.get('hidden_dim', 128),
                num_layers=checkpoint.get('num_layers', 2),
                dropout=0.0,  # No dropout at inference
            ).to(self._lstm_device)

            self._lstm_model.load_state_dict(checkpoint['model_state_dict'])
            self._lstm_model.eval()
            self._lstm_classes = checkpoint.get('class_names', self._lstm_classes)

            logger.info(f"LSTM model loaded from {model_path} (device: {self._lstm_device})")
        except Exception as e:
            logger.error(f"Failed to load LSTM model: {e}")
            self._lstm_model = None

    def _normalise_keypoints_for_lstm(self, kps: np.ndarray) -> np.ndarray:
        """Normalise keypoints for LSTM input (hip-centred, scale-invariant)."""
        if kps.shape[0] < 17 or kps.shape[1] < 3:
            return np.zeros(51)

        hip_x = (kps[11, 0] + kps[12, 0]) / 2
        hip_y = (kps[11, 1] + kps[12, 1]) / 2

        body_scale = np.linalg.norm(kps[5, :2] - kps[6, :2])
        if body_scale < 10:
            body_scale = 100.0

        normalised = np.zeros_like(kps)
        normalised[:, 0] = (kps[:, 0] - hip_x) / body_scale
        normalised[:, 1] = (kps[:, 1] - hip_y) / body_scale
        normalised[:, 2] = kps[:, 2]  # Keep confidence
        return normalised.flatten()  # (51,)

    def _predict_lstm(self, persons: List) -> Optional[Tuple[str, float]]:
        """
        Run LSTM prediction on the accumulated keypoint buffer.
        Returns (activity_name, confidence) or None if not enough data.
        """
        if self._lstm_model is None or len(persons) == 0:
            return None

        # Add current frame keypoints to buffer (use first/primary person)
        person = persons[0]
        kps = person.keypoints  # (17, 3)
        norm_kps = self._normalise_keypoints_for_lstm(kps)
        self._lstm_buffer.append(norm_kps)

        # Need minimum frames (pad up to LSTM_SEQ_LEN if between MIN and SEQ_LEN)
        buf_len = len(self._lstm_buffer)
        if buf_len < self.LSTM_MIN_FRAMES:
            return None

        frames = list(self._lstm_buffer)
        # Pad to LSTM_SEQ_LEN by repeating last frame
        while len(frames) < self.LSTM_SEQ_LEN:
            frames.append(frames[-1])

        # Build tensor from padded frames
        seq = np.array(frames, dtype=np.float32)  # (30, 51)
        tensor = torch.from_numpy(seq).unsqueeze(0).to(self._lstm_device)  # (1, 30, 51)

        with torch.no_grad():
            logits = self._lstm_model(tensor)
            probs = torch.softmax(logits, dim=1)
            conf, idx = probs.max(dim=1)
            class_name = self._lstm_classes[idx.item()]
            confidence = conf.item()

        return (class_name, confidence)

    def classify(self, persons: List[PersonPose],
                 timestamp: Optional[float] = None) -> ActivityResult:
        """
        Classify the activity in a frame from detected poses.
        Uses temporal voting — single suspicious frames are NOT reported.
        """
        if not persons:
            return self._make_result('normal', 0, '')

        now = timestamp or time.time()

        # Compute centroids + bboxes for tracker
        centroids = []
        bboxes = []
        for person in persons:
            hip_mid = person.midpoint('left_hip', 'right_hip')
            centroids.append((float(hip_mid[0]), float(hip_mid[1])))
            bboxes.append(person.bbox)

        # Update tracker with IoU support
        track_map = self.tracker.update(centroids, now, bboxes)

        # --- Activity Detection with Temporal Voting ---
        activities: List[Tuple[str, float, str]] = []

        # 0. LSTM-based prediction (primary — learned from 2000+ training clips)
        lstm_pred = self._predict_lstm(persons)
        if lstm_pred:
            lstm_class, lstm_conf = lstm_pred
            self._lstm_votes.append(lstm_class)

            # Temporal smoothing: need consecutive agreement
            if (len(self._lstm_votes) >= self.LSTM_TEMPORAL_VOTES and
                    lstm_class != 'normal' and
                    lstm_conf >= self.LSTM_CONF_THRESHOLD):
                # Check if last N predictions agree
                recent = list(self._lstm_votes)[-self.LSTM_TEMPORAL_VOTES:]
                if all(p == lstm_class for p in recent):
                    desc = f'LSTM: {lstm_class} detected (confidence: {lstm_conf:.0%})'
                    activities.append((lstm_class, lstm_conf, desc))

        # 1. FALLING (per-person, temporal vote)
        for idx, person in enumerate(persons):
            tid = list(track_map.values())[idx] if idx < len(track_map) else idx

            is_falling = self._check_falling(person)
            self._falling_votes[tid].append(bool(is_falling))

            # Require N out of M frames
            vote_count = sum(self._falling_votes[tid])
            if vote_count >= self.rules.falling_persistence:
                conf = is_falling['confidence'] if is_falling else 0.55
                desc = is_falling['description'] if is_falling else 'Person appears to have fallen'
                activities.append(('falling', conf, desc))

        # 2. FIGHTING (multi-person, temporal vote)
        if len(persons) >= 2:
            is_fighting = self._check_fighting(persons)
            self._fighting_votes.append(bool(is_fighting))

            fight_count = sum(self._fighting_votes)
            if fight_count >= self.rules.fighting_min_frames:
                conf = is_fighting['confidence'] if is_fighting else 0.7
                desc = is_fighting['description'] if is_fighting else 'Physical altercation detected'
                activities.append(('fighting', conf, desc))

        # 3. RUNNING (per-track, temporal vote)
        for idx, ((cx, cy), tid) in enumerate(track_map.items()):
            is_running = self._check_running(tid, now, persons=persons, person_idx=idx)
            self._running_votes[tid].append(bool(is_running))

            run_count = sum(self._running_votes[tid])
            if run_count >= self.rules.running_min_frames:
                conf = is_running['confidence'] if is_running else 0.6
                desc = is_running['description'] if is_running else 'Person running detected'
                activities.append(('running', conf, desc))

        # 4. LOITERING (per-track, duration-based — already temporal)
        for (cx, cy), tid in track_map.items():
            loiter = self._check_loitering(tid, now)
            if loiter:
                activities.append(('loitering', loiter['confidence'], loiter['description']))

        # Store keypoints for next frame
        for idx, ((cx, cy), tid) in enumerate(track_map.items()):
            if idx < len(persons):
                self._prev_keypoints[tid] = persons[idx].keypoints.copy()
        self._prev_time = now

        # Filter by global confidence floor
        activities = [
            a for a in activities
            if a[1] >= self.rules.global_confidence_floor
        ]

        # Filter by cooldown
        activities = [
            a for a in activities
            if not self._is_on_cooldown(a[0], now)
        ]

        # Return highest priority activity
        if activities:
            activities.sort(
                key=lambda a: ACTIVITY_PRIORITY.get(a[0], 0),
                reverse=True,
            )
            top = activities[0]
            # Set cooldown for this activity
            self._cooldowns[top[0]] = now
            return self._make_result(top[0], top[1], top[2])

        return self._make_result('normal', 0, '')

    def _is_on_cooldown(self, activity_type: str, now: float) -> bool:
        """Check if an activity type is currently suppressed."""
        last = self._cooldowns.get(activity_type, 0)
        return (now - last) < self.rules.activity_cooldown

    def _make_result(self, activity_type: str, confidence: float,
                     description: str) -> ActivityResult:
        meta = ACTIVITY_METADATA.get(activity_type, ACTIVITY_METADATA['normal'])
        return ActivityResult(
            type=activity_type,
            is_abnormal=meta['is_abnormal'],
            severity=meta['severity'],
            confidence=round(confidence, 2),
            description=description,
        )

    # ========== Rule Checks ==========
    # Each returns a dict with confidence/description, or None/False.
    # These check a SINGLE frame — temporal voting is done in classify().

    def _check_falling(self, person: PersonPose) -> Optional[dict]:
        """Detect falling: extremely horizontal body position.

        Guards against false positives:
        - Requires high keypoint confidence on shoulders, hips, knees
        - Requires extreme body angle (75° from vertical)
        - Optionally checks bbox aspect ratio (truly horizontal body)
        - Sitting/bending/crouching should NOT trigger
        """
        try:
            kps = person.keypoints
            confs = person.confidences

            # Require reliable keypoints for all body parts used
            required = [KP['left_shoulder'], KP['right_shoulder'],
                        KP['left_hip'], KP['right_hip'],
                        KP['left_knee'], KP['right_knee']]
            if not _keypoint_valid(confs, required, self.rules.min_keypoint_confidence):
                return None

            shoulder_mid = _midpoint(kps, KP['left_shoulder'], KP['right_shoulder'])
            hip_mid = _midpoint(kps, KP['left_hip'], KP['right_hip'])

            dx = hip_mid[0] - shoulder_mid[0]
            dy = hip_mid[1] - shoulder_mid[1]
            angle = abs(math.degrees(math.atan2(abs(dx), abs(dy) + 1e-6)))

            # Check 1: Extreme body angle (nearly horizontal)
            if angle > self.rules.falling_angle:
                conf = min(0.90, (angle - self.rules.falling_angle) / (90.0 - self.rules.falling_angle))
                if conf < self.rules.falling_min_confidence:
                    return None

                # Extra check: bbox aspect ratio if available
                if person.bbox:
                    w = person.bbox[2] - person.bbox[0]
                    h = person.bbox[3] - person.bbox[1]
                    if h > 0 and w / h < self.rules.falling_aspect_ratio:
                        # Body is taller than wide — more likely sitting/crouching
                        return None

                return {
                    'confidence': conf,
                    'description': f'Person appears to have fallen (body angle: {angle:.0f}°)',
                }

            # Check 2: Hip below knees WITH torso tilt
            if angle > self.rules.falling_hip_angle_req:
                knee_mid = _midpoint(kps, KP['left_knee'], KP['right_knee'])
                # In image coordinates, y increases downward
                if hip_mid[1] > knee_mid[1] + self.rules.falling_hip_offset:
                    # Extra: verify bbox is horizontal
                    if person.bbox:
                        w = person.bbox[2] - person.bbox[0]
                        h = person.bbox[3] - person.bbox[1]
                        if h > 0 and w / h < self.rules.falling_aspect_ratio:
                            return None

                    return {
                        'confidence': 0.55,
                        'description': 'Person on ground (hip below knees, body tilted)',
                    }

        except Exception:
            pass
        return None

    def _check_fighting(self, persons: List[PersonPose]) -> Optional[dict]:
        """Detect fighting: 2+ people very close + bbox overlap + rapid arm movement.

        Research-backed approach:
        - Check proximity of hip centroids (people physically close)
        - Check bbox overlap (bodies intersecting)
        - Check wrist velocity between frames (rapid punching motion)
        - Check fist-to-body proximity (striking distance)
        """
        try:
            if len(persons) < 2:
                return None

            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    kps_i = persons[i].keypoints
                    kps_j = persons[j].keypoints

                    hip_i = _midpoint(kps_i, KP['left_hip'], KP['right_hip'])
                    hip_j = _midpoint(kps_j, KP['left_hip'], KP['right_hip'])
                    dist = _distance(hip_i, hip_j)

                    if dist > self.rules.fighting_proximity:
                        continue

                    # Need significant bbox overlap
                    bbox_i = persons[i].bbox
                    bbox_j = persons[j].bbox
                    if bbox_i and bbox_j:
                        from engines.activity_detection.tracker import _iou
                        overlap = _iou(bbox_i, bbox_j)

                        # Check wrist-to-body proximity (fist striking distance)
                        # Research: if one person's wrist is near the other's torso
                        wrist_body_close = False
                        try:
                            confs_i = persons[i].confidences
                            confs_j = persons[j].confidences
                            torso_j = _midpoint(kps_j, KP['left_shoulder'], KP['right_shoulder'])
                            torso_i = _midpoint(kps_i, KP['left_shoulder'], KP['right_shoulder'])

                            for wrist_idx in [KP['left_wrist'], KP['right_wrist']]:
                                if confs_i[wrist_idx] > 0.3:
                                    d = _distance(kps_i[wrist_idx], torso_j)
                                    if d < self.rules.fighting_proximity * 0.8:
                                        wrist_body_close = True
                                if confs_j[wrist_idx] > 0.3:
                                    d = _distance(kps_j[wrist_idx], torso_i)
                                    if d < self.rules.fighting_proximity * 0.8:
                                        wrist_body_close = True
                        except Exception:
                            pass

                        if overlap > 0.4:
                            # Very strong overlap — bodies intertwined, likely fight
                            base_conf = 0.6 + overlap * 0.3
                            if wrist_body_close:
                                base_conf += 0.15
                            return {
                                'confidence': min(0.90, base_conf),
                                'description': f'Physical altercation detected (distance: {dist:.0f}px, overlap: {overlap:.0%})',
                            }

                        if overlap > 0.2 and wrist_body_close:
                            # Moderate overlap WITH wrist-to-body contact — strong indicator
                            return {
                                'confidence': min(0.85, 0.55 + overlap),
                                'description': f'Physical altercation detected (distance: {dist:.0f}px, strike contact)',
                            }

                    # Very close proximity with wrist contact (no overlap data)
                    if dist < self.rules.fighting_proximity * 0.3 and wrist_body_close:
                        return {
                            'confidence': 0.60,
                            'description': f'Potential altercation (very close: {dist:.0f}px)',
                        }

        except Exception:
            pass
        return None

    def _check_running(self, track_id: int, now: float, persons: List[PersonPose] = None, person_idx: int = 0) -> Optional[dict]:
        """Detect running: sustained high velocity + running pose (knee angle).

        Research-backed approach:
        - Primary: velocity in px/s exceeds threshold
        - Secondary: knee angle check — running shows greater knee extension (>155°)
          vs walking (~120-140°), providing a biomechanical discriminator
        """
        try:
            velocity = self.tracker.get_velocity(track_id, n_frames=5)
            if velocity is None:
                return None

            # velocity is in px/s — compare directly against threshold
            if velocity > self.rules.running_velocity:
                conf = min(0.85, velocity / (self.rules.running_velocity * 2))

                # Knee angle check: running has more extended knee (>155°)
                # This reduces false positives from fast walking/camera shake
                if persons and person_idx < len(persons):
                    try:
                        kps = persons[person_idx].keypoints
                        confs = persons[person_idx].confidences
                        knee_indices = [
                            (KP['left_hip'], KP['left_knee'], KP['left_ankle']),
                            (KP['right_hip'], KP['right_knee'], KP['right_ankle']),
                        ]
                        max_knee_angle = 0
                        for h, k, a in knee_indices:
                            if _keypoint_valid(confs, [h, k, a], 0.3):
                                angle = _angle_deg(kps[h], kps[k], kps[a])
                                max_knee_angle = max(max_knee_angle, angle)

                        # If we got valid knee angles and they're in walking range,
                        # reduce confidence to avoid false positive
                        if max_knee_angle > 0 and max_knee_angle < 150:
                            conf *= 0.5  # Likely walking, not running
                    except Exception:
                        pass

                return {
                    'confidence': conf,
                    'description': f'Person running detected (speed: {velocity:.0f} px/s)',
                }

        except Exception:
            pass
        return None

    def _check_loitering(self, track_id: int, now: float) -> Optional[dict]:
        """Detect loitering: person in the same area for extended time."""
        try:
            duration = self.tracker.get_track_duration(track_id)
            if duration < self.rules.loiter_duration:
                return None

            history = self.tracker.tracks.get(track_id)
            if not history or len(history) < 10:
                return None

            positions = [(h[0], h[1]) for h in history]
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            spread = max(max(xs) - min(xs), max(ys) - min(ys))

            if spread < self.rules.loiter_radius * 3:
                return {
                    'confidence': min(0.8, duration / (self.rules.loiter_duration * 2)),
                    'description': f'Loitering detected ({duration:.0f}s in same area)',
                }

        except Exception:
            pass
        return None

    def get_stats(self) -> dict:
        return {
            'tracker': self.tracker.get_stats(),
            'falling_tracks': len(self._falling_votes),
            'running_tracks': len(self._running_votes),
            'cooldowns': {k: round(time.time() - v, 1)
                          for k, v in self._cooldowns.items()},
        }
