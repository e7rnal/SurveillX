"""
WebRTC API Blueprint
Handles WebRTC signaling for streaming from Windows client.
Bridges WebRTC video frames to Socket.IO for browser live monitor.
"""
import asyncio
import base64
import json
import logging
import threading
import time
import uuid
import cv2
import numpy as np
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

webrtc_bp = Blueprint('webrtc', __name__)

# Store peer connections and state
peer_connections = {}
streamer_pc = None
_event_loop = None
_loop_thread = None
_frame_bridge_active = False

# Try to import aiortc
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaRelay
    AIORTC_AVAILABLE = True
    relay = MediaRelay()
except ImportError:
    AIORTC_AVAILABLE = False
    logger.warning("aiortc not installed - WebRTC disabled")

# ICE Server configuration (STUN + TURN)
ICE_SERVERS = RTCConfiguration([
    RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
    RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
    RTCIceServer(
        urls=["turn:13.205.156.238:3478"],
        username="surveillx",
        credential="Vishu@9637"
    ),
]) if AIORTC_AVAILABLE else None


def get_event_loop():
    """Get or create a persistent event loop running in a background thread."""
    global _event_loop, _loop_thread

    if _event_loop is not None and _event_loop.is_running():
        return _event_loop

    _event_loop = asyncio.new_event_loop()

    def run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    _loop_thread = threading.Thread(target=run_loop, args=(_event_loop,), daemon=True)
    _loop_thread.start()
    time.sleep(0.1)  # Give loop time to start

    return _event_loop


def run_async(coro):
    """Run an async coroutine from sync Flask context using background event loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


async def consume_and_bridge(track):
    """
    Consume frames from the WebRTC video track and emit them
    to Socket.IO /stream namespace for the browser live monitor.
    """
    global _frame_bridge_active
    _frame_bridge_active = True

    # Import socketio inside the function to avoid circular imports
    from app import socketio

    frame_count = 0
    logger.info("Frame bridge started - relaying WebRTC frames to Socket.IO")

    try:
        while _frame_bridge_active:
            try:
                frame = await track.recv()
                frame_count += 1

                # Relay every 2nd frame to avoid overloading
                if frame_count % 2 != 0:
                    continue

                # Convert AV frame to JPEG base64
                img = frame.to_ndarray(format="bgr24")
                _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Emit to Socket.IO from background thread
                socketio.emit('frame', {
                    'frame': frame_b64,
                    'timestamp': str(frame.pts),
                    'camera_id': 1
                }, namespace='/stream')

                if frame_count % 100 == 0:
                    logger.info(f"Frame bridge: relayed {frame_count} frames")

            except Exception as e:
                logger.info(f"Frame bridge stopped: {e}")
                break
    finally:
        _frame_bridge_active = False
        logger.info(f"Frame bridge ended after {frame_count} frames")


@webrtc_bp.route('/streamer', methods=['POST', 'OPTIONS'])
def handle_streamer_offer():
    """Handle WebRTC offer from streaming client (Windows client)."""
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
@jwt_required(optional=True)
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


@webrtc_bp.route('/stats', methods=['GET'])
@jwt_required(optional=True)
def get_stats():
    """Get WebRTC connection stats."""
    return jsonify({
        "available": AIORTC_AVAILABLE,
        "active_viewers": len(peer_connections),
        "streamer_connected": streamer_pc is not None,
        "frame_bridge_active": _frame_bridge_active,
        "connections": list(peer_connections.keys())
    })


async def _handle_streamer(params):
    """Async handler for streamer WebRTC offer."""
    global streamer_pc, _frame_bridge_active

    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        # Close existing streamer
        if streamer_pc:
            _frame_bridge_active = False
            try:
                await streamer_pc.close()
            except:
                pass
            streamer_pc = None

        pc = RTCPeerConnection(configuration=ICE_SERVERS)
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
                # Start frame bridge in the event loop
                loop = get_event_loop()
                asyncio.run_coroutine_threadsafe(consume_and_bridge(track), loop)
                logger.info("Frame bridge task scheduled")

                # Also relay to WebRTC viewers
                for vid, vpc in list(peer_connections.items()):
                    try:
                        vpc.addTrack(relay.subscribe(track))
                    except Exception as e:
                        logger.error(f"Relay to {vid}: {e}")

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        logger.info(f"Streamer {pc_id} SDP exchange complete")

        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "connection_id": pc_id
        })

    except Exception as e:
        logger.error(f"Streamer offer error: {e}")
        return jsonify({"error": str(e)}), 500


async def _handle_viewer(params):
    """Async handler for viewer WebRTC offer."""
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection(configuration=ICE_SERVERS)
        pc_id = f"viewer-{str(uuid.uuid4())[:8]}"
        peer_connections[pc_id] = pc

        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"Viewer {pc_id}: {state}")
            if state in ["failed", "closed", "disconnected"]:
                await pc.close()
                peer_connections.pop(pc_id, None)

        pc.addTransceiver("video", direction="recvonly")

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "connection_id": pc_id
        })

    except Exception as e:
        logger.error(f"Viewer offer error: {e}")
        return jsonify({"error": str(e)}), 500


def _cors_response():
    """Return CORS preflight response."""
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response
