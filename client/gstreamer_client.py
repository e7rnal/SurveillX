#!/usr/bin/env python3
"""
GStreamer-based WebRTC Streaming Client
Uses GStreamer pipeline directly for better WSL compatibility
"""
import asyncio
import argparse
import base64
import logging
import sys
import time
import subprocess

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"])
    import aiohttp

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Check for GStreamer
def check_gstreamer():
    result = subprocess.run(['which', 'gst-launch-1.0'], capture_output=True)
    if result.returncode != 0:
        print("❌ GStreamer not found!")
        print("\nInstall with:")
        print("sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad")
        sys.exit(1)
    print("✅ GStreamer found")

class GStreamerClient:
    """Stream camera using GStreamer + WebSocket"""
    
    def __init__(self, server_url: str, camera: int = 0):
        self.server_url = server_url.rstrip('/')
        self.camera = camera
        self.process = None
        self.running = False
        
    async def test_connection(self):
        """Test server connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        logger.info("✅ Server connection OK")
                        return True
        except Exception as e:
            logger.error(f"❌ Cannot reach server: {e}")
        return False
    
    async def stream_with_gstreamer(self):
        """Stream using GStreamer pipeline directly"""
        logger.info("Starting GStreamer stream...")
        
        # GStreamer pipeline that outputs JPEG frames to stdout
        pipeline = f"""
        gst-launch-1.0 -q \
            v4l2src device=/dev/video{self.camera} ! \
            video/x-raw,width=640,height=480,framerate=30/1 ! \
            videoconvert ! \
            jpegenc quality=70 ! \
            filesink location=/dev/stdout
        """
        
        logger.info(f"Pipeline: v4l2src -> jpegenc -> WebSocket")
        
        self.process = await asyncio.create_subprocess_shell(
            pipeline.strip(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        self.running = True
        frame_count = 0
        start_time = time.time()
        
        # Read JPEG frames from GStreamer and send via HTTP
        buffer = b''
        
        while self.running:
            try:
                chunk = await asyncio.wait_for(
                    self.process.stdout.read(8192),
                    timeout=2.0
                )
                
                if not chunk:
                    break
                
                buffer += chunk
                
                # Look for JPEG start/end markers
                while True:
                    start = buffer.find(b'\xff\xd8')  # JPEG start
                    if start == -1:
                        break
                    
                    end = buffer.find(b'\xff\xd9', start + 2)  # JPEG end
                    if end == -1:
                        break
                    
                    # Extract complete JPEG
                    jpeg_data = buffer[start:end + 2]
                    buffer = buffer[end + 2:]
                    
                    # Send frame to server
                    await self.send_frame(jpeg_data)
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        elapsed = time.time() - start_time
                        fps = frame_count / elapsed
                        logger.info(f"Streaming: {fps:.1f} fps | {frame_count} frames")
                        
            except asyncio.TimeoutError:
                logger.warning("No data from camera, retrying...")
                continue
            except Exception as e:
                logger.error(f"Error: {e}")
                break
    
    async def send_frame(self, jpeg_data: bytes):
        """Send JPEG frame to server via HTTP"""
        try:
            encoded = base64.b64encode(jpeg_data).decode('utf-8')
            
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.server_url}/api/stream/frame",
                    json={
                        'frame': encoded,
                        'timestamp': time.time(),
                        'camera_id': 'main'
                    },
                    timeout=aiohttp.ClientTimeout(total=1)
                )
        except Exception as e:
            pass  # Don't log every failed frame
    
    async def stop(self):
        """Stop streaming"""
        self.running = False
        if self.process:
            self.process.terminate()
            await self.process.wait()


async def main():
    parser = argparse.ArgumentParser(description="GStreamer Streaming Client")
    parser.add_argument("--server", default="http://localhost:5000")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()
    
    print("=" * 50)
    print("  SurveillX GStreamer Client")
    print("=" * 50)
    print(f"  Server: {args.server}")
    print(f"  Camera: /dev/video{args.camera}")
    print("=" * 50)
    
    check_gstreamer()
    
    client = GStreamerClient(args.server, args.camera)
    
    # Test connection first
    if not await client.test_connection():
        return
    
    # Test camera with GStreamer
    print("\n🎥 Testing camera with GStreamer...")
    test_cmd = f"gst-launch-1.0 -v v4l2src device=/dev/video{args.camera} num-buffers=1 ! fakesink"
    result = subprocess.run(test_cmd.split(), capture_output=True, timeout=5)
    
    if result.returncode != 0:
        print(f"❌ Camera test failed!")
        print(f"Try: sudo chmod 666 /dev/video{args.camera}")
        print(f"Or try --camera 1")
        return
    
    print("✅ Camera test passed!")
    
    try:
        await client.stream_with_gstreamer()
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
