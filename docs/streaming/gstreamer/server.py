"""
SurveillX GStreamer Streaming Server (Reference Implementation)
Uses GStreamer webrtcbin for WebRTC media + WebSocket for signaling.

Usage:
    python server.py

Requires (system):
    sudo apt install gstreamer1.0-plugins-bad python3-gi gir1.2-gst-plugins-bad-1.0

Requires (pip):
    pip install websockets python-socketio[client] opencv-python

Ports:
    8443 — WebSocket signaling
    5000 — Flask (must be running for frame forwarding)
"""
import asyncio
import json
import base64
import logging
import time

import cv2
import numpy as np
import websockets
import socketio

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GstWebRTC, GstSdp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gst-streaming")

# ---------- Config ----------
SIGNALING_PORT = 8443
FLASK_URL = "http://localhost:5000"
STUN_SERVER = "stun://stun.l.google.com:19302"
TURN_URL = "turn://surveillx:Vishu%409637@13.205.156.238:3478"

# ---------- Socket.IO Client (frame forwarding to Flask) ----------
sio = socketio.Client(logger=False)
sio_connected = False

def connect_to_flask():
    global sio_connected
    try:
        sio.connect(FLASK_URL, namespaces=["/stream"])
        sio_connected = True
        logger.info(f"Connected to Flask at {FLASK_URL}")
    except Exception as e:
        logger.warning(f"Flask connection failed: {e}")
        sio_connected = False


# ---------- State ----------
frame_count = 0
pipeline = None
webrtcbin = None
current_ws = None
loop = None


# ---------- Frame Processing ----------
def forward_to_browser(frame):
    global sio_connected
    if not sio_connected:
        return
    try:
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")
        sio.emit("frame", {
            "frame": frame_b64,
            "camera_id": 1,
            "timestamp": str(time.time()),
        }, namespace="/stream")
    except Exception as e:
        logger.error(f"Frame forward error: {e}")
        sio_connected = False


def process_for_attendance(frame):
    """
    Hook for face recognition.
    TODO: Import SurveillX face recognition service.
    """
    # from services.face_recognition import recognize_faces
    # detections = recognize_faces(frame)
    # for det in detections:
    #     submit_attendance(det.student_id)
    pass


def on_new_sample(sink):
    """Called by GStreamer when a new frame is available from webrtcbin."""
    global frame_count
    sample = sink.emit("pull-sample")
    if not sample:
        return Gst.FlowReturn.OK

    buf = sample.get_buffer()
    caps = sample.get_caps()
    struct = caps.get_structure(0)
    width = struct.get_value("width")
    height = struct.get_value("height")

    success, map_info = buf.map(Gst.MapFlags.READ)
    if not success:
        return Gst.FlowReturn.OK

    frame = np.ndarray(
        shape=(height, width, 3),
        dtype=np.uint8,
        buffer=map_info.data
    ).copy()  # Copy so we can unmap immediately
    buf.unmap(map_info)

    frame_count += 1

    if frame_count == 1:
        logger.info(f"FIRST FRAME! {width}x{height}")

    # Face recognition every 5th frame
    if frame_count % 5 == 0:
        process_for_attendance(frame)

    # Forward to browser every 2nd frame
    if frame_count % 2 == 0:
        forward_to_browser(frame)

    if frame_count % 200 == 0:
        logger.info(f"Processed {frame_count} frames")

    return Gst.FlowReturn.OK


# ---------- GStreamer Pipeline ----------
def create_pipeline():
    """Create the GStreamer pipeline with webrtcbin and appsink."""
    global pipeline, webrtcbin

    pipe_str = f"""
        webrtcbin name=recv bundle-policy=max-bundle stun-server={STUN_SERVER}
        recv. ! queue max-size-buffers=2 leaky=downstream
             ! rtpvp8depay ! vp8dec
             ! queue max-size-buffers=2 leaky=downstream
             ! videoconvert ! video/x-raw,format=BGR
             ! appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true
    """

    pipeline = Gst.parse_launch(pipe_str)
    webrtcbin = pipeline.get_by_name("recv")
    appsink = pipeline.get_by_name("sink")

    # Connect frame callback
    appsink.connect("new-sample", on_new_sample)

    # Set TURN server
    webrtcbin.emit("add-turn-server", TURN_URL)

    logger.info("GStreamer pipeline created")
    return pipeline


# ---------- ICE Candidate Handling ----------
def on_ice_candidate(element, mline_index, candidate):
    """Send ICE candidate to Windows client via WebSocket."""
    if current_ws:
        msg = json.dumps({
            "type": "ice",
            "candidate": candidate,
            "sdpMLineIndex": mline_index,
        })
        asyncio.run_coroutine_threadsafe(current_ws.send(msg), loop)


# ---------- WebSocket Signaling ----------
async def handle_client(websocket, path=None):
    """Handle WebSocket connection from Windows streaming client."""
    global current_ws, pipeline, webrtcbin
    current_ws = websocket
    logger.info("Client connected via WebSocket")

    # Create fresh pipeline
    if pipeline:
        pipeline.set_state(Gst.State.NULL)
    create_pipeline()

    # ICE candidate callback
    webrtcbin.connect("on-ice-candidate", on_ice_candidate)

    # Pad-added callback (for dynamic pads)
    def on_pad_added(element, pad):
        if pad.get_current_caps() and "video" in pad.get_current_caps().to_string():
            logger.info(f"Video pad added: {pad.get_name()}")

    webrtcbin.connect("pad-added", on_pad_added)

    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "offer":
                logger.info("Received SDP offer")

                # Set remote description
                res, sdp = GstSdp.SDPMessage.new_from_text(data["sdp"])
                if res != GstSdp.SDPResult.OK:
                    logger.error("Failed to parse SDP")
                    continue

                offer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.OFFER, sdp
                )
                promise = Gst.Promise.new()
                webrtcbin.emit("set-remote-description", offer, promise)
                promise.wait()

                # Create answer
                promise = Gst.Promise.new()
                webrtcbin.emit("create-answer", None, promise)
                promise.wait()
                reply = promise.get_reply()
                answer = reply.get_value("answer")

                # Set local description
                promise = Gst.Promise.new()
                webrtcbin.emit("set-local-description", answer, promise)
                promise.wait()

                # Send answer to client
                await websocket.send(json.dumps({
                    "type": "answer",
                    "sdp": answer.sdp.as_text()
                }))
                logger.info("Sent SDP answer")

            elif data["type"] == "ice":
                webrtcbin.emit(
                    "add-ice-candidate",
                    data["sdpMLineIndex"],
                    data["candidate"]
                )

    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    finally:
        if pipeline:
            pipeline.set_state(Gst.State.NULL)
        current_ws = None


async def main():
    global loop
    loop = asyncio.get_event_loop()

    Gst.init(None)
    connect_to_flask()

    logger.info(f"WebSocket signaling server on ws://0.0.0.0:{SIGNALING_PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", SIGNALING_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped.")
