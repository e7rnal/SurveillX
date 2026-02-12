"""
SurveillX FastRTC Streaming Server (Reference Implementation)
Runs on port 8080 alongside Flask on port 5000.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8080

Requires:
    pip install fastapi uvicorn aiortc opencv-python python-socketio[client]
"""
import asyncio
import base64
import logging
import time
import uuid

import cv2
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCConfiguration,
    RTCIceServer,
)
import socketio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streaming-server")

# ---------- Config ----------
FLASK_URL = "http://localhost:5000"
TURN_URL = "turn:13.205.156.238:3478"
TURN_USER = "surveillx"
TURN_PASS = "Vishu@9637"

# Server uses STUN only (has public IP)
# Client uses STUN + TURN (behind NAT)
SERVER_ICE = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)

# ---------- FastAPI App ----------
app = FastAPI(title="SurveillX Streaming Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- Socket.IO Client (to emit frames to Flask) ----------
sio = socketio.Client(logger=False)
sio_connected = False


def connect_to_flask():
    """Connect to Flask's Socket.IO for frame forwarding."""
    global sio_connected
    try:
        sio.connect(FLASK_URL, namespaces=["/stream"])
        sio_connected = True
        logger.info(f"Connected to Flask Socket.IO at {FLASK_URL}")
    except Exception as e:
        logger.warning(f"Failed to connect to Flask: {e}. Frames won't be forwarded to browser.")
        sio_connected = False


# ---------- State ----------
streamer_pc = None
frame_count = 0


# ---------- Frame Processing ----------
def forward_to_browser(img):
    """Send frame to Flask via Socket.IO for browser display."""
    global sio_connected
    if not sio_connected:
        return
    try:
        _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")
        sio.emit(
            "frame",
            {"frame": frame_b64, "camera_id": 1, "timestamp": str(time.time())},
            namespace="/stream",
        )
    except Exception as e:
        logger.error(f"Frame forward error: {e}")
        sio_connected = False


def process_for_attendance(img):
    """
    Run face recognition on frame and submit attendance.
    TODO: Import and call the actual SurveillX face recognition service.
    """
    # from services.face_recognition import recognize_faces
    # detections = recognize_faces(img)
    # for det in detections:
    #     submit_attendance(det.student_id)
    pass


async def consume_frames(track, pc):
    """Consume WebRTC frames — this works because FastAPI has a native asyncio loop."""
    global frame_count
    frame_count = 0

    # Wait for connection to be fully established
    for _ in range(60):
        if pc.connectionState == "connected":
            break
        if pc.connectionState in ["failed", "closed"]:
            logger.error(f"PC state: {pc.connectionState}, aborting frame consumer")
            return
        await asyncio.sleep(0.5)
    else:
        logger.error("PC never reached 'connected' state")
        return

    await asyncio.sleep(0.5)  # Let DTLS/SRTP finalize
    logger.info("Frame consumer started — awaiting frames...")

    try:
        while True:
            frame = await track.recv()
            frame_count += 1

            if frame_count == 1:
                logger.info(f"FIRST FRAME received! {frame.width}x{frame.height}")

            img = frame.to_ndarray(format="bgr24")

            # Face recognition every 5th frame
            if frame_count % 5 == 0:
                process_for_attendance(img)

            # Forward to browser every 2nd frame
            if frame_count % 2 == 0:
                forward_to_browser(img)

            if frame_count % 200 == 0:
                logger.info(f"Processed {frame_count} frames")

    except Exception as e:
        logger.info(f"Frame consumer stopped: {type(e).__name__}: {e}")
    finally:
        logger.info(f"Total frames processed: {frame_count}")


# ---------- Routes ----------
@app.on_event("startup")
async def startup():
    connect_to_flask()


@app.post("/webrtc/streamer")
async def handle_streamer(request: Request):
    """Handle WebRTC offer from Windows streaming client."""
    global streamer_pc

    params = await request.json()
    if not params or "sdp" not in params:
        return {"error": "Missing 'sdp'"}, 400

    # Close existing connection
    if streamer_pc:
        try:
            await streamer_pc.close()
        except:
            pass

    pc = RTCPeerConnection(configuration=SERVER_ICE)
    pc_id = f"streamer-{uuid.uuid4().hex[:8]}"
    streamer_pc = pc

    @pc.on("connectionstatechange")
    async def on_state():
        global streamer_pc
        logger.info(f"{pc_id}: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            if streamer_pc == pc:
                streamer_pc = None

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            logger.info(f"Received video track from {pc_id}")
            asyncio.ensure_future(consume_frames(track, pc))

    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logger.info(f"{pc_id}: SDP exchange complete")
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@app.get("/webrtc/ice-config")
async def ice_config():
    """Return ICE config for clients (includes TURN for NAT traversal)."""
    return {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": [TURN_URL, f"{TURN_URL}?transport=tcp"],
                "username": TURN_USER,
                "credential": TURN_PASS,
            },
        ]
    }


@app.get("/webrtc/stats")
async def stats():
    return {
        "streamer_connected": streamer_pc is not None,
        "frames_processed": frame_count,
        "flask_connected": sio_connected,
    }
