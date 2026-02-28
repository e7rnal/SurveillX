"""
Person Tracker — centroid + IoU hybrid tracker for temporal analysis.
Assigns persistent IDs to detected persons across frames with timestamped history.
Supports velocity calculation for running detection.
"""

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Track entry: (x, y, timestamp)
TrackEntry = Tuple[float, float, float]


def _iou(box_a, box_b) -> float:
    """Compute Intersection-over-Union between two [x1,y1,x2,y2] boxes."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / (area_a + area_b - inter + 1e-6)


class PersonTracker:
    """
    Centroid + IoU hybrid person tracker for temporal analysis.

    Matches detections across frames using:
    1. IoU overlap between bounding boxes (preferred)
    2. Centroid distance fallback (when IoU is ambiguous)

    Stores timestamped position history for velocity and loitering.
    """

    def __init__(self, max_history: int = 150, max_distance: float = 120.0,
                 iou_threshold: float = 0.2, stale_timeout: float = 3.0):
        """
        Args:
            max_history: past positions per track (~10s at 15fps)
            max_distance: max pixel distance for centroid matching
            iou_threshold: minimum IoU to match via bounding box
            stale_timeout: seconds before a track is removed
        """
        self.max_history = max_history
        self.max_distance = max_distance
        self.iou_threshold = iou_threshold
        self.stale_timeout = stale_timeout

        self.tracks: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=max_history)
        )
        self.last_seen: Dict[int, float] = {}
        self.last_bbox: Dict[int, List[float]] = {}
        self._next_id = 0

    def _distance(self, p1: Tuple, p2: Tuple) -> float:
        return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))

    def update(self, centroids: List[Tuple[float, float]],
               timestamp: float,
               bboxes: Optional[List[List[float]]] = None) -> Dict[Tuple[float, float], int]:
        """
        Match new detections to existing tracks.

        Args:
            centroids: list of (x, y) person center positions
            timestamp: current time (seconds)
            bboxes: optional list of [x1,y1,x2,y2] per person (for IoU matching)

        Returns:
            dict mapping (cx, cy) → track_id
        """
        matched: Dict[Tuple[float, float], int] = {}
        used_tracks = set()

        for idx, (cx, cy) in enumerate(centroids):
            best_tid = None
            best_score = -1.0

            bbox = bboxes[idx] if bboxes and idx < len(bboxes) else None

            for tid, history in self.tracks.items():
                if tid in used_tracks or not history:
                    continue

                score = 0.0

                # Try IoU first (if bboxes available)
                if bbox and tid in self.last_bbox:
                    iou_val = _iou(bbox, self.last_bbox[tid])
                    if iou_val >= self.iou_threshold:
                        score = iou_val + 1.0  # IoU scores get priority

                # Centroid distance fallback
                if score < 0.01:
                    last_entry = history[-1]
                    dist = self._distance((cx, cy), (last_entry[0], last_entry[1]))
                    if dist < self.max_distance:
                        score = 1.0 - (dist / self.max_distance)

                if score > best_score:
                    best_score = score
                    best_tid = tid

            if best_tid is None or best_score <= 0:
                best_tid = self._next_id
                self._next_id += 1

            # Store (x, y, timestamp)
            self.tracks[best_tid].append((cx, cy, timestamp))
            self.last_seen[best_tid] = timestamp
            if bbox:
                self.last_bbox[best_tid] = bbox
            matched[(cx, cy)] = best_tid
            used_tracks.add(best_tid)

        # Purge stale tracks
        stale = [tid for tid, t in self.last_seen.items()
                 if timestamp - t > self.stale_timeout]
        for tid in stale:
            self.tracks.pop(tid, None)
            self.last_seen.pop(tid, None)
            self.last_bbox.pop(tid, None)

        return matched

    def get_velocity(self, track_id: int, n_frames: int = 5) -> Optional[float]:
        """
        Calculate average velocity (px/sec) for a track over the last N frames.

        Returns:
            float velocity in px/sec, or None if insufficient data
        """
        history = self.tracks.get(track_id)
        if not history or len(history) < max(2, n_frames):
            return None

        recent = list(history)[-n_frames:]
        total_dist = 0.0
        total_time = 0.0

        for k in range(1, len(recent)):
            d = self._distance(recent[k][:2], recent[k - 1][:2])
            dt = recent[k][2] - recent[k - 1][2]
            total_dist += d
            total_time += dt

        if total_time < 0.05:
            return None

        return total_dist / total_time

    def get_track_history(self, track_id: int) -> List[TrackEntry]:
        """Get position+timestamp history for a given track."""
        return list(self.tracks.get(track_id, []))

    def get_track_duration(self, track_id: int) -> float:
        """Get how long a track has been observed (seconds)."""
        history = self.tracks.get(track_id)
        if not history or len(history) < 2:
            return 0.0
        return history[-1][2] - history[0][2]

    def get_stats(self) -> dict:
        return {
            'active_tracks': len(self.tracks),
            'next_id': self._next_id,
        }
