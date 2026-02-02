# SurveillX - Development Roadmap

This document outlines the remaining development phases and implementation details for completing the SurveillX system.

---

## Phase 3: Face Recognition Integration

### Objective
Enable real-time face recognition in video streams for automatic attendance marking.

### Prerequisites
```bash
# Install on server (Ubuntu)
sudo apt-get update
sudo apt-get install -y cmake build-essential
pip install dlib face_recognition
```

### Implementation Steps

#### 3.1 Update Face Service

File: `services/face_service.py`

```python
# Replace mock implementation with real face_recognition library
import face_recognition
import numpy as np

class FaceService:
    def __init__(self, db_manager):
        self.db = db_manager
        self.known_faces = []
        self.known_ids = []
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load face encodings from database"""
        students = self.db.get_all_students()
        for student in students:
            if student.get('face_encoding'):
                encoding = np.frombuffer(
                    base64.b64decode(student['face_encoding']),
                    dtype=np.float64
                )
                self.known_faces.append(encoding)
                self.known_ids.append(student['id'])
    
    def detect_and_recognize(self, frame):
        """Detect faces and match to known students"""
        # Convert BGR to RGB
        rgb_frame = frame[:, :, ::-1]
        
        # Find faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        results = []
        for encoding, location in zip(face_encodings, face_locations):
            # Compare to known faces
            matches = face_recognition.compare_faces(self.known_faces, encoding)
            
            if True in matches:
                match_index = matches.index(True)
                student_id = self.known_ids[match_index]
                results.append({
                    'student_id': student_id,
                    'location': location,
                    'confidence': 0.9
                })
            else:
                results.append({
                    'student_id': None,
                    'location': location,
                    'confidence': 0
                })
        
        return results
```

#### 3.2 Generate Face Encoding During Enrollment Approval

File: `api/enrollment.py`

```python
@enrollment_bp.route('/<int:enrollment_id>/approve', methods=['PUT'])
@jwt_required()
def approve_enrollment(enrollment_id):
    """Approve enrollment and generate face encoding"""
    try:
        db = current_app.db
        enrollment = db.get_pending_enrollment_by_id(enrollment_id)
        
        if not enrollment:
            return jsonify({"error": "Enrollment not found"}), 404
        
        # Generate face encoding from sample images
        face_service = current_app.face_service
        sample_images = enrollment.get('sample_images', [])
        
        if sample_images:
            encoding = face_service.generate_encoding_from_images(sample_images)
            if encoding is not None:
                # Save encoding with student
                student_id = db.approve_enrollment(enrollment_id, face_encoding=encoding)
            else:
                return jsonify({"error": "Could not generate face encoding"}), 400
        
        return jsonify({"message": "Enrollment approved", "student_id": student_id})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### 3.3 Initialize Face Service in app.py

```python
# In app.py after app creation
from services.face_service import FaceService

face_service = FaceService(db)
stream_handler.set_face_service(face_service)
```

---

## Phase 4: Activity Detection

### Objective
Detect abnormal activities like running, fighting, and loitering.

### Implementation Approach

Option 1: **MediaPipe + Custom Rules**
- Use MediaPipe for pose estimation
- Calculate movement velocity for running detection
- Detect proximity for fighting detection

Option 2: **Pre-trained Action Recognition Model**
- Use models like SlowFast or I3D
- Train on custom campus footage

### Implementation Steps

#### 4.1 Create Activity Detector Service

File: `services/activity_detector.py`

```python
import cv2
import numpy as np
from collections import deque

class ActivityDetector:
    def __init__(self):
        self.frame_history = deque(maxlen=30)  # 1 second at 30fps
        self.person_positions = {}
        self.loitering_threshold = 60  # seconds
        self.running_velocity = 2.5  # m/s threshold
        
    def detect(self, frame):
        """Detect activity in frame"""
        self.frame_history.append(frame)
        
        # Get current detections
        activities = {
            'type': 'Normal',
            'is_abnormal': False,
            'confidence': 0,
            'severity': 'low',
            'description': ''
        }
        
        # Check for running
        if self._detect_running():
            activities = {
                'type': 'running',
                'is_abnormal': True,
                'confidence': 0.8,
                'severity': 'medium',
                'description': 'Person running detected'
            }
        
        # Check for fighting (close proximity + sudden movements)
        if self._detect_fighting():
            activities = {
                'type': 'fighting',
                'is_abnormal': True,
                'confidence': 0.85,
                'severity': 'high',
                'description': 'Physical altercation detected'
            }
        
        # Check for loitering
        if self._detect_loitering():
            activities = {
                'type': 'loitering',
                'is_abnormal': True,
                'confidence': 0.7,
                'severity': 'low',
                'description': 'Prolonged presence in area'
            }
        
        return activities
    
    def _detect_running(self):
        """Detect running based on motion velocity"""
        # Implementation using optical flow or pose estimation
        pass
    
    def _detect_fighting(self):
        """Detect fighting based on proximity and sudden movement"""
        # Implementation using pose estimation
        pass
    
    def _detect_loitering(self):
        """Detect loitering based on prolonged presence"""
        # Implementation using person tracking
        pass
```

#### 4.2 Integrate with Stream Handler

```python
# In app.py
from services.activity_detector import ActivityDetector

activity_detector = ActivityDetector()
stream_handler.set_activity_detector(activity_detector)
```

---

## Phase 5: Video Clip Recording

### Objective
Record video clips when alerts are triggered and save for review.

### Implementation Steps

#### 5.1 Create Clip Recorder Service

File: `services/clip_recorder.py`

```python
import cv2
import os
from datetime import datetime

class ClipRecorder:
    def __init__(self, output_dir='clips'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.buffer = []
        self.buffer_size = 150  # 5 seconds at 30fps
        
    def add_frame(self, frame):
        """Add frame to buffer"""
        self.buffer.append(frame)
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)
    
    def save_clip(self, alert_id, pre_seconds=5, post_seconds=5):
        """Save video clip for alert"""
        filename = f"alert_{alert_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        
        # Get frames from buffer
        frames = list(self.buffer)
        
        if not frames:
            return None
        
        # Write video
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filepath, fourcc, 30.0, (w, h))
        
        for frame in frames:
            out.write(frame)
        
        out.release()
        return filepath
```

---

## Phase 6: Production Deployment

### 6.1 HTTPS Configuration (Nginx + Let's Encrypt)

```bash
# Install Nginx
sudo apt-get install nginx

# Install Certbot
sudo snap install --classic certbot

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Nginx config for reverse proxy
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
    
    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 6.2 Systemd Service

File: `/etc/systemd/system/surveillx.service`

```ini
[Unit]
Description=SurveillX Backend
After=network.target postgresql.service

[Service]
User=ubuntu
WorkingDirectory=/opt/dlami/nvme/surveillx-backend
Environment="PATH=/opt/dlami/nvme/surveillx-backend/venv/bin"
ExecStart=/opt/dlami/nvme/surveillx-backend/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable surveillx
sudo systemctl start surveillx
sudo systemctl status surveillx
```

### 6.3 Production Checklist

- [ ] Set `EMAIL_DEVELOPMENT_MODE=false` in .env
- [ ] Configure real AWS SES credentials
- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring (e.g., Prometheus/Grafana)
- [ ] Load test WebSocket connections
- [ ] Security audit (OWASP guidelines)

---

## Useful Commands

```bash
# Check app status
curl http://localhost:5000/health

# View logs
tail -f logs/app.log

# Restart app
sudo systemctl restart surveillx

# Database backup
pg_dump surveillx > backup_$(date +%Y%m%d).sql

# Seed demo data
python scripts/seed_demo_data.py
```

---

## Testing Checklist

- [ ] Login/logout works
- [ ] Dashboard loads with stats
- [ ] Students CRUD operations
- [ ] Attendance displays correctly
- [ ] Alerts filter works
- [ ] Live Monitor shows video stream
- [ ] Student enrollment with photos
- [ ] Enrollment approval/rejection
- [ ] Face recognition marks attendance (Phase 3)
- [ ] Activity detection creates alerts (Phase 4)

---

*Document Version: 1.0 | Last Updated: February 2, 2026*
