"""
SurveillX Streaming Server — Low-Latency WebSocket Hub
Receives JPEG frames from Windows client, broadcasts to browser viewers.
No Flask/HTTP/Socket.IO in the frame path — minimal latency.

Usage:
    python gst_streaming_server.py

Architecture:
    Windows Client --WS frame--> This server --WS broadcast--> Browser(s)
    (Flask is only used for dashboard HTML, REST API, auth — not video)
"""
import asyncio
import json
import base64
import logging
import time
import sys
import cv2
import numpy as np
import os

import websockets

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.recognition_handler import RecognitionHandler

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/gst_streaming.log"),
    ],
)
logger = logging.getLogger("gst-streaming")

# ---------- Config ----------
SIGNALING_PORT = 8443

# ---------- Connection Registry ----------
viewers = set()       # Browser WebSocket connections
streamer = None       # The camera client connection
frame_count = 0
last_frame_data = None  # Cache last frame for new viewer connections

# Recognition handler (initialized in main)
recognition_handler = None


async def broadcast_to_viewers(message):
    """Send a message to all connected browser viewers — parallel for lowest latency."""
    if not viewers:
        return
    async def _safe_send(ws):
        try:
            await ws.send(message)
        except Exception:
            return ws
        return None
    results = await asyncio.gather(*[_safe_send(ws) for ws in viewers.copy()])
    dead = {ws for ws in results if ws is not None}
    viewers.difference_update(dead)


async def handle_connection(websocket, path=None):
    """Handle any incoming WebSocket connection (client or viewer)."""
    global streamer, frame_count, last_frame_data

    # Wait for the first message to determine connection type
    try:
        first_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
        data = json.loads(first_msg)
    except Exception as e:
        logger.warning(f"Connection failed handshake: {e}")
        return

    msg_type = data.get("type", "")

    if msg_type == "hello" and data.get("mode") == "jpeg":
        # ===== CAMERA CLIENT (streamer) =====
        streamer = websocket
        frame_count = 0
        w = data.get("width", 0)
        h = data.get("height", 0)
        fps = data.get("fps", 0)
        logger.info(f"📷 Camera client connected: {w}x{h} @ {fps}fps")
        await websocket.send(json.dumps({"type": "ready", "status": "ok"}))

        try:
            async for message in websocket:
                msg = json.loads(message)
                if msg.get("type") != "frame":
                    continue

                frame_b64 = msg.get("frame", "")
                if not frame_b64:
                    continue

                frame_count += 1

                if frame_count == 1:
                    raw = base64.b64decode(frame_b64)
                    logger.info(f"🎉 FIRST FRAME! size={len(raw)} bytes, viewers={len(viewers)}")

                # Run face recognition on frame
                recognition_data = None
                if recognition_handler:
                    try:
                        # Decode JPEG to numpy array
                        jpg_bytes = base64.b64decode(frame_b64)
                        jpg_arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
                        frame_bgr = cv2.imdecode(jpg_arr, cv2.IMREAD_COLOR)
                        
                        if frame_bgr is not None:
                            recognition_data = recognition_handler.process_frame(frame_bgr)
                    except Exception as e:
                        logger.error(f"Recognition error: {e}")

                # Prepare broadcast message with server timestamp for latency
                broadcast_msg = json.dumps({
                    "type": "frame",
                    "frame": frame_b64,
                    "camera_id": msg.get("camera_id", 1),
                    "timestamp": msg.get("timestamp", ""),
                    "server_time": time.time() * 1000,
                    "width": msg.get("width", 0),
                    "height": msg.get("height", 0),
                    "recognition": recognition_data,  # Include recognition results
                })

                # Cache for new viewers joining mid-stream
                last_frame_data = broadcast_msg

                # Broadcast to all viewers
                await broadcast_to_viewers(broadcast_msg)

                if frame_count % 200 == 0:
                    logger.info(f"Processed {frame_count} frames, viewers={len(viewers)}")

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Camera client disconnected: {e}")
        finally:
            streamer = None
            frame_count = 0
            # Notify viewers that stream ended
            try:
                await broadcast_to_viewers(json.dumps({"type": "stream_ended"}))
            except Exception:
                pass
            logger.info("Camera client session ended")

    elif msg_type == "viewer":
        # ===== BROWSER VIEWER =====
        viewers.add(websocket)
        logger.info(f"👁 Viewer connected (total: {len(viewers)})")

        # Send current status
        await websocket.send(json.dumps({
            "type": "status",
            "streaming": streamer is not None,
            "frames_processed": frame_count,
        }))

        # Send last frame if available (so viewer doesn't see blank)
        if last_frame_data:
            try:
                await websocket.send(last_frame_data)
            except Exception:
                pass

        try:
            # Keep connection alive, listen for pings/commands
            async for message in websocket:
                # Viewers might send commands in the future
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            viewers.discard(websocket)
            logger.info(f"👁 Viewer disconnected (total: {len(viewers)})")

    else:
        logger.warning(f"Unknown connection type: {msg_type}")
        await websocket.close(1008, "Unknown connection type. Send {type: 'hello', mode: 'jpeg'} or {type: 'viewer'}")


# ---------- Main ----------
async def reload_students_periodically():
    """Background task to reload students every 10 seconds for instant recognition of newly approved enrollments"""
    await asyncio.sleep(10)  # Wait 10s before first check
    
    while True:
        try:
            if recognition_handler:
                new_count = recognition_handler.reload_students()
                if new_count > 0:
                    logger.info(f"🔄 Reloaded {new_count} new student(s) for recognition")
        except Exception as e:
            logger.error(f"Error in reload task: {e}")
        
        await asyncio.sleep(10)  # Check every 10 seconds


async def main():
    global recognition_handler
    
    # Initialize face recognition
    try:
        from services.face_recognition_service import FaceRecognitionService
        from services.db_manager import DBManager
        from config import Config
        
        config = Config()
        db = DBManager(config)
        face_service = FaceRecognitionService(config)
        
        # Load enrolled students into face service
        students = db.get_all_students()
        for student in students:
            if student.get('face_encoding'):
                face_service.add_known_face(
                    student['id'],
                    student['name'],
                    student['face_encoding']
                )
        
        recognition_handler = RecognitionHandler(face_service, db)
        
        # Initialize loaded student IDs
        recognition_handler.loaded_student_ids = {s['id'] for s in students if s.get('face_encoding')}
        
        logger.info(f"✅ Face recognition initialized with {len(students)} students")
        
        # Start background reload task
        asyncio.create_task(reload_students_periodically())
        
    except Exception as e:
        logger.error(f"Failed to initialize face recognition: {e}")
        recognition_handler = None
    
    logger.info(f"WebSocket hub starting on ws://0.0.0.0:{SIGNALING_PORT}")
    async with websockets.serve(
        handle_connection,
        "0.0.0.0",
        SIGNALING_PORT,
        max_size=2 * 1024 * 1024,  # 2MB max message (for large JPEG frames)
        ping_interval=20,
        ping_timeout=10,
    ):
        logger.info(f"✅ Streaming hub ready on port {SIGNALING_PORT}")
        logger.info(f"   Camera clients: ws://server:{SIGNALING_PORT}")
        logger.info(f"   Browser viewers: ws://server:{SIGNALING_PORT}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
