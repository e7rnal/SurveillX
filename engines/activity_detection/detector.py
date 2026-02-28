"""
Pose Detector — YOLOv8-pose wrapper.
Detects human poses and extracts 17 COCO keypoints per person.
GPU-accelerated with FP16 on CUDA.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO not installed — pose detection unavailable")


# COCO 17-keypoint indices
KEYPOINT_NAMES = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2,
    'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6,
    'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10,
    'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14,
    'left_ankle': 15, 'right_ankle': 16,
}


@dataclass
class PersonPose:
    """A detected person with pose keypoints."""
    keypoints: np.ndarray          # (17, 2) — x, y coordinates
    confidences: np.ndarray        # (17,) — per-keypoint confidence
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]

    def keypoint(self, name: str) -> np.ndarray:
        """Get a single keypoint by name. Returns [x, y]."""
        return self.keypoints[KEYPOINT_NAMES[name]]

    def midpoint(self, name1: str, name2: str) -> np.ndarray:
        """Average of two named keypoints."""
        return (self.keypoint(name1) + self.keypoint(name2)) / 2.0

    def to_dict(self) -> dict:
        return {
            'keypoints': self.keypoints.tolist(),
            'confidences': self.confidences.tolist(),
            'bbox': self.bbox,
        }


class PoseDetector:
    """
    Detects human poses in frames using YOLOv8s-pose (or compatible).

    Uses GPU with FP16 for optimal throughput on T4.
    Returns structured PersonPose objects with COCO-17 keypoints.
    """

    def __init__(self, model_name: str = 'yolov8s-pose.pt',
                 gpu_id: int = 0, conf_threshold: float = 0.5,
                 use_half: bool = True):
        self.model = None
        self.gpu_id = gpu_id
        self.conf_threshold = conf_threshold
        self.model_name = model_name
        self.use_half = use_half
        self.device = f'cuda:{gpu_id}'

        if YOLO_AVAILABLE:
            self._init_model()

    @property
    def available(self) -> bool:
        return YOLO_AVAILABLE and self.model is not None

    def _init_model(self):
        try:
            import torch
            if not torch.cuda.is_available():
                self.device = 'cpu'
                self.use_half = False
                logger.warning("CUDA not available — pose detector will use CPU")

            self.model = YOLO(self.model_name)

            # Warm up with a dummy frame to load weights onto GPU
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model(dummy, device=self.device,
                       half=self.use_half, verbose=False)

            logger.info(
                f"PoseDetector: {self.model_name} loaded on {self.device} "
                f"(half={self.use_half})"
            )
        except Exception as e:
            logger.error(f"PoseDetector: failed to load {self.model_name}: {e}")
            self.model = None

    def detect(self, frame: np.ndarray) -> List[PersonPose]:
        """
        Detect human poses in a BGR frame.

        Returns:
            List of PersonPose with keypoints, confidences, and bounding boxes
        """
        if not self.available:
            return []

        try:
            results = self.model(
                frame,
                device=self.device,
                conf=self.conf_threshold,
                half=self.use_half,
                verbose=False,
            )

            if not results or len(results) == 0:
                return []

            result = results[0]
            persons = []

            if result.keypoints is not None and result.keypoints.data.shape[0] > 0:
                kps_data = result.keypoints.data.cpu().numpy()  # (N, 17, 3)
                boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else []

                for i in range(kps_data.shape[0]):
                    kps = kps_data[i]  # (17, 3) — x, y, conf
                    person = PersonPose(
                        keypoints=kps[:, :2],      # (17, 2)
                        confidences=kps[:, 2],     # (17,)
                        bbox=boxes[i].tolist() if i < len(boxes) else None,
                    )
                    persons.append(person)

            return persons

        except Exception as e:
            logger.error(f"Pose detection error: {e}")
            return []

    def get_stats(self) -> dict:
        return {
            'available': self.available,
            'model': self.model_name,
            'device': self.device,
            'half': self.use_half,
            'conf_threshold': self.conf_threshold,
        }
