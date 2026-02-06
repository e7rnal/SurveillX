# Windows Client Setup Guide

Complete setup instructions for the SurveillX Windows streaming client.

## Prerequisites

### 1. Install Python 3.9+

Download from [python.org](https://www.python.org/downloads/windows/)

**Important:** Check "Add Python to PATH" during installation.

### 2. Install Visual Studio Build Tools (for face_recognition)

Download from [Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

Required components:
- C++ Build Tools
- Windows 10/11 SDK

### 3. Install CMake

Download from [cmake.org](https://cmake.org/download/)

## Installation Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/e7rnal/SurveillX.git
cd SurveillX/windows-client
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If `face_recognition` fails to install:

```bash
pip install cmake
pip install dlib
pip install face_recognition
```

### Step 4: Configure Settings

1. Copy default settings:
   ```bash
   copy config\default_settings.json config\settings.json
   ```

2. Edit `config/settings.json`:
   - Set `server.url` to your backend server URL
   - Set `auth.username` and `auth.password`

### Step 5: Test Camera

```bash
python src/test_camera.py
```

### Step 6: Run Client

```bash
python src/main.py
```

## Troubleshooting

### Camera Not Found

1. Check camera is connected
2. Try different `camera.device_id` values (0, 1, 2...)
3. Close other apps using the camera

### Connection Failed

1. Verify server URL is correct
2. Check network connectivity
3. Ensure backend server is running
4. Check firewall settings

### Face Recognition Not Working

1. Ensure good lighting
2. Face should be clearly visible
3. Check `detection.min_face_confidence` setting

## Building Executable

To create a standalone `.exe` file:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name SurveillX-Client src/gui_launcher.py
```

The executable will be in `dist/SurveillX-Client.exe`

## Support

For issues, open a GitHub issue or contact support.
