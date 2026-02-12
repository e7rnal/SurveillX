"""
SurveillX GStreamer Streaming Server
Uses GStreamer webrtcbin for WebRTC media + WebSocket for signaling.
Runs alongside Flask on a separate port (8443).

Usage:
    python gst_streaming_server.py

Architecture:
    Windows Client --WebRTC--> This server (GStreamer) --Socket.IO--> Flask :5000 --> Browser
"""
import asyncio
import json
import base64
import logging
import time
import sys
import threading

import cv2
import numpy as np
import websockets
import requests as req_lib

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GLib, GstWebRTC, GstSdp

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
STUN_SERVER = "stun://stun.l.google.com:19302"
TURN_URL = "turn://surveillx:Vishu%409637@13.205.156.238:3478"

# ---------- HTTP Session (for frame forwarding to Flask) ----------
http_session = req_lib.Session()
http_session.headers.update({"Content-Type": "application/json"})
flask_connected = False


def check_flask_connection():
    """Verify Flask is reachable."""
    global flask_connected
    try:
        r = http_session.get(f"{FLASK_URL}/health", timeout=3)
        flask_connected = r.status_code == 200
        if flask_connected:
            logger.info(f"Flask is reachable at {FLASK_URL}")
    except Exception as e:
        logger.warning(f"Flask not reachable: {e}")
        flask_connected = False


# ---------- Global State ----------
frame_count = 0
pipeline = None
webrtcbin = None
current_ws = None
main_loop = None
glib_loop = None


# ---------- Frame Processing ----------
def forward_to_browser(frame):
    """Encode frame as JPEG and POST to Flask for Socket.IO broadcast."""
    global flask_connected

    try:
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")
        r = http_session.post(
            FLASK_FRAME_ENDPOINT,
            json={"frame": frame_b64, "camera_id": 1, "timestamp": str(time.time())},
            timeout=2,
        )
        if r.status_code != 200 and frame_count % 100 == 0:
            logger.warning(f"Frame POST failed: {r.status_code}")
        elif not flask_connected:
            flask_connected = True
            logger.info("Frame forwarding to Flask working!")
    except Exception as e:
        if frame_count % 100 == 0:
            logger.error(f"Frame forward error: {e}")
        flask_connected = False


def process_for_attendance(frame):
    """
    Placeholder for face recognition.
    Import SurveillX face recognition service and process.
    """
    # TODO: Import and call actual face recognition
    # from services.face_recognition import recognize_faces
    # detections = recognize_faces(frame)
    # for det in detections:
    #     submit_attendance(det.student_id)
    pass


def on_new_sample(sink):
    """
    Called by GStreamer's appsink when a decoded frame is ready.
    This runs in the GLib main loop thread — keep it fast.
    """
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

    # Copy frame data to numpy array
    frame = np.ndarray(
        shape=(height, width, 3), dtype=np.uint8, buffer=map_info.data
    ).copy()
    buf.unmap(map_info)

    frame_count += 1

    if frame_count == 1:
        logger.info(f"🎉 FIRST FRAME received! {width}x{height}")

    # Face recognition every 5th frame (to save CPU)
    if frame_count % 5 == 0:
        process_for_attendance(frame)

    # Forward every frame to browser
    forward_to_browser(frame)

    if frame_count % 200 == 0:
        logger.info(f"Processed {frame_count} frames")

    return Gst.FlowReturn.OK


# ---------- GStreamer Pipeline ----------
def create_pipeline():
    """
    Create GStreamer pipeline:
    webrtcbin (receives RTP) → decode VP8 → convert to BGR → appsink (Python callback)
    """
    global pipeline, webrtcbin

    pipe_str = (
        f"webrtcbin name=recv bundle-policy=max-bundle stun-server={STUN_SERVER} "
        "recv. ! queue max-size-buffers=2 leaky=downstream "
        "! rtpvp8depay ! vp8dec "
        "! queue max-size-buffers=2 leaky=downstream "
        "! videoconvert ! video/x-raw,format=BGR "
        "! appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
    )

    pipeline = Gst.parse_launch(pipe_str)
    webrtcbin = pipeline.get_by_name("recv")
    appsink = pipeline.get_by_name("sink")

    # Connect frame callback
    appsink.connect("new-sample", on_new_sample)

    # Add TURN server for NAT traversal
    webrtcbin.emit("add-turn-server", TURN_URL)

    logger.info("GStreamer pipeline created")
    return pipeline


def on_negotiation_needed(element):
    """Called when webrtcbin needs negotiation (not used for receive-only)."""
    logger.debug("Negotiation needed signal received")


# ---------- ICE Candidate Handling ----------
def send_ice_candidate_to_client(element, mline_index, candidate):
    """Send locally generated ICE candidate to the Windows client via WebSocket."""
    if current_ws and main_loop:
        msg = json.dumps({
            "type": "ice",
            "candidate": candidate,
            "sdpMLineIndex": mline_index,
        })
        asyncio.run_coroutine_threadsafe(current_ws.send(msg), main_loop)


# ---------- Pad Handling ----------
def on_pad_added(element, pad):
    """Handle dynamic pad from webrtcbin when media starts flowing."""
    caps = pad.get_current_caps()
    if caps:
        name = caps.to_string()
        logger.info(f"Pad added: {pad.get_name()} caps={name[:80]}...")


# ---------- WebSocket Signaling Handler ----------
async def handle_client(websocket, path=None):
    """Handle WebSocket connection from Windows streaming client."""
    global current_ws, pipeline, webrtcbin, frame_count

    current_ws = websocket
    frame_count = 0
    logger.info("Windows client connected via WebSocket")

    # Create fresh pipeline for each connection
    if pipeline:
        pipeline.set_state(Gst.State.NULL)
        await asyncio.sleep(0.5)

    create_pipeline()

    # Connect signals
    webrtcbin.connect("on-ice-candidate", send_ice_candidate_to_client)
    webrtcbin.connect("on-negotiation-needed", on_negotiation_needed)
    webrtcbin.connect("pad-added", on_pad_added)

    # Start pipeline (it will wait for incoming RTP)
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        logger.error("Failed to start pipeline!")
        return
    logger.info("Pipeline PLAYING — waiting for SDP offer...")

    # Event to signal when ICE gathering is complete
    ice_gathering_complete = asyncio.Event()

    def on_ice_gathering_state(element, pspec):
        state = element.get_property("ice-gathering-state")
        logger.info(f"ICE gathering state: {state}")
        if state == GstWebRTC.WebRTCICEGatheringState.COMPLETE:
            main_loop.call_soon_threadsafe(ice_gathering_complete.set)

    webrtcbin.connect("notify::ice-gathering-state", on_ice_gathering_state)

    # Also monitor ICE connection state for debugging
    def on_ice_conn_state(element, pspec):
        state = element.get_property("ice-connection-state")
        logger.info(f"ICE connection state: {state}")

    webrtcbin.connect("notify::ice-connection-state", on_ice_conn_state)

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "offer":
                logger.info("Received SDP offer from client")

                # Parse SDP
                res, sdp = GstSdp.SDPMessage.new_from_text(data["sdp"])
                if res != GstSdp.SDPResult.OK:
                    logger.error(f"Failed to parse SDP: {res}")
                    continue

                # Set remote description (client's offer)
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

                if reply is None:
                    logger.error("create-answer returned None")
                    continue

                answer = reply.get_value("answer")
                if answer is None:
                    logger.error("No 'answer' in reply")
                    continue

                # Set local description (triggers ICE gathering)
                promise = Gst.Promise.new()
                webrtcbin.emit("set-local-description", answer, promise)
                promise.wait()

                # CRITICAL: Wait for ICE gathering to complete so candidates
                # are embedded in the SDP answer. Without this, the answer
                # has 0 candidates and aiortc can't connect.
                logger.info("Waiting for ICE gathering to complete...")
                try:
                    await asyncio.wait_for(ice_gathering_complete.wait(), timeout=10.0)
                    logger.info("ICE gathering complete!")
                except asyncio.TimeoutError:
                    logger.warning("ICE gathering timeout (10s) — sending answer with available candidates")

                # Re-read local description (now includes gathered ICE candidates)
                local_desc = webrtcbin.get_property("local-description")
                if local_desc:
                    answer_sdp = local_desc.sdp.as_text()
                else:
                    answer_sdp = answer.sdp.as_text()

                # Count candidates in the SDP
                candidate_count = answer_sdp.count("a=candidate:")
                logger.info(f"Answer SDP has {candidate_count} ICE candidates")

                await websocket.send(json.dumps({
                    "type": "answer",
                    "sdp": answer_sdp,
                }))
                logger.info("Sent SDP answer to client (with candidates)")

            elif data["type"] == "ice":
                # Add remote ICE candidate from client
                candidate = data.get("candidate", "")
                mline = data.get("sdpMLineIndex", 0)
                if candidate:
                    webrtcbin.emit("add-ice-candidate", mline, candidate)
                    logger.debug(f"Added ICE candidate: {candidate[:60]}...")

        # Keep WebSocket alive for media streaming
        logger.info("Signaling done. Keeping connection alive for media...")
        try:
            await websocket.wait_closed()
        except Exception:
            pass

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Client disconnected: {e}")
    except Exception as e:
        logger.error(f"Error in client handler: {e}", exc_info=True)
    finally:
        logger.info(f"Session ended. Total frames: {frame_count}")
        if pipeline:
            pipeline.set_state(Gst.State.NULL)
        current_ws = None


# ---------- GLib Main Loop (for GStreamer events) ----------
def run_glib_loop():
    """Run GLib main loop in a background thread (required for GStreamer signals)."""
    global glib_loop
    glib_loop = GLib.MainLoop()
    logger.info("GLib main loop started")
    glib_loop.run()


# ---------- Stats Endpoint (optional HTTP) ----------
async def stats_handler(websocket, path=None):
    """Simple stats endpoint (connect via ws://server:8444)."""
    stats = json.dumps({
        "streamer_connected": current_ws is not None,
        "frames_processed": frame_count,
        "flask_connected": flask_connected,
        "pipeline_state": str(pipeline.get_state(0)[1]) if pipeline else "NULL",
    })
    await websocket.send(stats)


# ---------- Main ----------
async def main():
    global main_loop

    # Initialize GStreamer
    logger.info("Initializing GStreamer...")
    Gst.init(sys.argv)
    logger.info("GStreamer initialized")

    # Start GLib main loop in background thread
    glib_thread = threading.Thread(target=run_glib_loop, daemon=True)
    glib_thread.start()

    # Verify Flask is reachable for frame forwarding
    check_flask_connection()

    # Save reference to asyncio loop (for ICE candidate forwarding)
    main_loop = asyncio.get_event_loop()

    # Start WebSocket signaling server
    logger.info(f"WebSocket signaling server starting on ws://0.0.0.0:{SIGNALING_PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", SIGNALING_PORT):
        logger.info(f"✅ GStreamer streaming server ready on port {SIGNALING_PORT}")
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        if glib_loop:
            glib_loop.quit()
        if pipeline:
            pipeline.set_state(Gst.State.NULL)
