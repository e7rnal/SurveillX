#!/usr/bin/env python3
"""
SurveillX Low-Latency Streaming Client
Optimized WebSocket-based streaming (~100-200ms latency)
Works through any firewall - no special ports needed!
"""
import asyncio
import argparse
import base64
import logging
import sys
import time
from typing import Optional

try:
    import cv2
    import numpy as np
    import socketio
except ImportError as e:
    print(f"Missing package: {e}")
    print("\nInstall with:")
    print("pip3 install python-socketio[client] opencv-python-headless aiohttp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LowLatencyStreamer:
    """
    WebSocket-based streaming client optimized for low latency
    Uses JPEG compression with quality/size balance for speed
    """
    
    def __init__(self, server_url: str, camera: int = 0):
        self.server_url = server_url.rstrip('/')
        self.camera_id = camera
        
        # Streaming settings - optimized for low latency
        self.width = 640
        self.height = 480
        self.fps = 30
        self.jpeg_quality = 65  # Lower = faster, smaller (50-80 is good)
        
        # State
        self.cap = None
        self.sio = None
        self.running = False
        self.connected = False
        self.frame_count = 0
        self.start_time = None
        
        # Stats
        self.bytes_sent = 0
        self.last_stats_time = 0
    
    def init_camera(self):
        """Initialize camera with low-latency settings"""
        logger.info(f"Opening camera {self.camera_id}...")
        
        # Try V4L2 backend (Linux)
        self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_id}")
        
        # Settings for low latency
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer!
        
        # Disable auto-exposure for consistent performance
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        
        actual = (
            int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            int(self.cap.get(cv2.CAP_PROP_FPS))
        )
        logger.info(f"Camera ready: {actual[0]}x{actual[1]} @ {actual[2]}fps")
        return True
    
    async def connect(self):
        """Connect to server via WebSocket"""
        logger.info(f"Connecting to {self.server_url}...")
        
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=5,
            reconnection_delay=1,
            logger=False
        )
        
        @self.sio.event
        async def connect():
            logger.info("✅ Connected to server!")
            self.connected = True
        
        @self.sio.event
        async def disconnect():
            logger.warning("Disconnected from server")
            self.connected = False
        
        @self.sio.event
        async def connect_error(error):
            logger.error(f"Connection error: {error}")
            self.connected = False
        
        try:
            await self.sio.connect(
                self.server_url,
                namespaces=['/stream'],
                transports=['websocket']  # Force WebSocket, skip polling
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def stream(self):
        """Main streaming loop - optimized for speed"""
        logger.info("Streaming... Press Ctrl+C to stop")
        
        self.running = True
        self.start_time = time.time()
        self.last_stats_time = self.start_time
        frame_interval = 1.0 / self.fps
        
        while self.running and self.connected:
            loop_start = time.time()
            
            # Grab frame (non-blocking)
            ret = self.cap.grab()
            if not ret:
                await asyncio.sleep(0.001)
                continue
            
            # Decode frame
            ret, frame = self.cap.retrieve()
            if not ret:
                continue
            
            # Encode to JPEG (faster than PNG)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            
            # Send via WebSocket
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            try:
                await self.sio.emit('frame', {
                    'frame': frame_data,
                    'timestamp': time.time(),
                    'camera_id': 'main'
                }, namespace='/stream')
                
                self.frame_count += 1
                self.bytes_sent += len(frame_data)
                
            except Exception as e:
                logger.error(f"Send error: {e}")
                await asyncio.sleep(0.1)
                continue
            
            # Stats every 5 seconds
            now = time.time()
            if now - self.last_stats_time >= 5:
                elapsed = now - self.start_time
                fps = self.frame_count / elapsed
                mbps = (self.bytes_sent * 8 / 1_000_000) / elapsed
                logger.info(f"Stats: {fps:.1f} fps | {mbps:.2f} Mbps | {self.frame_count} frames")
                self.last_stats_time = now
            
            # Frame rate control
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    async def stop(self):
        """Stop streaming and cleanup"""
        logger.info("Stopping...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.sio:
            await self.sio.disconnect()
        
        # Final stats
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(f"Sent {self.frame_count} frames in {elapsed:.1f}s")


async def main():
    parser = argparse.ArgumentParser(description="SurveillX Low-Latency Streaming Client")
    parser.add_argument("--server", default="http://localhost:5000",
                        help="Server URL (e.g., http://surveillx.duckdns.org:5000)")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device index")
    parser.add_argument("--quality", type=int, default=65,
                        help="JPEG quality (30-95, lower = faster)")
    parser.add_argument("--fps", type=int, default=30,
                        help="Target FPS")
    args = parser.parse_args()
    
    print("=" * 55)
    print("  SurveillX Low-Latency Streaming Client")
    print("=" * 55)
    print(f"  Server:  {args.server}")
    print(f"  Camera:  /dev/video{args.camera}")
    print(f"  Quality: {args.quality}%")
    print(f"  FPS:     {args.fps}")
    print("=" * 55)
    
    streamer = LowLatencyStreamer(args.server, args.camera)
    streamer.jpeg_quality = args.quality
    streamer.fps = args.fps
    
    try:
        # Initialize camera
        if not streamer.init_camera():
            print("\n❌ Failed to open camera")
            return
        
        # Connect to server
        if not await streamer.connect():
            print("\n❌ Failed to connect to server")
            return
        
        # Start streaming
        await streamer.stream()
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopping...")
    finally:
        await streamer.stop()


if __name__ == "__main__":
    asyncio.run(main())
