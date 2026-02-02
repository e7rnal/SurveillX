#!/usr/bin/env python3
"""
SurveillX GStreamer WebSocket Client
Uses python-socketio with GStreamer for low-latency streaming
"""
import asyncio
import base64
import logging
import sys
import time
import subprocess
import tempfile
import os

try:
    import socketio
    import cv2
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install: pip3 install python-socketio[asyncio_client] opencv-python-headless aiohttp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SocketIOClient:
    """Stream webcam to server via Socket.IO"""
    
    def __init__(self, server_url: str, camera: int = 0, quality: int = 70, fps: int = 30):
        self.server_url = server_url.rstrip('/')
        self.camera = camera
        self.quality = quality
        self.fps = fps
        self.cap = None
        self.sio = None
        self.running = False
        self.frame_count = 0
        self.bytes_sent = 0
        self.start_time = None
        
    def init_camera(self):
        """Initialize webcam with low-latency settings"""
        logger.info(f"Opening camera /dev/video{self.camera}...")
        
        # Use GStreamer backend for better performance
        gst_pipeline = f"v4l2src device=/dev/video{self.camera} ! video/x-raw,width=640,height=480,framerate={self.fps}/1 ! videoconvert ! appsink"
        
        self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            logger.warning("GStreamer backend failed, trying V4L2...")
            self.cap = cv2.VideoCapture(self.camera, cv2.CAP_V4L2)
        
        if not self.cap.isOpened():
            logger.warning("V4L2 backend failed, trying default...")
            self.cap = cv2.VideoCapture(self.camera)
        
        if not self.cap.isOpened():
            logger.error("Cannot open camera!")
            return False
        
        # Low-latency settings
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Read one frame to verify
        ret, frame = self.cap.read()
        if ret:
            logger.info(f"✅ Camera ready: {frame.shape[1]}x{frame.shape[0]}")
            return True
        else:
            logger.error("Camera opened but can't read frames")
            return False
    
    async def connect(self):
        """Connect to server via Socket.IO"""
        logger.info(f"Connecting to {self.server_url}...")
        
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=10,
            logger=False
        )
        
        @self.sio.event
        async def connect():
            logger.info("✅ Socket.IO connected!")
        
        @self.sio.event
        async def disconnect():
            logger.warning("Disconnected from server")
            self.running = False
        
        @self.sio.event
        async def connect_error(error):
            logger.error(f"Connection error: {error}")
        
        try:
            await self.sio.connect(
                self.server_url,
                namespaces=['/stream'],
                transports=['websocket']
            )
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def stream(self):
        """Main streaming loop"""
        logger.info(f"Streaming at {self.fps} FPS, quality {self.quality}%")
        logger.info("Press Ctrl+C to stop")
        
        self.running = True
        self.start_time = time.time()
        frame_interval = 1.0 / self.fps
        last_stats = time.time()
        
        while self.running:
            loop_start = time.time()
            
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue
            
            # Encode to JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            _, buffer = cv2.imencode('.jpg', frame, encode_params)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send via Socket.IO
            try:
                await self.sio.emit('frame', {
                    'frame': frame_b64,
                    'timestamp': time.time(),
                    'camera_id': 'main'
                }, namespace='/stream')
                
                self.frame_count += 1
                self.bytes_sent += len(frame_b64)
                
            except Exception as e:
                logger.warning(f"Send error: {e}")
                await asyncio.sleep(0.1)
            
            # Stats every 5 seconds
            now = time.time()
            if now - last_stats >= 5:
                elapsed = now - self.start_time
                fps = self.frame_count / elapsed
                mbps = (self.bytes_sent * 8 / 1_000_000) / elapsed
                logger.info(f"📊 {fps:.1f} fps | {mbps:.2f} Mbps | {self.frame_count} frames")
                last_stats = now
            
            # FPS control
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    async def stop(self):
        """Cleanup"""
        logger.info("Stopping...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.sio:
            await self.sio.disconnect()
        
        if self.start_time and self.frame_count:
            elapsed = time.time() - self.start_time
            logger.info(f"Sent {self.frame_count} frames in {elapsed:.1f}s ({self.frame_count/elapsed:.1f} fps)")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="SurveillX Streaming Client")
    parser.add_argument("--server", default="http://surveillx.duckdns.org:5000", help="Server URL")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--quality", type=int, default=70, help="JPEG quality (30-95)")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS")
    args = parser.parse_args()
    
    print("=" * 55)
    print("  🎥 SurveillX Streaming Client")
    print("=" * 55)
    print(f"  Server:  {args.server}")
    print(f"  Camera:  /dev/video{args.camera}")
    print(f"  Quality: {args.quality}%")
    print(f"  FPS:     {args.fps}")
    print("=" * 55)
    
    client = SocketIOClient(args.server, args.camera, args.quality, args.fps)
    
    try:
        if not client.init_camera():
            print("\n❌ Camera failed to open")
            print("Try: sudo chmod 666 /dev/video0")
            return
        
        if not await client.connect():
            print("\n❌ Server connection failed")
            return
        
        await client.stream()
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopping...")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
