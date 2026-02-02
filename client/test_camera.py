#!/usr/bin/env python3
"""
Quick camera test for WSL
Run: python3 test_camera.py
"""
import sys
import time

print("Testing camera access...")
print("")

# Check for OpenCV
try:
    import cv2
    print(f"✅ OpenCV version: {cv2.__version__}")
except ImportError:
    print("❌ OpenCV not installed!")
    print("Run: pip3 install opencv-python-headless")
    sys.exit(1)

# Check /dev/video devices
import subprocess
result = subprocess.run(['ls', '-la', '/dev/'], capture_output=True, text=True)
video_devices = [line for line in result.stdout.split('\n') if 'video' in line]
print(f"\n📹 Video devices found: {len(video_devices)}")
for dev in video_devices:
    print(f"   {dev.split()[-1] if dev else 'none'}")

if not video_devices:
    print("\n❌ No video devices found!")
    print("\nTo fix, run in Windows PowerShell (Admin):")
    print("  usbipd list")
    print("  usbipd attach --wsl --busid <BUSID>")
    sys.exit(1)

# Try to open camera
print("\n🎥 Trying to open /dev/video0...")

# Use timeout to avoid hanging
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Camera open timed out!")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5 second timeout

try:
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    signal.alarm(0)  # Cancel alarm
    
    if cap.isOpened():
        print("✅ Camera opened successfully!")
        
        # Try to grab a frame
        ret, frame = cap.read()
        if ret:
            print(f"✅ Frame captured: {frame.shape}")
        else:
            print("⚠️ Camera open but can't read frames")
        
        cap.release()
    else:
        print("❌ Camera failed to open")
        print("\nPossible fixes:")
        print("1. Re-attach USB: usbipd attach --wsl --busid <BUSID>")
        print("2. Check permissions: sudo chmod 666 /dev/video0")
        print("3. Check if another app is using the camera")

except TimeoutError:
    print("❌ Camera open timed out (>5 seconds)")
    print("\nThis usually means the USB device isn't properly connected to WSL")
    print("Re-attach with: usbipd attach --wsl --busid <BUSID>")

except Exception as e:
    print(f"❌ Error: {e}")

print("\nDone!")
