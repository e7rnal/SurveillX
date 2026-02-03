# WSL Webcam + GStreamer Setup Guide

## Step 1: Enable WSL2 (Required for USB)

Open **PowerShell as Administrator** and run:

```powershell
# Check WSL version
wsl --list --verbose

# If using WSL1, upgrade to WSL2
wsl --set-version kali-linux 2
```

---

## Step 2: Install USBIPD (Windows Side)

This allows USB devices (webcam) to be accessed from WSL.

### Download and Install
```powershell
# In PowerShell (Admin)
winget install --interactive --exact dorssel.usbipd-win
```

Or download from: https://github.com/dorssel/usbipd-win/releases

**Restart your computer after installation!**

---

## Step 3: Connect Webcam to WSL

### In PowerShell (Admin):
```powershell
# List USB devices
usbipd list

# Find your webcam (look for "Camera" or "Webcam")
# Note the BUSID (e.g., 1-3)

# Bind and attach to WSL
usbipd bind --busid 1-3
usbipd attach --wsl --busid 1-3
```

### In WSL Kali Terminal:
```bash
# Check if webcam is detected
ls /dev/video*

# Should show /dev/video0
```

---

## Step 4: Install GStreamer (WSL Kali)

```bash
# Update packages
sudo apt update

# Install GStreamer and plugins
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-x \
    libgstreamer1.0-dev \
    v4l-utils

# Install Python packages for WebRTC
pip3 install aiortc aiohttp opencv-python-headless av
```

---

## Step 5: Test Webcam in WSL

```bash
# Check video devices
v4l2-ctl --list-devices

# Test GStreamer capture (text output, no display)
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=10 ! fakesink

# If successful, you'll see:
# "Setting pipeline to PLAYING"
# "Got EOS from element 'pipeline0'"
```

---

## Step 6: Run WebRTC Client

After I create the client script:

```bash
cd ~/surveillx-client
python3 webrtc_client.py --server http://surveillx.duckdns.org:5000
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `/dev/video0` not found | Re-attach USB: `usbipd attach --wsl --busid X-X` |
| Permission denied | Run: `sudo chmod 666 /dev/video0` |
| GStreamer error | Install: `sudo apt install gstreamer1.0-v4l2` |

---

## Alternative: Windows Native (No WSL)

If USB passthrough doesn't work, use Windows directly:

1. Install GStreamer from: https://gstreamer.freedesktop.org/download/
2. Add to PATH: `C:\gstreamer\1.0\x86_64\bin`
3. Use the Windows version of the client script

---

**Next:** After you complete the WSL setup, let me know and I'll create the WebRTC client script!
