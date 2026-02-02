#!/usr/bin/env python3
"""
SurveillX Streaming Client
Run this on your laptop to stream webcam video to the server

Usage:
    python stream_client.py --server http://your-server-ip:5000

Requirements:
    pip install opencv-python python-socketio websocket-client
"""

import argparse
import base64
import cv2
import socketio
import time
import sys
from datetime import datetime

class StreamClient:
    def __init__(self, server_url, camera_id=0, fps=10, quality=70):
        self.server_url = server_url
        self.camera_id = camera_id
        self.target_fps = fps
        self.quality = quality  # JPEG quality 0-100
        
        self.sio = socketio.Client()
        self.running = False
        self.cap = None
        self.frame_count = 0
        self.start_time = None
        
        # Set up SocketIO event handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"✓ Connected to server: {self.server_url}")
            print(f"  Streaming from camera {self.camera_id}")
        
        @self.sio.event
        def connect_error(data):
            print(f"✗ Connection error: {data}")
        
        @self.sio.event
        def disconnect():
            print("✗ Disconnected from server")
        
        @self.sio.on('status')
        def on_status(data):
            print(f"  Server: {data.get('message', 'Connected')}")
        
        @self.sio.on('detection')
        def on_detection(data):
            faces = data.get('faces', [])
            activity = data.get('activity', 'Normal')
            if faces or activity != 'Normal':
                print(f"  Detection: Faces={len(faces)}, Activity={activity}")
    
    def start(self):
        """Start streaming"""
        print("\n" + "="*50)
        print("SurveillX Stream Client")
        print("="*50)
        
        # Open camera
        print(f"\nOpening camera {self.camera_id}...")
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print("✗ Failed to open camera")
            print("  Try a different camera_id (0, 1, 2, etc.)")
            return False
        
        # Get camera info
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"✓ Camera opened: {width}x{height}")
        
        # Connect to server
        print(f"\nConnecting to {self.server_url}...")
        try:
            self.sio.connect(self.server_url, namespaces=['/stream'])
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            self.cap.release()
            return False
        
        # Start streaming loop
        self.running = True
        self.start_time = time.time()
        self.frame_count = 0
        
        print("\n▶ Streaming started (Press Ctrl+C to stop)")
        print("-"*50)
        
        frame_interval = 1.0 / self.target_fps
        last_frame_time = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                # Frame rate limiting
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                
                ret, frame = self.cap.read()
                if not ret:
                    print("✗ Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                # Encode frame as JPEG
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_params)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame to server
                self.sio.emit('frame', {
                    'frame': frame_base64,
                    'camera_id': self.camera_id,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/stream')
                
                self.frame_count += 1
                last_frame_time = current_time
                
                # Print stats every 5 seconds
                elapsed = current_time - self.start_time
                if self.frame_count % (self.target_fps * 5) == 0:
                    actual_fps = self.frame_count / elapsed
                    print(f"  Stats: {self.frame_count} frames, {actual_fps:.1f} FPS, {elapsed:.0f}s elapsed")
                
                # Optional: show local preview
                # cv2.imshow('Preview', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
                
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping stream...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop streaming"""
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.sio.connected:
            self.sio.disconnect()
        
        # Print final stats
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                print(f"\n✓ Stream ended")
                print(f"  Total frames: {self.frame_count}")
                print(f"  Average FPS: {self.frame_count / elapsed:.1f}")
                print(f"  Duration: {elapsed:.1f}s")
        
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description='SurveillX Streaming Client - Stream webcam to server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python stream_client.py --server http://65.0.87.179:5000
    python stream_client.py --server http://localhost:5000 --camera 1
    python stream_client.py --server http://my-server:5000 --fps 15 --quality 80
        """
    )
    
    parser.add_argument(
        '--server', '-s',
        required=True,
        help='Server URL (e.g., http://65.0.87.179:5000)'
    )
    
    parser.add_argument(
        '--camera', '-c',
        type=int,
        default=0,
        help='Camera ID (default: 0)'
    )
    
    parser.add_argument(
        '--fps', '-f',
        type=int,
        default=10,
        help='Target FPS (default: 10)'
    )
    
    parser.add_argument(
        '--quality', '-q',
        type=int,
        default=70,
        help='JPEG quality 1-100 (default: 70)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.server.startswith('http'):
        print("Error: Server URL must start with http:// or https://")
        sys.exit(1)
    
    args.quality = max(1, min(100, args.quality))
    args.fps = max(1, min(30, args.fps))
    
    # Create and start client
    client = StreamClient(
        server_url=args.server,
        camera_id=args.camera,
        fps=args.fps,
        quality=args.quality
    )
    
    client.start()


if __name__ == '__main__':
    main()
