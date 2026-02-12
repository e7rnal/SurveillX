"""
SurveillX Streaming Server
Receives JPEG frames from Windows client via WebSocket.
Forwards them to Flask via HTTP POST for browser display.

Usage:
    python gst_streaming_server.py

Architecture:
    Windows Client --WebSocket (JPEG)--> This server --> Flask :5000 --> Browser
"""
import asyncio
import json
import base64
import logging
import time
import sys

import requests as req_lib
import websockets

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
FLASK_URL = "http://localhost:5000"
FLASK_FRAME_ENDPOINT = f"{FLASK_URL}/api/stream/frame"

# ---------- HTTP Session (for frame forwarding to Flask) ----------
http_session = req_lib.Session()
http_session.headers.update({"Content-Type": "application/json"})

# ---------- Global State ----------
frame_count = 0
current_ws = None


def forward_to_flask(frame_b64, camera_id=1, client_timestamp=""):
    """POST a base64-encoded JPEG frame to Flask for Socket.IO broadcast."""
    try:
        r = http_session.post(
            FLASK_FRAME_ENDPOINT,
            json={"frame": frame_b64, "camera_id": camera_id, "timestamp": client_timestamp},
            timeout=2,
        )
        if r.status_code != 200 and frame_count % 100 == 0:
            logger.warning(f"Frame POST failed: {r.status_code}")
    except Exception as e:
        if frame_count % 100 == 0:
            logger.error(f"Frame forward error: {e}")


# ---------- WebSocket Handler ----------
async def handle_client(websocket, path=None):
    """Handle WebSocket connection from Windows streaming client."""
    global current_ws, frame_count

    current_ws = websocket
    frame_count = 0
    logger.info("Client connected via WebSocket")

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "hello":
                # Client handshake
                mode = data.get("mode", "unknown")
                w = data.get("width", 0)
                h = data.get("height", 0)
                fps = data.get("fps", 0)
                logger.info(f"Client hello: mode={mode}, {w}x{h} @ {fps}fps")
                await websocket.send(json.dumps({"type": "ready", "status": "ok"}))

            elif msg_type == "frame":
                # Receive JPEG frame from client
                frame_b64 = data.get("frame", "")
                camera_id = data.get("camera_id", 1)
                client_ts = data.get("timestamp", "")

                if not frame_b64:
                    continue

                frame_count += 1

                if frame_count == 1:
                    raw = base64.b64decode(frame_b64)
                    logger.info(f"🎉 FIRST FRAME! size={len(raw)} bytes")

                # Forward to Flask for browser display
                forward_to_flask(frame_b64, camera_id, client_ts)

                if frame_count % 200 == 0:
                    logger.info(f"Processed {frame_count} frames")

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Client disconnected: {e}")
    except Exception as e:
        logger.error(f"Error in client handler: {e}", exc_info=True)
    finally:
        logger.info(f"Session ended. Total frames: {frame_count}")
        current_ws = None


# ---------- Main ----------
async def main():
    # Check Flask is reachable
    try:
        r = http_session.get(f"{FLASK_URL}/health", timeout=3)
        if r.status_code == 200:
            logger.info(f"Flask is reachable at {FLASK_URL}")
        else:
            logger.warning(f"Flask returned {r.status_code}")
    except Exception as e:
        logger.warning(f"Flask not reachable: {e} (will retry on first frame)")

    # Start WebSocket server
    logger.info(f"WebSocket server starting on ws://0.0.0.0:{SIGNALING_PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", SIGNALING_PORT):
        logger.info(f"✅ Streaming server ready on port {SIGNALING_PORT}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
