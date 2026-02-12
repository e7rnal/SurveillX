"""
WebRTC API Blueprint
Handles WebRTC signaling for streaming from Windows client.
Server uses STUN only (has public IP), client uses STUN+TURN via coturn.
Bridges WebRTC video frames to Socket.IO /stream namespace for browser.
"""
import asyncio
import base64
import json
import logging
import threading
import time
import uuid

import cv2
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

webrtc_bp = Blueprint('webrtc', __name__)

# Check if aiortc is available
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaRelay
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    logger.warning("aiortc not installed - WebRTC disabled")

# ---------- ICE Configuration ----------
# SERVER uses STUN only - it has a public IP, does NOT need TURN.
# This prevents the same-machine relay loop that caused 0 frames.
SERVER_ICE_CONFIG = RTCConfiguration(
    iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
    ]
) if AIORTC_AVAILABLE else None

# TURN credentials (for reference - used by Windows client only)
# URLs: turn:13.205.156.238:3478
# Username: surveillx
# Credential: Vishu@9637

# ---------- Persistent Event Loop ----------
_loop = None
_loop_thread = None


def get_event_loop():
    """Get or create a persistent asyncio event loop in a daemon thread."""
    global _loop, _loop_thread
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        _loop_thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _loop_thread.start()
        logger.info("Background asyncio event loop started")
    return _loop


def run_async(coro):
    """Run an async coroutine from sync Flask context."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


# ---------- State ----------
streamer_pc = None           # The Windows client's peer connection
peer_connections = {}        # Browser viewer peer connections
_frame_bridge_active = False
relay = MediaRelay() if AIORTC_AVAILABLE else None


# ---------- CORS Helper ----------
def _cors_response():
    resp = jsonify({"status": "ok"})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return resp


# ---------- Frame Bridge ----------
async def consume_and_bridge(track, pc):
    """
    Consume frames from WebRTC video track and emit to Socket.IO.
    Waits for PC to be fully connected before consuming.
    """
    global _frame_bridge_active
    _frame_bridge_active = True

    from app import socketio

    frame_count = 0
    logger.info("Frame bridge: waiting for PC to reach 'connected' state...")

    # Wait for connection
    for i in range(60):  # 30 seconds max
        if pc.connectionState == "connected":
            logger.info("Frame bridge: PC connected! Starting frame consumption.")
            break
        if pc.connectionState in ["failed", "closed"]:
            logger.error(f"Frame bridge: PC state is {pc.connectionState}, aborting")
            _frame_bridge_active = False
            return
        await asyncio.sleep(0.5)
    else:
        logger.error(f"Frame bridge: PC never connected (stuck at {pc.connectionState})")
        _frame_bridge_active = False
        return

    # Let DTLS/SRTP fully initialize
    await asyncio.sleep(1.0)
    logger.info(f"Frame bridge: starting recv loop. Track={track.kind}, state={track.readyState}")

    try:
        while _frame_bridge_active:
            try:
                frame = await asyncio.wait_for(track.recv(), timeout=30.0)
                frame_count += 1

                if frame_count == 1:
                    logger.info(f"Frame bridge: FIRST FRAME! {frame.width}x{frame.height}")

                # Relay every 2nd frame to reduce load
                if frame_count % 2 != 0:
                    continue

                # Convert to JPEG base64
                img = frame.to_ndarray(format="bgr24")
                _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Emit to browser via Socket.IO
                socketio.emit('frame', {
                    'frame': frame_b64,
                    'timestamp': str(frame.pts),
                    'camera_id': 1
                }, namespace='/stream')

                if frame_count % 100 == 0:
                    logger.info(f"Frame bridge: relayed {frame_count} frames")

            except asyncio.TimeoutError:
                logger.warning(f"Frame bridge: 30s timeout. Track={track.readyState}, PC={pc.connectionState}")
                break
            except Exception as e:
                logger.info(f"Frame bridge stopped: {type(e).__name__}: {e}")
                break
    finally:
        _frame_bridge_active = False
        logger.info(f"Frame bridge ended after {frame_count} frames")


# ---------- Routes ----------
@webrtc_bp.route('/streamer', methods=['POST', 'OPTIONS'])
def handle_streamer_offer():
    """Handle WebRTC offer from Windows streaming client."""
    if request.method == 'OPTIONS':
        return _cors_response()

    if not AIORTC_AVAILABLE:
        return jsonify({"error": "WebRTC not available. Install aiortc."}), 503

    try:
        params = request.json
        if not params or 'sdp' not in params or 'type' not in params:
            return jsonify({"error": "Missing 'sdp' or 'type' in request body"}), 400

        result = run_async(_handle_streamer(params))
        return result

    except Exception as e:
        logger.error(f"Streamer offer error: {e}")
        return jsonify({"error": str(e)}), 500


@webrtc_bp.route('/offer', methods=['POST', 'OPTIONS'])
def handle_viewer_offer():
    """Handle WebRTC offer from browser viewer."""
    if request.method == 'OPTIONS':
        return _cors_response()

    if not AIORTC_AVAILABLE:
        return jsonify({"error": "WebRTC not available"}), 503

    try:
        result = run_async(_handle_viewer(request.json))
        return result
    except Exception as e:
        logger.error(f"Viewer offer error: {e}")
        return jsonify({"error": str(e)}), 500



# ---------- Helper for HTTP Frames ----------
_http_frame_count = 0

@webrtc_bp.route('/frame', methods=['POST', 'OPTIONS'])
def receive_frame():
    """
    HTTP endpoint to receive video frames from the Windows client.
    Reliable fallback when WebRTC media transport doesn't work.
    Accepts: { "frame": "<base64 JPEG>", "camera_id": "main", "timestamp": <float> }
    """
    global _http_frame_count
    
    if request.method == 'OPTIONS':
        return _cors_response()
    
    try:
        data = request.json
        if not data or 'frame' not in data:
            return jsonify({"error": "Missing 'frame' field"}), 400
        
        _http_frame_count += 1
        
        # Import socketio and emit frame to browser
        from app import socketio
        socketio.emit('frame', {
            'frame': data['frame'],
            'timestamp': str(data.get('timestamp', '')),
            'camera_id': data.get('camera_id', 1)
        }, namespace='/stream')
        
        if _http_frame_count % 100 == 0:
            logger.info(f"HTTP frame relay: {_http_frame_count} frames received")
        
        return jsonify({"status": "ok", "frame_count": _http_frame_count}), 200
        
    except Exception as e:
        logger.error(f"Frame receive error: {e}")
        return jsonify({"error": str(e)}), 500


@webrtc_bp.route('/stats', methods=['GET'])
@jwt_required(optional=True)
def get_stats():
    """Get Webrtc Stats"""
    return jsonify({
        "available": AIORTC_AVAILABLE,
        "active_viewers": len(peer_connections),
        "streamer_connected": streamer_pc is not None,
        "frame_bridge_active": _frame_bridge_active,
        "server_ice_mode": "STUN only (no TURN)",
        "http_frames_received": _http_frame_count,
        "connections": list(peer_connections.keys())
    })


@webrtc_bp.route('/ice-config', methods=['GET'])
def get_ice_config():
    """Return TURN server config for clients that need it (Windows client)."""
    return jsonify({
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": [
                    "turn:13.205.156.238:3478",
                    "turn:13.205.156.238:3478?transport=tcp"
                ],
                "username": "surveillx",
                "credential": "Vishu@9637"
            }
        ]
    })


# ---------- Async Handlers ----------
async def _handle_streamer(params):
    """Async handler for streamer WebRTC offer."""
    global streamer_pc, _frame_bridge_active

    try:
        # Close existing streamer
        if streamer_pc:
            _frame_bridge_active = False
            try:
                await streamer_pc.close()
            except:
                pass
            streamer_pc = None

        # Server uses STUN only — no TURN needed (has public IP)
        pc = RTCPeerConnection(configuration=SERVER_ICE_CONFIG)
        pc_id = f"streamer-{str(uuid.uuid4())[:8]}"
        streamer_pc = pc

        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"Streamer {pc_id}: {state}")
            if state in ["failed", "closed", "disconnected"]:
                global streamer_pc, _frame_bridge_active
                _frame_bridge_active = False
                if streamer_pc == pc:
                    streamer_pc = None

        @pc.on("track")
        def on_track(track):
            logger.info(f"Received {track.kind} track from streamer")

            if track.kind == "video":
                # Start frame bridge on the event loop
                loop = get_event_loop()
                asyncio.run_coroutine_threadsafe(consume_and_bridge(track, pc), loop)
                logger.info("Frame bridge task scheduled")

                # Also relay to WebRTC viewers
                for vid, vpc in list(peer_connections.items()):
                    try:
                        vpc.addTrack(relay.subscribe(track))
                    except Exception as e:
                        logger.error(f"Failed to relay to viewer {vid}: {e}")

        # Set remote description (the client's offer)
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        await pc.setRemoteDescription(offer)

        # Create and set local description (our answer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        logger.info(f"Streamer {pc_id} SDP exchange complete")

        response = jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        logger.error(f"Streamer handler error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


async def _handle_viewer(params):
    """Async handler for browser viewer WebRTC offer."""
    global streamer_pc

    try:
        if not params or 'sdp' not in params:
            return jsonify({"error": "Missing SDP"}), 400

        pc = RTCPeerConnection(configuration=SERVER_ICE_CONFIG)
        viewer_id = f"viewer-{str(uuid.uuid4())[:8]}"
        peer_connections[viewer_id] = pc

        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"Viewer {viewer_id}: {state}")
            if state in ["failed", "closed", "disconnected"]:
                peer_connections.pop(viewer_id, None)

        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        logger.info(f"Viewer {viewer_id} SDP exchange complete")

        response = jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        logger.error(f"Viewer handler error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
