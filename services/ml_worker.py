"""
SurveillX ML Processing Worker
Background process that taps into the WebSocket stream,
runs face recognition + activity detection on every Nth frame,
and pushes results back to Flask via HTTP.

Pipeline:
    Stage 1: YOLOv8n — person detection (bboxes)
    Stage 2: InsightFace buffalo_l — face detect + ArcFace embed (on person crops)
    Stage 3: YOLOv8s-pose — pose estimation (FP16 on GPU)
    Stage 4: Temporal classifier — multi-frame voting with cooldowns

Usage:
    python -m services.ml_worker
    # or
    python services/ml_worker.py

This runs independently of gst_streaming_server.py and app.py.
"""

import sys
import os

# Ensure parent directory is in path for imports
if __name__ == '__main__':
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

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
PROCESS_EVERY_N = 3                         # Process every Nth frame (was 5)
GPU_ID = 0
PERSON_DETECT_MODEL = 'yolov8n.pt'          # Stage 1: lightweight person detector
POSE_MODEL = 'yolov8s-pose.pt'             # Stage 3: pose estimation
PERSON_CONF = 0.4                           # Person detection confidence
USE_FP16 = True                             # FP16 inference on T4


class MLWorker:
    """Background ML processing worker with multi-stage pipeline."""

    def __init__(self):
        self.face_service = None
        self.activity_detector = None
        self.person_detector = None          # Stage 1: YOLOv8n
        self.frame_count = 0
        self.processed_count = 0
        self.last_detection_time = 0
        self.running = False

    def init_models(self):
        """Load ML models (GPU with FP16)."""
        import torch
        device = f'cuda:{GPU_ID}' if torch.cuda.is_available() else 'cpu'
        logger.info(f"🖥️ Device: {device}")

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(GPU_ID)
            vram_total = torch.cuda.get_device_properties(GPU_ID).total_memory / 1024**3
            logger.info(f"🖥️ GPU: {gpu_name} ({vram_total:.1f} GB VRAM)")

        # ── Stage 1: Person Detector (YOLOv8n) ──
        try:
            from ultralytics import YOLO
            self.person_detector = YOLO(PERSON_DETECT_MODEL)
            # Warm up
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self.person_detector(dummy, device=device, half=USE_FP16,
                                 classes=[0], verbose=False)  # class 0 = person
            logger.info(f"✅ Stage 1: Person detector ({PERSON_DETECT_MODEL}) on {device}")
        except Exception as e:
            logger.error(f"❌ Person detector init failed: {e}")

        # ── Stage 2: Face Recognition (InsightFace buffalo_l / ArcFace) ──
        try:
            from services.face_service import FaceService
            self.face_service = FaceService(db_manager=None, threshold=0.4, gpu_id=GPU_ID)
            self._load_known_faces()
            stats = self.face_service.get_stats()
            logger.info(f"✅ Stage 2: Face service ({stats})")
        except Exception as e:
            logger.error(f"❌ Face service init failed: {e}")

        # ── Stage 3+4: Activity Detection (YOLOv8s-pose + Temporal Classifier) ──
        try:
            from services.activity_detector import ActivityDetector
            self.activity_detector = ActivityDetector(
                model_name=POSE_MODEL,
                gpu_id=GPU_ID,
            )
            stats = self.activity_detector.get_stats()
            logger.info(f"✅ Stage 3+4: Activity detector ({stats})")
        except Exception as e:
            logger.error(f"❌ Activity detector init failed: {e}")

        # Log VRAM usage after loading
        if torch.cuda.is_available():
            vram_used = torch.cuda.memory_allocated(GPU_ID) / 1024**3
            vram_reserved = torch.cuda.memory_reserved(GPU_ID) / 1024**3
            logger.info(
                f"📊 VRAM after model loading: "
                f"allocated={vram_used:.2f}GB, reserved={vram_reserved:.2f}GB"
            )

    def _load_known_faces(self):
        """Load known face embeddings from Flask internal API (no auth required)."""
        try:
            resp = requests.get(f"{FLASK_API_URL}/api/internal/known-faces", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                faces = data.get('faces', [])
                loaded = 0
                for face in faces:
                    encoding = face.get('face_encoding')
                    if encoding:
                        try:
                            if isinstance(encoding, str):
                                encoding = json.loads(encoding)
                            self.face_service.add_known_face(
                                face['id'], face['name'], encoding
                            )
                            loaded += 1
                            logger.info(f"✅ Loaded face for: {face['name']} (ID: {face['id']})")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to load face for {face.get('name')}: {e}")
                logger.info(f"🧠 Loaded {loaded} known faces from API")
            else:
                logger.warning(f"⚠️ Known faces API returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"❌ Could not load known faces: {e}")

    def _reload_known_faces_periodically(self):
        """Reload known faces every 60 seconds to pick up new enrollments."""
        def reload():
            while self.running:
                time.sleep(60)
                logger.info("🔄 Reloading known faces...")
                self._load_known_faces()
        t = threading.Thread(target=reload, daemon=True)
        t.start()

    def process_frame(self, frame_bgr, camera_id=1):
        """
        Run multi-stage ML pipeline on a single frame.

        Stage 1: YOLOv8n person detection → person bboxes
        Stage 2: InsightFace face recognition (on full frame — InsightFace handles crops)
        Stage 3+4: YOLOv8s-pose + temporal activity classifier
        """
        results = {
            'faces': [],
            'activity': {'type': 'normal', 'is_abnormal': False, 'severity': 'low',
                         'confidence': 0, 'description': '', 'persons': []},
            'person_count': 0,
            'timestamp': time.time(),
        }

        # ── Stage 1: Person Detection ──
        person_bboxes = []
        if self.person_detector:
            try:
                import torch
                device = f'cuda:{GPU_ID}' if torch.cuda.is_available() else 'cpu'
                det_results = self.person_detector(
                    frame_bgr,
                    device=device,
                    half=USE_FP16,
                    classes=[0],  # person only
                    conf=PERSON_CONF,
                    verbose=False,
                )
                if det_results and len(det_results) > 0:
                    boxes = det_results[0].boxes
                    if boxes is not None and len(boxes) > 0:
                        person_bboxes = boxes.xyxy.cpu().numpy().tolist()
                        results['person_count'] = len(person_bboxes)
            except Exception as e:
                logger.error(f"Person detection error: {e}")

        # ── Stage 2: Face Recognition ──
        # InsightFace runs on full frame (it has its own face detector + crops internally)
        if self.face_service:
            try:
                faces = self.face_service.detect_and_recognize(frame_bgr)
                results['faces'] = faces
            except Exception as e:
                logger.error(f"Face recognition error: {e}")

        # ── Stage 3+4: Activity Detection (pose + temporal classifier) ──
        if self.activity_detector:
            try:
                activity = self.activity_detector.detect(frame_bgr)
                results['activity'] = activity
            except Exception as e:
                logger.error(f"Activity detection error: {e}")

        return results

    def _push_detections(self, detections):
        """Push detection results to Flask for SocketIO broadcast."""
        try:
            faces_count = len(detections.get('faces', []))
            activity_type = detections.get('activity', {}).get('type', 'unknown')
            person_count = detections.get('person_count', 0)

            logger.info(
                f"📊 Pushing detection: {faces_count} faces, "
                f"{person_count} persons, activity: {activity_type}"
            )

            response = requests.post(
                f"{FLASK_API_URL}/api/stream/detections",
                json=detections,
                timeout=2
            )

            if response.status_code == 200:
                logger.info(f"✅ Detection pushed successfully to Flask")
            else:
                logger.warning(f"⚠️ Flask returned status {response.status_code}: {response.text}")

        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error pushing detections: {e}")
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout pushing detections to Flask")
        except Exception as e:
            logger.error(f"❌ Detection push error: {e}", exc_info=True)


    async def run(self):
        """Main loop: connect to WS hub as viewer, process frames."""
        self.running = True
        logger.info(f"ML Worker starting — connecting to {WS_HUB_URL}")

        # Start periodic face reload in background
        self._reload_known_faces_periodically()

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

                            # Save snapshot when activity is abnormal
                            if detections['activity'].get('is_abnormal'):
                                try:
                                    snap_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'snapshots')
                                    os.makedirs(snap_dir, exist_ok=True)
                                    snap_name = f"alert_{int(time.time())}_{camera_id}.jpg"
                                    snap_path = os.path.join(snap_dir, snap_name)
                                    cv2.imwrite(snap_path, frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                                    detections['snapshot_path'] = f"/uploads/snapshots/{snap_name}"
                                    logger.info(f"📸 Saved alert snapshot: {snap_name}")
                                except Exception as snap_err:
                                    logger.warning(f"Failed to save snapshot: {snap_err}")

                            # Push detections to browser via Flask SocketIO
                            if detections['faces'] or detections['activity'].get('is_abnormal'):
                                self._push_detections(detections)

                            if self.processed_count % 20 == 0:
                                logger.info(
                                    f"Processed {self.processed_count} frames "
                                    f"(total received: {self.frame_count}, "
                                    f"last: {elapsed:.0f}ms, "
                                    f"persons: {detections.get('person_count', 0)}, "
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

    logger.info("="*60)
    logger.info("SurveillX ML Worker — Multi-Stage Pipeline")
    logger.info(f"  Stage 1: Person Detector   → {worker.person_detector is not None}")
    logger.info(f"  Stage 2: Face Service      → {worker.face_service is not None}")
    logger.info(f"  Stage 3+4: Activity Detect → {worker.activity_detector is not None}")
    logger.info(f"  Process every {PROCESS_EVERY_N}th frame")
    logger.info(f"  GPU: {GPU_ID} (FP16: {USE_FP16})")
    logger.info("="*60)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        logger.info("ML Worker stopped.")


if __name__ == "__main__":
    main()
