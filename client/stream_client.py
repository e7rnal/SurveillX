#!/usr/bin/env python3
"""
SurveillX Streaming Client (Windows Compatible)
Run this on your laptop to stream webcam video to the server

Usage:
    python stream_client.py --server http://65.0.87.179:5000

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
        self.quality = quality
        
        self.sio = socketio.Client()
        self.running = False
        self.cap = None
        self.frame_count = 0
        self.start_time = None
        
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.sio.event
        def connect():
            print(f"[OK] Connected to server: {self.server_url}")
            print(f"     Streaming from camera {self.camera_id}")
        
        @self.sio.event
        def connect_error(data):
            print(f"[ERROR] Connection error: {data}")
        
        @self.sio.event
        def disconnect():
            print("[INFO] Disconnected from server")
        
        @self.sio.on('status')
        def on_status(data):
            print(f"     Server: {data.get('message', 'Connected')}")
        
        @self.sio.on('detection')
        def on_detection(data):
            faces = data.get('faces', [])
            activity = data.get('activity', 'Normal')
            if faces or activity != 'Normal':
                print(f"     Detection: Faces={len(faces)}, Activity={activity}")
    
    def start(self):
        print("")
        print("=" * 50)
        print("SurveillX Stream Client")
        print("=" * 50)
        
        print(f"\nOpening camera {self.camera_id}...")
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            print("[ERROR] Failed to open camera")
            print("        Try: --camera 1 or --camera 2")
            return False
        
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[OK] Camera opened: {width}x{height}")
        
        print(f"\nConnecting to {self.server_url}...")
        try:
            self.sio.connect(self.server_url, namespaces=['/stream'])
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            self.cap.release()
            return False
        
        self.running = True
        self.start_time = time.time()
        self.frame_count = 0
        
        print("\n>>> Streaming started (Press Ctrl+C to stop)")
        print("-" * 50)
        
        frame_interval = 1.0 / self.target_fps
        last_frame_time = 0
        
        try:
            while self.running:
                current_time = time.time()
                
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                
                ret, frame = self.cap.read()
                if not ret:
                    print("[WARN] Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
                _, buffer = cv2.imencode('.jpg', frame, encode_params)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                self.sio.emit('frame', {
                    'frame': frame_base64,
                    'camera_id': self.camera_id,
                    'timestamp': datetime.now().isoformat()
                }, namespace='/stream')
                
                self.frame_count += 1
                last_frame_time = current_time
                
                elapsed = current_time - self.start_time
                if self.frame_count % (self.target_fps * 5) == 0:
                    actual_fps = self.frame_count / elapsed
                    print(f"     Stats: {self.frame_count} frames, {actual_fps:.1f} FPS, {elapsed:.0f}s")
                
        except KeyboardInterrupt:
            print("\n\n>>> Stopping stream...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        self.running = False
        
        if self.cap:
            self.cap.release()
        
        if self.sio.connected:
            self.sio.disconnect()
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                print(f"\n[OK] Stream ended")
                print(f"     Total frames: {self.frame_count}")
                print(f"     Average FPS: {self.frame_count / elapsed:.1f}")
                print(f"     Duration: {elapsed:.1f}s")
        
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description='SurveillX Streaming Client',
        epilog='Example: python stream_client.py --server http://65.0.87.179:5000'
    )
    
    parser.add_argument('--server', '-s', required=True, help='Server URL')
    parser.add_argument('--camera', '-c', type=int, default=0, help='Camera ID (default: 0)')
    parser.add_argument('--fps', '-f', type=int, default=10, help='Target FPS (default: 10)')
    parser.add_argument('--quality', '-q', type=int, default=70, help='JPEG quality (default: 70)')
    
    args = parser.parse_args()
    
    if not args.server.startswith('http'):
        print("Error: Server URL must start with http:// or https://")
        sys.exit(1)
    
    args.quality = max(1, min(100, args.quality))
    args.fps = max(1, min(30, args.fps))
    
    client = StreamClient(
        server_url=args.server,
        camera_id=args.camera,
        fps=args.fps,
        quality=args.quality
    )
    
    client.start()


if __name__ == '__main__':
    main()
