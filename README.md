# SurveillX - Smart Surveillance & Attendance System

> AI-powered campus surveillance with face recognition attendance and abnormal activity detection.

![Status](https://img.shields.io/badge/Status-In%20Development-yellow)
![Version](https://img.shields.io/badge/Version-2.0.0-blue)

## 🎯 Project Overview

SurveillX is an intelligent surveillance system designed for educational institutions. It provides:

- **Automated Attendance** - Face recognition marks attendance automatically
- **Live Monitoring** - Real-time video streaming from campus cameras
- **Activity Detection** - AI detects running, fighting, loitering
- **Self-Enrollment** - Students enroll via QR code/link with photo capture
- **Alert System** - Instant notifications for suspicious activity

---

## 🏗️ Architecture

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│  Laptop Camera  │ ───────────────→  │   Flask Server  │
│  (stream_client)│                   │   (app.py)      │
└─────────────────┘                   └────────┬────────┘
                                               │
       ┌───────────────────────────────────────┼──────────────────┐
       │                                       │                  │
       ▼                                       ▼                  ▼
┌──────────────┐                    ┌──────────────┐    ┌──────────────┐
│ Face Service │                    │  PostgreSQL  │    │  Frontend    │
│ (recognition)│                    │  (Database)  │    │  (Dashboard) │
└──────────────┘                    └──────────────┘    └──────────────┘
```

---

## 📁 Project Structure

```
surveillx-backend/
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings
├── .env                      # Environment variables (secrets)
│
├── api/                      # REST API endpoints
│   ├── auth.py               # Login/authentication
│   ├── students.py           # Student CRUD
│   ├── attendance.py         # Attendance records
│   ├── alerts.py             # Security alerts
│   ├── cameras.py            # Camera management
│   ├── clips.py              # Video clips
│   ├── enrollment.py         # Student enrollment
│   └── stats.py              # Dashboard statistics
│
├── services/                 # Business logic
│   ├── db_manager.py         # Database operations
│   ├── email_service.py      # AWS SES email
│   ├── face_service.py       # Face detection/recognition
│   └── stream_handler.py     # WebSocket video streaming
│
├── client/                   # Laptop streaming client
│   ├── stream_client.py      # Webcam capture & send
│   └── requirements.txt      # Client dependencies
│
├── templates/                # HTML pages
│   ├── index.html            # Main dashboard
│   ├── login.html            # Login page
│   └── enroll.html           # Student enrollment
│
├── static/                   # Frontend assets
│   ├── css/style.css         # Styling
│   └── js/
│       ├── api.js            # API wrapper
│       ├── app.js            # Main app controller
│       └── enrollment.js     # Enrollment functions
│
├── scripts/                  # Utility scripts
│   └── seed_demo_data.py     # Populate demo data
│
└── logs/                     # Application logs
    └── app.log
```

---

## 🚀 Quick Start

### 1. Server Setup (EC2)

```bash
# Clone repository
git clone https://github.com/e7rnal/SurveillX.git
cd SurveillX

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Start server
python app.py
```

### 2. Access Dashboard

```
URL: http://your-server-ip:5000/templates/login.html
Username: admin
Password: admin123
```

### 3. Start Streaming (on laptop)

```bash
cd client
pip install -r requirements.txt
python stream_client.py --server http://your-server-ip:5000
```

---

## 🔌 API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with username/password |

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/students/` | List all students |
| POST | `/api/students/` | Add new student |
| PUT | `/api/students/<id>` | Update student |
| DELETE | `/api/students/<id>` | Delete student |

### Attendance
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/attendance/` | Get attendance records |
| GET | `/api/attendance/today` | Today's attendance |
| POST | `/api/attendance/mark` | Mark attendance |

### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/alerts/` | List alerts (with filters) |
| GET | `/api/alerts/<id>` | Get alert details |
| PUT | `/api/alerts/<id>/resolve` | Resolve alert |

### Enrollment
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/enrollment/generate-link` | Generate enrollment link |
| GET | `/api/enrollment/verify/<token>` | Verify token |
| POST | `/api/enrollment/submit` | Submit enrollment |
| GET | `/api/enrollment/pending` | List pending enrollments |
| PUT | `/api/enrollment/<id>/approve` | Approve enrollment |
| PUT | `/api/enrollment/<id>/reject` | Reject enrollment |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/api/stats` | Dashboard statistics |

---

## 🗄️ Database Schema

### Tables

```sql
-- Students
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    roll_no VARCHAR(50) UNIQUE,
    contact_no VARCHAR(20),
    class VARCHAR(50),
    face_encoding TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Attendance
CREATE TABLE attendance_logs (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    camera_id INTEGER
);

-- Alerts
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    camera_id INTEGER,
    clip_path VARCHAR(255),
    severity VARCHAR(20),
    metadata JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Enrollment Tokens
CREATE TABLE enrollment_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE,
    email VARCHAR(255),
    roll_no VARCHAR(50),
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pending Enrollments
CREATE TABLE pending_enrollments (
    id SERIAL PRIMARY KEY,
    token_id INTEGER REFERENCES enrollment_tokens(id),
    name VARCHAR(100),
    roll_no VARCHAR(50),
    contact_no VARCHAR(20),
    class VARCHAR(50),
    face_encoding TEXT,
    sample_images JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT NOW()
);

-- Admin Users
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/surveillx

# JWT Secret
JWT_SECRET_KEY=your-super-secret-key

# AWS SES (for emails)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
SES_SENDER_EMAIL=noreply@yourdomain.com

# Development Mode
EMAIL_DEVELOPMENT_MODE=true  # Set false in production
```

---

## 📋 Current Status

### ✅ Completed (Phase 1 & 2)

- [x] Professional dashboard frontend
- [x] User authentication with JWT
- [x] Student management (CRUD)
- [x] Attendance display
- [x] Alert management with filtering
- [x] Live Monitor page with canvas
- [x] Video streaming client (laptop → server)
- [x] WebSocket stream handler
- [x] Face service scaffold
- [x] Student enrollment with camera capture
- [x] Demo data seeding script

### ⏳ Pending (Phase 3 & 4)

- [ ] Face recognition library integration
- [ ] Face encoding during enrollment approval
- [ ] Real-time face matching in video stream
- [ ] Activity detection (running, fighting, loitering)
- [ ] Video clip recording on alerts
- [ ] Email notifications for alerts
- [ ] Mobile responsive design
- [ ] HTTPS/SSL configuration
- [ ] Production deployment guide

---

## 🛠️ Development Notes

### Adding Face Recognition

1. Install dlib and face_recognition:
```bash
# Install cmake first
sudo apt-get install cmake

# Install dlib (takes 10-15 minutes)
pip install dlib

# Install face_recognition
pip install face_recognition
```

2. Update `face_service.py` to use real library instead of mock.

### Activity Detection Integration

The activity detector should implement:
```python
class ActivityDetector:
    def detect(self, frame) -> dict:
        return {
            'type': 'running',  # or fighting, loitering, normal
            'is_abnormal': True,
            'confidence': 0.85,
            'severity': 'high',
            'description': 'Person running in corridor'
        }
```

### Testing WebSocket Streaming

```python
# test_websocket.py
import socketio

sio = socketio.Client()

@sio.on('frame', namespace='/stream')
def on_frame(data):
    print(f"Received frame from camera {data['camera_id']}")

sio.connect('http://localhost:5000', namespaces=['/stream'])
sio.wait()
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not opening on Windows | Try `--camera 1` or `--camera 2` |
| WebSocket connection fails | Check firewall allows port 5000 |
| Login fails | Verify admin user exists in database |
| No video on Live Monitor | Check browser console for WebSocket errors |

---

## 📞 Contact

**Developer:** Vishnu Jadhav  
**Repository:** https://github.com/e7rnal/SurveillX

---

*Last Updated: February 2, 2026*
