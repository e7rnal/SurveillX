"""
SurveillX ML Processing Worker
Background process that taps into the WebSocket stream,
runs InsightFace + YOLO11 on every Nth frame, and pushes
results (attendance, alerts, detections) back to Flask via HTTP.

Usage:
    python -m services.ml_worker
    # or
    python services/ml_worker.py

This runs independently of gst_streaming_server.py and app.py.
"""

import asyncio
import base64
import json
import logging
import time
import threading

import cv2
import numpy as np
import websockets
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/ml_worker.log"),
    ],
)
logger = logging.getLogger("ml-worker")

# ---------- Config ----------
WS_HUB_URL = "ws://localhost:8443"          # Main WebSocket hub
FLASK_API_URL = "http://localhost:5000"      # Flask API
PROCESS_EVERY_N = 5                         # Process every Nth frame (skip 4 out of 5)
GPU_ID = 0


class MLWorker:
    """Background ML processing worker."""

    def __init__(self):
        self.face_service = None
        self.activity_detector = None
        self.frame_count = 0
        self.processed_count = 0
        self.last_detection_time = 0
        self.running = False

    def init_models(self):
        """Load ML models (GPU)."""
        logger.info("Loading ML models...")

        # Face recognition
        try:
            from services.face_service import FaceService
            # Create a simple DB proxy that calls the Flask API
            self.face_service = FaceService(db_manager=None, threshold=0.4, gpu_id=GPU_ID)

            # Load known faces from Flask API
            self._load_known_faces()
            logger.info(f"Face service ready: {self.face_service.get_stats()}")
        except Exception as e:
            logger.error(f"Face service init failed: {e}")

        # Activity detection
        try:
            from services.activity_detector import ActivityDetector
            self.activity_detector = ActivityDetector(
                model_name='yolo11n-pose.pt',
                gpu_id=GPU_ID
            )
            logger.info(f"Activity detector ready: {self.activity_detector.get_stats()}")
        except Exception as e:
            logger.error(f"Activity detector init failed: {e}")

    def _load_known_faces(self):
        """Load known face embeddings from Flask API."""
        try:
            resp = requests.get(f"{FLASK_API_URL}/api/students", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                students = data.get('students', data) if isinstance(data, dict) else data
                loaded = 0
                for student in students:
                    encoding = student.get('face_encoding')
                    if encoding:
                        try:
                            if isinstance(encoding, str):
                                encoding = json.loads(encoding)
                            self.face_service.add_known_face(
                                student['id'], student['name'], encoding
                            )
                            loaded += 1
                        except Exception:
                            pass
                logger.info(f"Loaded {loaded} known faces from API")
        except Exception as e:
            logger.warning(f"Could not load known faces: {e}")

    def process_frame(self, frame_bgr, camera_id=1):
        """Run ML pipeline on a single frame."""
        results = {
            'faces': [],
            'activity': {'type': 'normal', 'is_abnormal': False, 'severity': 'low',
                         'confidence': 0, 'description': '', 'persons': []},
            'timestamp': time.time(),
        }

        # --- Face Recognition ---
        if self.face_service:
            try:
                faces = self.face_service.detect_and_recognize(frame_bgr)
                results['faces'] = faces

                # Auto-mark attendance for recognized faces
                for face in faces:
                    if face.get('student_id'):
                        self._mark_attendance(face['student_id'])
            except Exception as e:
                logger.error(f"Face recognition error: {e}")

        # --- Activity Detection ---
        if self.activity_detector:
            try:
                activity = self.activity_detector.detect(frame_bgr)
                results['activity'] = activity

                # Create alert for abnormal activity
                if activity.get('is_abnormal'):
                    self._create_alert(activity, camera_id)
            except Exception as e:
                logger.error(f"Activity detection error: {e}")

        return results

    def _mark_attendance(self, student_id):
        """Mark attendance via Flask API."""
        try:
            requests.post(
                f"{FLASK_API_URL}/api/attendance",
                json={"student_id": student_id},
                timeout=2
            )
        except Exception as e:
            logger.debug(f"Attendance API error: {e}")

    def _create_alert(self, activity, camera_id):
        """Create alert via Flask API."""
        try:
            requests.post(
                f"{FLASK_API_URL}/api/alerts",
                json={
                    "event_type": activity['type'],
                    "camera_id": camera_id,
                    "severity": activity['severity'],
                    "metadata": {
                        "description": activity['description'],
                        "confidence": activity['confidence'],
                    }
                },
                timeout=2
            )
        except Exception as e:
            logger.debug(f"Alert API error: {e}")

    def _push_detections(self, detections):
        """Push detection results to Flask for SocketIO broadcast."""
        try:
            requests.post(
                f"{FLASK_API_URL}/api/stream/detections",
                json=detections,
                timeout=2
            )
        except Exception as e:
            logger.debug(f"Detection push error: {e}")

    async def run(self):
        """Main loop: connect to WS hub as viewer, process frames."""
        self.running = True
        logger.info(f"ML Worker starting — connecting to {WS_HUB_URL}")

        while self.running:
            try:
                async with websockets.connect(
                    WS_HUB_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=2 * 1024 * 1024,
                ) as ws:
                    # Register as viewer
                    await ws.send(json.dumps({"type": "viewer"}))
                    logger.info("Connected to WebSocket hub as ML viewer")

                    async for message in ws:
                        try:
                            data = json.loads(message)

                            if data.get('type') == 'status':
                                logger.info(f"Hub status: streaming={data.get('streaming')}")
                                continue

                            if data.get('type') != 'frame':
                                continue

                            self.frame_count += 1

                            # Skip frames for performance
                            if self.frame_count % PROCESS_EVERY_N != 0:
                                continue

                            # Decode frame
                            frame_b64 = data.get('frame', '')
                            if not frame_b64:
                                continue

                            frame_bytes = base64.b64decode(frame_b64)
                            nparr = np.frombuffer(frame_bytes, np.uint8)
                            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                            if frame_bgr is None:
                                continue

                            # Process
                            t0 = time.time()
                            camera_id = data.get('camera_id', 1)
                            detections = self.process_frame(frame_bgr, camera_id)
                            elapsed = (time.time() - t0) * 1000  # ms

                            self.processed_count += 1

                            # Push detections to browser via Flask SocketIO
                            if detections['faces'] or detections['activity'].get('is_abnormal'):
                                self._push_detections(detections)

                            if self.processed_count % 20 == 0:
                                logger.info(
                                    f"Processed {self.processed_count} frames "
                                    f"(total received: {self.frame_count}, "
                                    f"last: {elapsed:.0f}ms, "
                                    f"faces: {len(detections['faces'])}, "
                                    f"activity: {detections['activity']['type']})"
                                )

                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"Frame processing error: {e}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Hub connection closed, reconnecting in 3s...")
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Connection error: {e}, retrying in 3s...")
                await asyncio.sleep(3)


def main():
    worker = MLWorker()
    worker.init_models()

    logger.info("="*50)
    logger.info("SurveillX ML Worker")
    logger.info(f"  Face Service: {worker.face_service is not None}")
    logger.info(f"  Activity Detector: {worker.activity_detector is not None}")
    logger.info(f"  Processing every {PROCESS_EVERY_N}th frame")
    logger.info(f"  GPU: {GPU_ID}")
    logger.info("="*50)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("ML Worker stopped.")


if __name__ == "__main__":
    main()
