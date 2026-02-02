"""
WebRTC Server - Ultra-low latency video streaming
Uses aiortc for WebRTC signaling and relay
"""
import asyncio
import json
import logging
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRelay
import uuid
from datetime import datetime
import cv2
import numpy as np
from av import VideoFrame
import fractions

logger = logging.getLogger(__name__)

# Store active peer connections
peer_connections = {}
relay = MediaRelay()

# Video track that receives frames and relays to browsers
class VideoStreamTrack(MediaStreamTrack):
    """
    A video track that receives frames from the streaming client
    and relays them to browser viewers
    """
    kind = "video"
    
    def __init__(self):
        super().__init__()
        self.frame_queue = asyncio.Queue(maxsize=5)
        self.last_frame = None
        self._timestamp = 0
        
    async def recv(self):
        """Return next frame to be sent to browser"""
        try:
            # Get frame from queue with timeout
            frame = await asyncio.wait_for(self.frame_queue.get(), timeout=1.0)
            self.last_frame = frame
        except asyncio.TimeoutError:
            # Return last frame if no new frame available
            if self.last_frame is not None:
                frame = self.last_frame
            else:
                # Create black frame if no frames yet
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                frame = VideoFrame.from_ndarray(img, format="bgr24")
        
        # Set timestamp
        self._timestamp += 3000  # 30fps = 90000/30 = 3000
        frame.pts = self._timestamp
        frame.time_base = fractions.Fraction(1, 90000)
        
        return frame
    
    async def add_frame(self, frame_data):
        """Add frame from streaming client"""
        try:
            # Don't block if queue is full - drop oldest frame
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await self.frame_queue.put(frame_data)
        except Exception as e:
            logger.error(f"Error adding frame: {e}")


# Shared video track for all browser viewers
shared_video_track = None


def get_or_create_video_track():
    """Get or create shared video track"""
    global shared_video_track
    if shared_video_track is None:
        shared_video_track = VideoStreamTrack()
    return shared_video_track


async def handle_offer(request):
    """
    Handle WebRTC offer from browser viewer
    Browser sends offer, server responds with answer
    """
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pc_id = str(uuid.uuid4())[:8]
    peer_connections[pc_id] = pc
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection {pc_id}: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            peer_connections.pop(pc_id, None)
    
    # Add video track (relayed from streaming client)
    video_track = relay.subscribe(get_or_create_video_track())
    pc.addTrack(video_track)
    
    # Set remote description (browser's offer)
    await pc.setRemoteDescription(offer)
    
    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "connection_id": pc_id
    })


async def handle_streamer_offer(request):
    """
    Handle WebRTC offer from streaming client (laptop with camera)
    """
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pc_id = f"streamer-{str(uuid.uuid4())[:8]}"
    peer_connections[pc_id] = pc
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Streamer {pc_id}: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            peer_connections.pop(pc_id, None)
    
    @pc.on("track")
    def on_track(track):
        """Receive video track from streaming client"""
        logger.info(f"Received {track.kind} track from streamer")
        
        if track.kind == "video":
            # Replace shared video track with incoming stream
            global shared_video_track
            shared_video_track = relay.subscribe(track)
            logger.info("Video track ready for browser viewers")
    
    # Set remote description
    await pc.setRemoteDescription(offer)
    
    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type,
        "connection_id": pc_id
    })


async def handle_ice_candidate(request):
    """Handle ICE candidate exchange"""
    params = await request.json()
    pc_id = params.get("connection_id")
    candidate = params.get("candidate")
    
    if pc_id in peer_connections:
        pc = peer_connections[pc_id]
        # Add ICE candidate if provided
        if candidate:
            await pc.addIceCandidate(candidate)
    
    return web.json_response({"status": "ok"})


async def handle_stats(request):
    """Get streaming stats"""
    return web.json_response({
        "active_connections": len(peer_connections),
        "connections": list(peer_connections.keys()),
        "video_track_active": shared_video_track is not None
    })


def create_webrtc_app():
    """Create aiohttp app for WebRTC signaling"""
    app = web.Application()
    
    # CORS headers
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            return response
        return middleware
    
    app.middlewares.append(cors_middleware)
    
    # Routes
    app.router.add_post("/webrtc/offer", handle_offer)
    app.router.add_post("/webrtc/streamer", handle_streamer_offer)
    app.router.add_post("/webrtc/ice", handle_ice_candidate)
    app.router.add_get("/webrtc/stats", handle_stats)
    
    return app


# For testing standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_webrtc_app()
    web.run_app(app, port=8080)
