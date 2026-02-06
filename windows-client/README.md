# SurveillX Windows Client

Real-time surveillance streaming client for Windows that captures video from laptop camera and streams to SurveillX backend with AI-powered face recognition and activity detection.

## 🎯 Features

- **Real-time Camera Streaming** - Capture and stream video from webcam
- **Face Recognition** - Local face detection before sending to server
- **Activity Detection** - Detect running, fighting, and suspicious activities
- **Low Latency** - Optimized WebSocket streaming with JPEG compression
- **Auto-Reconnect** - Automatic reconnection on network issues
- **System Tray** - Runs in background with system tray icon

## 📋 Requirements

- Windows 10/11
- Python 3.9+
- Webcam/Camera
- Network connection to SurveillX backend

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd windows-client
pip install -r requirements.txt
```

### 2. Configure Server

Edit `config/settings.json`:

```json
{
    "server_url": "http://your-server-ip:5000",
    "camera_id": 0,
    "stream_quality": 80,
    "fps": 15
}
```

### 3. Run the Client

```bash
python src/main.py
```

Or use the GUI launcher:

```bash
python src/gui_launcher.py
```

## 📁 Project Structure

```
windows-client/
├── src/
│   ├── main.py              # Main entry point
│   ├── stream_client.py     # WebSocket streaming client
│   ├── camera_capture.py    # Camera capture module
│   ├── face_detector.py     # Local face detection
│   ├── activity_detector.py # Activity detection
│   └── gui_launcher.py      # GUI launcher with system tray
├── config/
│   └── settings.json        # Configuration file
├── assets/
│   └── icon.ico             # Application icon
├── docs/
│   └── SETUP.md             # Detailed setup guide
└── requirements.txt         # Python dependencies
```

## 🔧 Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `server_url` | Backend server URL | `http://localhost:5000` |
| `camera_id` | Camera device ID (0 for default) | `0` |
| `stream_quality` | JPEG quality (1-100) | `80` |
| `fps` | Frames per second | `15` |
| `enable_face_detection` | Enable local face detection | `true` |
| `enable_activity_detection` | Enable activity detection | `true` |

## 🔌 API Endpoints Used

The client connects to these backend endpoints:

- `POST /api/auth/login` - Authenticate and get JWT token
- `WS /stream` - WebSocket for real-time streaming
- `POST /api/attendance/mark` - Mark attendance on face detection

## 🛠️ Development

### Building Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico src/gui_launcher.py
```

### Running in Debug Mode

```bash
python src/main.py --debug
```

## 📝 License

Part of SurveillX AI-Powered Surveillance System
