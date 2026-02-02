#!/usr/bin/env python3
"""
WebRTC Streaming Client for Kali Linux WSL
Ultra-low latency video streaming using GStreamer and aiortc
"""
import asyncio
import argparse
import json
import logging
import sys
from typing import Optional

# Check for required packages
try:
    import aiohttp
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    from aiortc.contrib.media import MediaPlayer, MediaRecorder
    import cv2
    import numpy as np
    from av import VideoFrame
except ImportError as e:
    print(f"Missing package: {e}")
    print("\nInstall with:")
    print("pip3 install aiortc aiohttp opencv-python-headless av")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CameraTrack(VideoStreamTrack):
    """
    Video track that captures from webcam using OpenCV
    Optimized for low latency
    """
    kind = "video"
    
    def __init__(self, device: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        super().__init__()
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self._start_time = None
        self._frame_count = 0
        
        self._init_camera()
    
    def _init_camera(self):
        """Initialize camera with optimal settings"""
        logger.info(f"Opening camera {self.device}...")
        
        # Try V4L2 backend first (Linux)
        self.cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        
        if not self.cap.isOpened():
            # Fallback to default backend
            self.cap = cv2.VideoCapture(self.device)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.device}")
        
        # Set camera properties for low latency
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
        
        # Get actual settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        
        logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
    
    async def recv(self):
        """Capture and return video frame"""
        if self._start_time is None:
            self._start_time = asyncio.get_event_loop().time()
        
        # Read frame from camera
        ret, frame = self.cap.read()
        
        if not ret:
            logger.warning("Failed to read frame, retrying...")
            await asyncio.sleep(0.01)
            return await self.recv()
        
        # Convert BGR to RGB for WebRTC
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create video frame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        
        # Calculate timestamp
        self._frame_count += 1
        elapsed = asyncio.get_event_loop().time() - self._start_time
        video_frame.pts = int(elapsed * 90000)  # 90kHz clock
        video_frame.time_base = "1/90000"
        
        return video_frame
    
    def stop(self):
        """Release camera"""
        if self.cap:
            self.cap.release()
            logger.info("Camera released")


class WebRTCStreamer:
    """WebRTC client for streaming to server"""
    
    def __init__(self, server_url: str, device: int = 0):
        self.server_url = server_url.rstrip('/')
        self.device = device
        self.pc: Optional[RTCPeerConnection] = None
        self.camera: Optional[CameraTrack] = None
        self.connection_id: Optional[str] = None
        self.running = False
    
    async def connect(self):
        """Establish WebRTC connection to server"""
        logger.info(f"Connecting to {self.server_url}...")
        
        # Create peer connection
        self.pc = RTCPeerConnection()
        
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"Connection state: {self.pc.connectionState}")
            if self.pc.connectionState == "connected":
                logger.info("✅ WebRTC connected! Streaming video...")
            elif self.pc.connectionState in ["failed", "closed", "disconnected"]:
                logger.warning(f"Connection {self.pc.connectionState}")
                self.running = False
        
        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE state: {self.pc.iceConnectionState}")
        
        # Create camera track
        try:
            self.camera = CameraTrack(device=self.device)
        except Exception as e:
            logger.error(f"Failed to open camera: {e}")
            print("\n❌ Camera not found!")
            print("Try: ls /dev/video*")
            print("Or run: usbipd attach --wsl --busid <BUSID>")
            return False
        
        # Add video track
        self.pc.addTrack(self.camera)
        
        # Create offer
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        
        # Wait for ICE gathering to complete
        await self._wait_for_ice()
        
        # Send offer to server
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.server_url}/webrtc/streamer",
                    json={
                        "sdp": self.pc.localDescription.sdp,
                        "type": self.pc.localDescription.type
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Server error: {response.status}")
                        return False
                    
                    result = await response.json()
                    self.connection_id = result.get("connection_id")
                    
                    # Set remote description (server's answer)
                    answer = RTCSessionDescription(
                        sdp=result["sdp"],
                        type=result["type"]
                    )
                    await self.pc.setRemoteDescription(answer)
                    
                    logger.info(f"Connected with ID: {self.connection_id}")
                    self.running = True
                    return True
                    
            except aiohttp.ClientError as e:
                logger.error(f"Connection failed: {e}")
                return False
    
    async def _wait_for_ice(self):
        """Wait for ICE gathering to complete"""
        if self.pc.iceGatheringState == "complete":
            return
        
        # Wait with timeout
        for _ in range(50):  # 5 second timeout
            if self.pc.iceGatheringState == "complete":
                break
            await asyncio.sleep(0.1)
    
    async def stream(self):
        """Keep connection alive and stream"""
        logger.info("Streaming... Press Ctrl+C to stop")
        
        frame_count = 0
        start_time = asyncio.get_event_loop().time()
        
        while self.running:
            await asyncio.sleep(1)
            
            # Log stats every 5 seconds
            frame_count += 1
            if frame_count % 5 == 0:
                elapsed = asyncio.get_event_loop().time() - start_time
                logger.info(f"Streaming: {elapsed:.0f}s | State: {self.pc.connectionState}")
    
    async def disconnect(self):
        """Clean up connection"""
        logger.info("Disconnecting...")
        
        if self.camera:
            self.camera.stop()
        
        if self.pc:
            await self.pc.close()
        
        self.running = False
        logger.info("Disconnected")


async def main():
    parser = argparse.ArgumentParser(description="WebRTC Streaming Client")
    parser.add_argument("--server", default="http://localhost:5000",
                        help="Server URL (e.g., http://65.0.87.179:5000)")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device index (default: 0)")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  SurveillX WebRTC Streaming Client")
    print("=" * 50)
    print(f"  Server: {args.server}")
    print(f"  Camera: /dev/video{args.camera}")
    print("=" * 50)
    
    streamer = WebRTCStreamer(args.server, args.camera)
    
    try:
        if await streamer.connect():
            await streamer.stream()
        else:
            print("\n❌ Failed to connect to server")
            print(f"Make sure server is running at {args.server}")
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopping...")
    finally:
        await streamer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
