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
import uuid
import cv2
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

webrtc_bp = Blueprint('webrtc', __name__)

# Store peer connections and state
peer_connections = {}
streamer_pc = None
_event_loop = None
_loop_thread = None

# Try to import aiortc
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRelay
    from av import VideoFrame
    AIORTC_AVAILABLE = True
    relay = MediaRelay()
except ImportError:
    AIORTC_AVAILABLE = False
    logger.warning("aiortc not installed - WebRTC disabled. Install with: pip install aiortc")


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
    
    return _event_loop


def run_async(coro):
    """Run an async coroutine from sync Flask context using background event loop."""
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)


class FrameBridgeTrack(MediaStreamTrack):
    """
    Receives video frames from WebRTC streamer and bridges them
    to Socket.IO for the browser live monitor.
    """
    kind = "video"
    
    def __init__(self, source_track, socketio_instance=None):
        super().__init__()
        self.source_track = source_track
        self.socketio = socketio_instance
        self._frame_count = 0
        self._running = True
        logger.info("FrameBridgeTrack created - will relay WebRTC to Socket.IO")
    
    async def recv(self):
        frame = await self.source_track.recv()
        
        # Relay every Nth frame to Socket.IO to avoid overloading
        self._frame_count += 1
        if self._frame_count % 2 == 0 and self.socketio:  # every 2nd frame
            try:
                # Convert frame to JPEG base64
                img = frame.to_ndarray(format="bgr24")
                _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Emit to Socket.IO /stream namespace
                self.socketio.emit('frame', {
                    'frame': frame_b64,
                    'timestamp': frame.time,
                    'camera_id': 1
                }, namespace='/stream')
                
            except Exception as e:
                if self._frame_count % 100 == 0:
                    logger.error(f"Frame bridge error: {e}")
        
        return frame
    
    def stop(self):
        self._running = False
        super().stop()


@webrtc_bp.route('/streamer', methods=['POST', 'OPTIONS'])
def handle_streamer_offer():
    """Handle WebRTC offer from streaming client (Windows client)."""
    if request.method == 'OPTIONS':
        return _cors_response()
    
    if not AIORTC_AVAILABLE:
        return jsonify({"error": "WebRTC not available on server. Install aiortc."}), 503
    
    try:
        params = request.json
        if not params or 'sdp' not in params or 'type' not in params:
            return jsonify({"error": "Missing 'sdp' or 'type' in request body"}), 400
        
        result = run_async(_handle_streamer_offer_async(params))
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
        return jsonify({"error": "WebRTC not available on server"}), 503
    
    try:
        result = run_async(_handle_viewer_offer_async(request.json))
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
        "connections": list(peer_connections.keys())
    })


async def _handle_streamer_offer_async(params):
    """Async handler for streamer WebRTC offer."""
    global streamer_pc
    
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        # Close existing streamer connection
        if streamer_pc:
            try:
                await streamer_pc.close()
            except:
                pass
            streamer_pc = None
        
        pc = RTCPeerConnection()
        pc_id = f"streamer-{str(uuid.uuid4())[:8]}"
        streamer_pc = pc
        
        # Get socketio instance for frame bridging
        from app import socketio as sio_instance
        
        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"Streamer {pc_id}: {state}")
            if state in ["failed", "closed", "disconnected"]:
                global streamer_pc
                if streamer_pc == pc:
                    streamer_pc = None
        
        @pc.on("track")
        def on_track(track):
            logger.info(f"Received {track.kind} track from streamer")
            
            if track.kind == "video":
                # Create bridge track that relays to Socket.IO
                bridge = FrameBridgeTrack(track, socketio_instance=sio_instance)
                
                # Also relay to any WebRTC viewers
                for viewer_id, viewer_pc in list(peer_connections.items()):
                    try:
                        relayed = relay.subscribe(track)
                        viewer_pc.addTrack(relayed)
                    except Exception as e:
                        logger.error(f"Failed to relay to viewer {viewer_id}: {e}")
                
                # Start consuming frames in background to trigger the bridge
                asyncio.ensure_future(_consume_frames(bridge))
        
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        logger.info(f"Streamer {pc_id} connected successfully")
        
        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "connection_id": pc_id
        })
        
    except Exception as e:
        logger.error(f"Streamer offer error: {e}")
        return jsonify({"error": str(e)}), 500


async def _consume_frames(bridge_track):
    """Consume frames from bridge track to keep the pipeline flowing."""
    try:
        while True:
            try:
                await bridge_track.recv()
            except Exception as e:
                logger.info(f"Frame bridge stopped: {e}")
                break
    except asyncio.CancelledError:
        pass


async def _handle_viewer_offer_async(params):
    """Async handler for viewer WebRTC offer."""
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        pc = RTCPeerConnection()
        pc_id = f"viewer-{str(uuid.uuid4())[:8]}"
        peer_connections[pc_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_state_change():
            state = pc.connectionState
            logger.info(f"Viewer {pc_id}: {state}")
            if state in ["failed", "closed", "disconnected"]:
                await pc.close()
                peer_connections.pop(pc_id, None)
        
        # Add video transceiver for receiving
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
