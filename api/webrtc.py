"""
WebRTC API Blueprint
Handles WebRTC signaling for ultra-low latency streaming
"""
import asyncio
import json
import logging
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

logger = logging.getLogger(__name__)

webrtc_bp = Blueprint('webrtc', __name__)

# Store peer connections and video state
peer_connections = {}
streamer_connection = None
video_frames = asyncio.Queue(maxsize=10)

# Try to import aiortc (may not be available)
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRelay
    AIORTC_AVAILABLE = True
    relay = MediaRelay()
except ImportError:
    AIORTC_AVAILABLE = False
    logger.warning("aiortc not installed - WebRTC disabled")


class VideoRelayTrack(MediaStreamTrack):
    """Video track that relays frames from streamer to viewers"""
    kind = "video"
    
    def __init__(self, source_track):
        super().__init__()
        self.source_track = source_track
    
    async def recv(self):
        return await self.source_track.recv()


@webrtc_bp.route('/offer', methods=['POST', 'OPTIONS'])
@jwt_required(optional=True)
def handle_viewer_offer():
    """Handle WebRTC offer from browser viewer"""
    if request.method == 'OPTIONS':
        return _cors_response()
    
    if not AIORTC_AVAILABLE:
        return jsonify({"error": "WebRTC not available on server"}), 503
    
    return asyncio.run(_handle_viewer_offer_async(request.json))


@webrtc_bp.route('/streamer', methods=['POST', 'OPTIONS'])
def handle_streamer_offer():
    """Handle WebRTC offer from streaming client"""
    if request.method == 'OPTIONS':
        return _cors_response()
    
    if not AIORTC_AVAILABLE:
        return jsonify({"error": "WebRTC not available on server"}), 503
    
    return asyncio.run(_handle_streamer_offer_async(request.json))


@webrtc_bp.route('/stats', methods=['GET'])
@jwt_required(optional=True)
def get_stats():
    """Get WebRTC connection stats"""
    return jsonify({
        "available": AIORTC_AVAILABLE,
        "active_viewers": len(peer_connections),
        "streamer_connected": streamer_connection is not None,
        "connections": list(peer_connections.keys())
    })


async def _handle_viewer_offer_async(params):
    """Async handler for viewer offer"""
    global peer_connections
    
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        pc = RTCPeerConnection()
        pc_id = str(uuid.uuid4())[:8]
        peer_connections[pc_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_state_change():
            logger.info(f"Viewer {pc_id}: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed", "disconnected"]:
                await pc.close()
                peer_connections.pop(pc_id, None)
        
        # Add video transceiver
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


async def _handle_streamer_offer_async(params):
    """Async handler for streamer offer"""
    global streamer_connection
    
    try:
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        pc = RTCPeerConnection()
        pc_id = f"streamer-{str(uuid.uuid4())[:8]}"
        streamer_connection = pc
        
        @pc.on("connectionstatechange")
        async def on_state_change():
            logger.info(f"Streamer {pc_id}: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed", "disconnected"]:
                global streamer_connection
                streamer_connection = None
        
        @pc.on("track")
        def on_track(track):
            logger.info(f"Received {track.kind} track from streamer")
            
            # Relay to all viewers
            if track.kind == "video":
                for viewer_id, viewer_pc in list(peer_connections.items()):
                    try:
                        relayed = relay.subscribe(track)
                        viewer_pc.addTrack(relayed)
                    except Exception as e:
                        logger.error(f"Failed to relay to {viewer_id}: {e}")
        
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return jsonify({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "connection_id": pc_id
        })
        
    except Exception as e:
        logger.error(f"Streamer offer error: {e}")
        return jsonify({"error": str(e)}), 500


def _cors_response():
    """Return CORS preflight response"""
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response
