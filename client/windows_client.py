"""
SurveillX Windows Streaming Client
Run directly on Windows - no WSL needed!

SETUP (one time):
1. Install Python from https://python.org
2. Open Command Prompt and run:
   pip install python-socketio[asyncio_client] opencv-python aiohttp

USAGE:
   python windows_client.py --server http://65.0.87.179:5000
"""
import asyncio
import base64
import sys
import time

# Check dependencies
try:
    import cv2
    import socketio
except ImportError as e:
    print(f"Missing package: {e}")
    print("\nInstall with:")
    print("pip install python-socketio[asyncio_client] opencv-python aiohttp")
    sys.exit(1)


class WindowsStreamer:
    """Simple webcam streamer for Windows"""
    
    def __init__(self, server_url: str, camera: int = 0):
        self.server_url = server_url.rstrip('/')
        self.camera = camera
        self.cap = None
        self.sio = None
        self.running = False
        
        # Settings
        self.quality = 70  # JPEG quality
        self.fps = 30
        self.width = 640
        self.height = 480
        
        # Stats
        self.frame_count = 0
        self.start_time = None
    
    def init_camera(self):
        """Open webcam"""
        print(f"Opening camera {self.camera}...")
        
        # Windows uses DirectShow backend
        self.cap = cv2.VideoCapture(self.camera, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            # Try default backend
            self.cap = cv2.VideoCapture(self.camera)
        
        if not self.cap.isOpened():
            print("ERROR: Cannot open camera!")
            print("Make sure no other app is using the webcam")
            return False
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Test frame
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"Camera ready: {w}x{h}")
            return True
        else:
            print("ERROR: Camera opened but can't read frames")
            return False
    
    async def connect(self):
        """Connect to server"""
        print(f"Connecting to {self.server_url}...")
        
        self.sio = socketio.AsyncClient(
            reconnection=True,
            logger=False
        )
        
        @self.sio.event
        async def connect():
            print("Connected to server!")
        
        @self.sio.event
        async def disconnect():
            print("Disconnected from server")
            self.running = False
        
        try:
            await self.sio.connect(
                self.server_url,
                namespaces=['/stream'],
                transports=['websocket']
            )
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    async def stream(self):
        """Stream frames to server"""
        print(f"\nStreaming at {self.fps} FPS...")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        self.start_time = time.time()
        last_stats = time.time()
        frame_interval = 1.0 / self.fps
        
        while self.running:
            start = time.time()
            
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                await asyncio.sleep(0.01)
                continue
            
            # Encode JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send to server
            try:
                await self.sio.emit('frame', {
                    'frame': frame_b64,
                    'timestamp': time.time(),
                    'camera_id': 'main'
                }, namespace='/stream')
                self.frame_count += 1
            except:
                pass
            
            # Print stats every 5 seconds
            now = time.time()
            if now - last_stats >= 5:
                elapsed = now - self.start_time
                fps = self.frame_count / elapsed
                print(f"[Stats] {fps:.1f} fps | {self.frame_count} frames sent")
                last_stats = now
            
            # FPS control
            elapsed = time.time() - start
            if elapsed < frame_interval:
                await asyncio.sleep(frame_interval - elapsed)
    
    async def stop(self):
        """Cleanup"""
        print("\nStopping...")
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.sio:
            await self.sio.disconnect()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="SurveillX Windows Streaming Client")
    parser.add_argument("--server", default="http://65.0.87.179:5000", help="Server URL")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (0 = default)")
    parser.add_argument("--quality", type=int, default=70, help="JPEG quality (1-100)")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS")
    args = parser.parse_args()
    
    print("=" * 50)
    print("  SurveillX Windows Streaming Client")
    print("=" * 50)
    print(f"  Server:  {args.server}")
    print(f"  Camera:  {args.camera}")
    print(f"  Quality: {args.quality}%")
    print(f"  FPS:     {args.fps}")
    print("=" * 50)
    
    client = WindowsStreamer(args.server, args.camera)
    client.quality = args.quality
    client.fps = args.fps
    
    try:
        if not client.init_camera():
            return
        
        if not await client.connect():
            return
        
        await client.stream()
        
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
