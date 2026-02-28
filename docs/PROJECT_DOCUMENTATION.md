# SurveillX — AI-Powered Smart Surveillance System

## Project Documentation

---

### Table of Contents

1. [Introduction & Abstract](#1-introduction--abstract)
2. [Problem Statement & Motivation](#2-problem-statement--motivation)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Features Walkthrough](#5-features-walkthrough)
6. [AI/ML Pipeline](#6-aiml-pipeline)
7. [User Guide — How to Use](#7-user-guide--how-to-use)
8. [Benefits & Impact](#8-benefits--impact)
9. [Teacher Q&A — Anticipated Questions](#9-teacher-qa--anticipated-questions)
10. [Future Scope](#10-future-scope)
11. [References](#11-references)

---

## 1. Introduction & Abstract

**SurveillX** is an AI-powered smart surveillance and attendance management system designed for educational institutions. It combines real-time face recognition, pose estimation, and activity detection to automate attendance tracking and classroom behavior monitoring — completely hands-free.

### Abstract

Traditional attendance systems rely on manual roll calls or biometric scanners, both of which are time-consuming, error-prone, and disruptive. SurveillX replaces these with a camera-based solution that:

- **Automatically identifies students** using face recognition (InsightFace Buffalo_L model)
- **Detects student activities** using pose estimation (YOLOv8/YOLO11) and an LSTM neural network
- **Generates real-time alerts** for suspicious or abnormal behavior
- **Provides a comprehensive dashboard** with analytics, attendance reports, and system health monitoring

The system runs entirely on a local server with GPU acceleration (NVIDIA Tesla T4), ensuring data privacy while delivering real-time performance.

---

## 2. Problem Statement & Motivation

### The Problem

Educational institutions face several challenges with traditional attendance and monitoring systems:

| Challenge | Traditional Approach | Impact |
|-----------|---------------------|--------|
| **Manual Roll Call** | Teacher calls names one by one | Wastes 5–10 minutes per class; students can mark proxy attendance |
| **Biometric Scanners** | Fingerprint/RFID at door | Queue bottleneck; hardware maintenance; easily bypassed |
| **Classroom Monitoring** | Physical supervision only | Teachers cannot monitor all students simultaneously |
| **Report Generation** | Manual spreadsheets | Time-consuming, error-prone, delayed insights |
| **Alert Systems** | No automated alerts | Incidents go unnoticed until reported |

### Our Motivation

We aimed to build a system that:
1. **Eliminates proxy attendance** — Face recognition ensures only the actual student is marked present
2. **Saves class time** — Attendance is captured automatically within seconds of class starting
3. **Enhances safety** — Real-time activity detection identifies potential incidents (fights, falls, unusual behavior)
4. **Provides actionable data** — Dashboards give administrators instant visibility into attendance patterns and alerts
5. **Preserves privacy** — All processing happens locally on-premises; no data leaves the institution's network

---

## 3. System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SurveillX System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  Camera   │───▶│  Stream      │───▶│   AI Processing       │  │
│  │  Feeds    │    │  Handler     │    │                       │  │
│  └──────────┘    └──────────────┘    │  ┌─────────────────┐  │  │
│                                      │  │ Face Detection  │  │  │
│  ┌──────────┐    ┌──────────────┐    │  │ (InsightFace)   │  │  │
│  │  Web UI   │◀──│  Flask API   │◀──▶│  ├─────────────────┤  │  │
│  │ (Browser) │    │  Server      │    │  │ Pose Estimation │  │  │
│  └──────────┘    └──────────────┘    │  │ (YOLOv8-Pose)   │  │  │
│                       │              │  ├─────────────────┤  │  │
│                       │              │  │ Activity LSTM   │  │  │
│                  ┌────▼─────┐        │  │ (Custom Model)  │  │  │
│                  │ Database │        │  └─────────────────┘  │  │
│                  │ (SQLite) │        └───────────────────────┘  │
│                  └──────────┘                                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              GPU: NVIDIA Tesla T4 (16GB VRAM)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Module Structure

```
surveillx-backend/
├── app.py                    # Main Flask application entry point
├── config.py                 # Configuration (database, JWT keys)
├── api/                      # REST API endpoints
│   ├── auth.py               # Login / Registration
│   ├── enrollment.py         # Student enrollment & face registration
│   ├── students.py           # Student management (CRUD)
│   ├── attendance.py         # Attendance records & reports
│   ├── alerts.py             # Alert management
│   ├── cameras.py            # Camera stream configuration
│   ├── detection.py          # Real-time detection demo page
│   ├── system_health.py      # Server monitoring API
│   └── stats.py              # Dashboard statistics
├── engines/                  # AI/ML processing engines
│   ├── facial_recognition/   # Face detection, encoding, matching
│   │   ├── detector.py       # Face detection (InsightFace)
│   │   ├── encoder.py        # Face encoding (512-dim vectors)
│   │   └── matcher.py        # Cosine similarity matching
│   └── activity_detection/   # Activity/behavior classification
│       ├── detector.py       # Pose estimation (YOLOv8-Pose)
│       ├── classifier.py     # Activity classification (rule + LSTM)
│       ├── lstm_model.py     # LSTM neural network architecture
│       ├── rules.py          # Rule-based activity rules
│       └── tracker.py        # Person tracking across frames
├── services/                 # Business logic services
│   ├── db_manager.py         # Database operations
│   ├── face_service.py       # Face enrollment pipeline
│   ├── ml_worker.py          # Background ML processing
│   ├── stream_handler.py     # Camera stream management
│   ├── recognition_handler.py # Face recognition pipeline
│   ├── activity_detector.py  # Activity detection integration
│   └── email_service.py      # Email notification (AWS SES)
├── static/                   # Frontend assets
│   ├── css/style.css         # Global stylesheet (dark theme)
│   └── js/app.js             # Single-page application logic
├── templates/                # HTML templates
│   ├── index.html            # Main SPA shell
│   ├── login.html            # Login page
│   └── partials/             # Page-specific templates
└── docs/                     # Documentation
```

---

## 4. Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | **Flask 3.x** | REST API server, routing, templating |
| Authentication | **Flask-JWT-Extended** | JWT token-based auth |
| Real-time | **Flask-SocketIO** | WebSocket for live updates |
| Database | **SQLite** | Lightweight relational database |
| Email | **AWS SES (boto3)** | Alert notifications via email |

### AI/ML
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Face Detection | **InsightFace (Buffalo_L)** | Detecting faces in video frames |
| Face Encoding | **ArcFace (via InsightFace)** | 512-dimensional face embeddings |
| Face Matching | **Cosine Similarity** | Comparing face vectors for identity |
| Pose Estimation | **YOLOv8s-Pose / YOLO11n-Pose** | 17-keypoint body pose detection |
| Activity Detection | **Custom LSTM Network** | Temporal activity classification |
| Object Detection | **YOLOv8n** | General person detection |

### Frontend
| Component | Technology | Purpose |
|-----------|-----------|---------|
| UI Framework | **Vanilla JavaScript (SPA)** | Single-page dynamic application |
| Styling | **Custom CSS (Dark Theme)** | Professional dark-mode interface |
| Charts | **Chart.js** | Attendance trends, alert distributions |
| Icons | **Font Awesome 6** | UI icons throughout the app |
| Font | **Inter (Google Fonts)** | Modern, readable typography |

### Infrastructure
| Component | Technology | Purpose |
|-----------|-----------|---------|
| GPU | **NVIDIA Tesla T4 (16GB)** | AI model inference acceleration |
| Server | **Ubuntu 22.04 LTS** | Host operating system |
| Python | **Python 3.10** | Programming language runtime |
| Process Manager | **systemd** | Service management |

---

## 5. Features Walkthrough

### 5.1 Dashboard Overview

The dashboard is the central hub of SurveillX. Upon login, users immediately see:

- **Stat Cards** — Today's attendance count, active cameras, recent alerts, total students, enrolled faces
- **System Health Panel** — Real-time monitoring of CPU, Memory, GPU usage, storage volumes, AI engine status, network I/O, and server information
- **Charts** — Attendance trend over the last 7 days (line chart) and alert distribution (pie chart)
- **Recent Alerts** — Latest security/behavioral alerts with severity badges
- **Attendance Summary** — Quick view of today's present/absent students
- **Quick Actions** — One-click buttons for common tasks (enroll student, view reports, settings)

### 5.2 Student Management

A full CRUD interface for managing students:

- **Add Student** — Name, roll number, department, year, contact details
- **Bulk Import** — Upload CSV file to import multiple students at once
- **Search & Filter** — Find students by name, roll number, or department
- **Edit/Delete** — Modify student details or remove from system
- **View Profile** — See student's attendance history, face enrollment status, and associated alerts

### 5.3 Face Enrollment

The face enrollment page provides a guided process:

1. **Select Student** — Choose from the registered student list
2. **Capture Faces** — Take photos via webcam or upload existing images
3. **Multiple Angles** — System recommends capturing 3–5 images from different angles for robust recognition
4. **Encoding** — Face embeddings are automatically generated and stored
5. **Verification** — System shows enrollment success and face quality score

### 5.4 Live Monitor

Real-time surveillance panel showing:

- **Multi-Camera View** — Up to 3 simultaneous camera feeds in a grid layout
- **Camera Controls** — Start/stop streams, switch cameras
- **WebRTC Streaming** — Low-latency video with peer-to-peer connections
- **Detection Overlay** — Bounding boxes and labels on detected faces and poses
- **Live Stats** — Active detections count, frame rate, processing status

### 5.5 Detection Test Page

A demonstration page for testing AI detection capabilities:

- **Video Upload** — Upload test videos or select demo clips
- **Face Recognition** — See identified students with confidence scores
- **Activity Detection** — Observe pose estimation skeletons and activity labels
- **Side-by-Side View** — Original video alongside annotated detection output
- **Activity Labels** — Real-time classification: sitting, standing, hand_raise, phone_use, writing, etc.

### 5.6 Attendance Management

Comprehensive attendance tracking:

- **Automatic Marking** — Attendance captured automatically when faces are recognized on camera
- **Daily Reports** — View present/absent/late students for any date
- **Export** — Download attendance records as reports
- **Manual Override** — Authorized users can manually adjust attendance records
- **History** — Full attendance history per student with timestamps

### 5.7 Alert System

Real-time behavioral and security alerts:

- **Alert Types** — Unauthorized person, suspicious activity, unusual behavior
- **Severity Levels** — High (red), Medium (yellow), Low (blue)
- **Email Notifications** — Automatic email alerts to administrators via AWS SES
- **Alert History** — Browse past alerts with filters by date, type, and severity
- **Resolution Tracking** — Mark alerts as reviewed/resolved

### 5.8 Settings

System configuration page:

- **Email Settings** — Configure notification recipients and alert preferences
- **Camera Settings** — Stream URL configuration, resolution settings
- **Detection Settings** — Adjust recognition thresholds and sensitivity
- **User Management** — Admin user configuration

---

## 6. AI/ML Pipeline

### 6.1 Face Recognition Pipeline

```
Camera Frame
    │
    ▼
┌──────────────────────┐
│  Face Detection       │  InsightFace (Buffalo_L)
│  ─ Locate all faces  │  → Returns bounding boxes + landmarks
│    in the frame      │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Face Encoding        │  ArcFace Model
│  ─ Extract 512-dim   │  → Converts face to numerical vector
│    embedding vector  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Face Matching        │  Cosine Similarity
│  ─ Compare against   │  → Returns matched student + confidence
│    enrolled database │  → Threshold: 0.4 (adjustable)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Attendance Record    │  Database Insert
│  ─ Mark student as   │  → Deduplication: 10-second window
│    present           │
└──────────────────────┘
```

**Key Technical Details:**
- **Model**: InsightFace Buffalo_L (Large) — State-of-the-art face recognition
- **Embedding Size**: 512 dimensions per face
- **Matching Method**: Cosine similarity between face vectors
- **Threshold**: 0.4 (lower = stricter matching; higher = more lenient)
- **Deduplication**: Same student won't be marked twice within 10 seconds
- **GPU Acceleration**: CUDA-enabled inference on NVIDIA Tesla T4

### 6.2 Activity Detection Pipeline

```
Camera Frame
    │
    ▼
┌──────────────────────┐
│  Person Detection     │  YOLOv8n
│  ─ Locate all people │  → Bounding boxes
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Pose Estimation      │  YOLOv8s-Pose / YOLO11n-Pose
│  ─ Extract 17 body   │  → Keypoints: nose, eyes, shoulders,
│    keypoints         │    elbows, wrists, hips, knees, ankles
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Person Tracking      │  IoU-based Tracker
│  ─ Maintain identity │  → Consistent person IDs across frames
│    across frames     │
└──────────┬───────────┘
           │
           ├──────────────────────────┐
           ▼                          ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Rule-Based Analysis  │  │  LSTM Classifier      │
│  ─ Geometric rules   │  │  ─ Temporal patterns  │
│  ─ Joint angles      │  │  ─ 30-frame sequences │
│  ─ Instant detection │  │  ─ Learned behaviors  │
└──────────┬───────────┘  └──────────┬───────────┘
           │                          │
           └──────────┬───────────────┘
                      ▼
┌──────────────────────────────────────┐
│  Final Classification                 │
│  ─ Combine rule + LSTM predictions   │
│  ─ Confidence-weighted fusion        │
│  ─ Generate alerts if suspicious     │
└──────────────────────────────────────┘
```

**Detected Activities:**

| Activity | Detection Method | Description |
|----------|-----------------|-------------|
| **Sitting** | Rule + LSTM | Normal seated posture |
| **Standing** | Rule + LSTM | Upright standing position |
| **Hand Raise** | Rule + LSTM | Arm raised above shoulder level |
| **Phone Use** | LSTM | Hand near ear/face in phone-like position |
| **Writing** | LSTM | Leaning forward with arm movement |
| **Sleeping** | Rule + LSTM | Head down on desk posture |
| **Fighting** | Rule + LSTM | Aggressive arm movements between people |
| **Falling** | Rule | Sudden vertical position change |

**LSTM Model Architecture:**
- **Input**: Sequence of 30 frames × 34 features (17 keypoints × 2 coordinates)
- **Hidden Layers**: 2 LSTM layers (128 units each) with dropout (0.3)
- **Output**: Probability distribution over activity classes
- **Training**: Supervised learning on pose sequence datasets
- **File**: `engines/activity_detection/activity_lstm.pt`

### 6.3 How the Models Work Together

During live surveillance, the system processes each camera frame through:

1. **Face Recognition** — Identifies who is in the frame → marks attendance
2. **Pose Estimation** — Detects body poses of all people → enables activity detection
3. **Activity Classification** — Analyzes pose sequences → identifies activities
4. **Alert Generation** — If abnormal activity detected → creates an alert with severity level

All inference runs on the GPU simultaneously, achieving real-time processing at 15–30 FPS depending on the complexity.

---

## 7. User Guide — How to Use

### Step 1: Access the System

1. Open a web browser (Chrome recommended)
2. Navigate to the SurveillX URL (e.g., `http://<server-ip>:5000`)
3. You will see the login page

### Step 2: Login

1. Enter your username and password
2. Click **Sign In**
3. Default credentials: `admin` / `admin123`
4. You will be redirected to the Dashboard

### Step 3: Enroll Students

Before the system can recognize students, they must be enrolled:

1. **Navigate to Students** → Click "Students" in the sidebar
2. **Add a Student** → Click "Add Student" button → Fill in name, roll number, department, year
3. **Enroll Face** → Go to the **Enrollment** page → Select the student → Capture 3–5 photos from different angles via webcam or upload photos
4. **Verify** → The system confirms successful face encoding

**Tips for Best Results:**
- Ensure good lighting when capturing face photos
- Capture from slightly different angles (front, slight left, slight right)
- Remove glasses/masks if they won't normally be worn
- Use clear, recent photos

### Step 4: Configure Cameras

1. Go to **Settings** → Camera Configuration
2. Enter the RTSP URL of your IP camera (e.g., `rtsp://192.168.1.100:554/stream`)
3. Give the camera a name and location
4. Click **Save**

### Step 5: Start Live Monitoring

1. Navigate to the **Live Monitor** page
2. Select a configured camera from the dropdown
3. Click **Start Stream**
4. The system will begin:
   - Detecting and recognizing faces
   - Estimating body poses
   - Classifying activities
   - Marking attendance automatically
5. Recognized students appear with green bounding boxes and their names

### Step 6: View Attendance

1. Go to the **Attendance** page
2. Select a date range
3. View the **Present** and **Absent** tabs
4. See each student's check-in time
5. Export reports as needed

### Step 7: Monitor Alerts

1. Navigate to the **Alerts** page
2. View alerts sorted by severity (High → Medium → Low)
3. Each alert shows: timestamp, type, description, and associated camera
4. Click on an alert for details
5. Mark as reviewed when addressed

### Step 8: Check System Health

On the **Dashboard**, the System Health panel shows:
- CPU, Memory, and GPU utilization gauges
- Storage volume usage (Root + External drives)
- GPU temperature and power draw
- AI engine status (Face Detection, Pose Estimation)
- Network I/O and server information

---

## 8. Benefits & Impact

### For Teachers

| Benefit | How |
|---------|-----|
| **Save 5–10 minutes per class** | Attendance is automatic — no roll call needed |
| **Eliminate proxy attendance** | Face recognition ensures only the actual student is marked |
| **Focus on teaching** | No time wasted on administrative tasks |
| **Real-time class insights** | See who is attentive, who is sleeping, who is on their phone |
| **Instant alerts** | Get notified immediately of disruptive behavior |

### For Administrators

| Benefit | How |
|---------|-----|
| **Comprehensive attendance data** | Access historical records for any student, any date |
| **Automated reports** | Generate attendance reports without manual work |
| **Safety monitoring** | Detect fights, falls, or unauthorized persons |
| **Data-driven decisions** | Analytics dashboards reveal attendance patterns |
| **Reduced operational cost** | No need for biometric hardware or manual data entry |

### For Students

| Benefit | How |
|---------|-----|
| **No queue at biometric scanner** | Just walk into class — system recognizes automatically |
| **Fair attendance** | No disputes over missed roll calls |
| **Privacy-first** | All data stays on local servers, not cloud |

### Comparison with Existing Systems

| Feature | Manual Roll Call | Biometric Scanner | SurveillX |
|---------|:---:|:---:|:---:|
| Time to mark attendance | 5–10 min | 1–3 min (queue) | **< 5 seconds** |
| Proxy prevention | ❌ | ✅ | ✅ |
| No physical contact | ✅ | ❌ | ✅ |
| Behavior monitoring | ❌ | ❌ | ✅ |
| Real-time alerts | ❌ | ❌ | ✅ |
| Analytics dashboard | ❌ | Limited | ✅ |
| Cost per classroom | Low | High | **Medium** |

---

## 9. Teacher Q&A — Anticipated Questions

### Technical Questions

**Q1: What AI/ML models does SurveillX use?**

> SurveillX uses three main AI models:
> 1. **InsightFace Buffalo_L** — A state-of-the-art face recognition model that detects and encodes faces into 512-dimensional vectors for identity matching
> 2. **YOLOv8s-Pose / YOLO11n-Pose** — YOLO-based pose estimation models that detect 17 body keypoints for activity analysis
> 3. **Custom LSTM Network** — A Long Short-Term Memory neural network trained to classify activities from temporal pose sequences (30 frames)

**Q2: How does face recognition work in this system?**

> When a student enrolls, the system captures their face photos and converts each into a 512-dimensional numerical vector (embedding) using InsightFace's ArcFace model. These vectors are stored in the database. During live surveillance, every detected face is similarly encoded, and the system compares the new vector against all stored vectors using **cosine similarity**. If the similarity score exceeds the threshold (0.4), the student is identified and their attendance is marked automatically.

**Q3: What is the accuracy of the face recognition?**

> InsightFace Buffalo_L achieves **99.7%+** accuracy on standard face recognition benchmarks (LFW dataset). In practice, with good lighting and clear face visibility, SurveillX achieves high accuracy. The recognition threshold (0.4) is configurable to balance between false acceptances and false rejections.

**Q4: How does the LSTM activity detection work?**

> The LSTM (Long Short-Term Memory) network is a type of recurrent neural network designed to learn patterns in sequential data. In SurveillX:
> 1. The YOLOv8-Pose model extracts 17 body keypoints from each video frame
> 2. Keypoints are normalized relative to the person's bounding box
> 3. Sequences of 30 consecutive frames are fed into the LSTM
> 4. The LSTM learns temporal patterns (e.g., repeated arm movement = writing, head dropping gradually = sleeping)
> 5. Output is a probability distribution over activity classes
>
> This temporal approach is more robust than single-frame analysis because activities are defined by movement over time, not static poses.

**Q5: Why did you use a hybrid approach (rules + LSTM) for activity detection?**

> We use a hybrid system for reliability:
> - **Rule-based analysis** handles clear-cut activities that can be defined geometrically (e.g., hand raise = wrist above shoulder, standing = hip-to-ankle angle > 160°). These are fast and interpretable.
> - **LSTM** handles complex, temporal activities that need motion context (e.g., phone use, writing, sleeping). These require learning from training data.
> - The **final classification** fuses both predictions using confidence-weighted voting, giving the best overall accuracy.

**Q6: What is the system architecture? Is it client-server or monolithic?**

> SurveillX follows a **client-server architecture** with a modular backend:
> - **Backend**: Python Flask server handling REST APIs, authentication (JWT), and real-time communication (WebSocket)
> - **Frontend**: Single-page application (SPA) served by Flask, built with vanilla JavaScript
> - **AI Engines**: Separate Python modules for face recognition and activity detection, running on GPU
> - **Database**: SQLite for data persistence (students, attendance, alerts)
> - **Communication**: RESTful HTTP APIs + WebSocket for real-time updates

**Q7: How do you handle real-time performance while running multiple AI models?**

> Several optimizations enable real-time processing:
> 1. **GPU Acceleration**: All models run on NVIDIA Tesla T4 (16GB VRAM) using CUDA
> 2. **Batch Processing**: Frames are processed in batches to maximize GPU utilization
> 3. **In-Memory Caching**: Face encodings are cached in memory for fast matching
> 4. **Deduplication**: A 10-second window prevents redundant processing for the same person
> 5. **Async Processing**: Background workers handle heavy ML tasks without blocking the web server

**Q8: What database are you using and why?**

> We use **SQLite** for simplicity and portability. It's a serverless database that stores everything in a single file, making deployment easy with no separate database server needed. For a single-institution deployment, SQLite handles the load efficiently. For larger deployments, the `DBManager` class abstracts database operations, making migration to PostgreSQL straightforward.

### Architecture & Design Questions

**Q9: Why Flask instead of Django or FastAPI?**

> Flask was chosen for its:
> - **Simplicity**: Lightweight framework ideal for custom architectures
> - **Flexibility**: No opinionated structure; we organized modules to match our AI pipeline
> - **SocketIO Support**: Flask-SocketIO provides robust WebSocket integration for real-time feeds
> - **Template Integration**: Easy to serve the SPA frontend alongside the API
> - **Ecosystem**: Rich ecosystem of extensions (JWT, CORS, etc.)

**Q10: How is the system deployed? Can it work without internet?**

> SurveillX is designed for **on-premises deployment**:
> - All AI models run locally on the server's GPU
> - No cloud API calls required for detection, recognition, or attendance
> - The only internet dependency is email alerts (AWS SES), which is optional
> - The system can run entirely offline within a campus LAN
> - Deployment is managed via systemd services on Ubuntu

**Q11: How do you ensure data privacy and security?**

> Privacy is a core design principle:
> 1. **Local Processing**: All face recognition and activity detection runs on the local server — no data sent to cloud
> 2. **JWT Authentication**: All API endpoints are protected with JSON Web Token authentication
> 3. **Password Hashing**: User passwords are hashed before storage
> 4. **Session Management**: Tokens expire after a configurable period
> 5. **Access Control**: Only authenticated administrators can access the system
> 6. **On-Premises Storage**: All images, encodings, and attendance data stay on the local server

**Q12: What happens if the system misidentifies someone or fails to detect?**

> The system includes several safeguards:
> - **Adjustable Threshold**: The face matching threshold (0.4) can be tuned — lower for stricter matching, higher for more lenient
> - **Manual Override**: Administrators can manually correct attendance records
> - **Unknown Person Alerts**: Faces not matching any enrolled student are flagged as "Unknown Person"
> - **Confidence Scores**: Every match includes a confidence percentage so administrators can judge reliability
> - **Multi-Frame Verification**: The system confirms detections across multiple frames before marking attendance

### Practical Questions

**Q13: What hardware is needed to run SurveillX?**

> Minimum requirements:
> - **GPU**: NVIDIA GPU with CUDA support (GTX 1060 or better; Tesla T4 recommended)
> - **RAM**: 16 GB minimum
> - **CPU**: 4+ cores (modern Intel/AMD)
> - **Storage**: 50 GB for system + models
> - **Camera**: IP camera with RTSP support (720p minimum)
> - **OS**: Ubuntu 20.04 or later

**Q14: How many cameras can the system handle simultaneously?**

> On a Tesla T4 GPU, the system comfortably handles **2–3 simultaneous camera feeds** at 15–20 FPS with both face recognition and activity detection active. Scaling to more cameras would require multiple GPUs or dedicated hardware.

**Q15: What are the limitations of the current system?**

> Current known limitations include:
> 1. **Lighting Sensitivity**: Face recognition accuracy decreases in very poor lighting conditions
> 2. **Occlusion**: Partial face coverage (masks, hand covering face) can reduce recognition accuracy
> 3. **Camera Angle**: Best performance with front-facing cameras at face height
> 4. **Scale**: Designed for single-institution use; multi-branch would need modifications
> 5. **Activity Classes**: Currently supports a fixed set of activities; adding new ones requires retraining the LSTM model

**Q16: What is the difference between your system and commercial products like Verkada or Hikvision?**

> Key differentiators:
> - **Open Source**: SurveillX is built with open-source AI models, making it free from vendor lock-in
> - **Education-Focused**: Built specifically for attendance and classroom behavior, not general surveillance
> - **Privacy-First**: No cloud dependency; data stays on-premises
> - **Customizable**: The LSTM model can be retrained for institution-specific activities
> - **Cost-Effective**: Uses standard hardware + open-source software, significantly cheaper than commercial alternatives

**Q17: Can the LSTM model be retrained with new data?**

> Yes. The system includes a full retraining pipeline:
> - `engines/activity_detection/train.py` — Training script with configurable hyperparameters
> - `engines/activity_detection/retrain.py` — Incremental retraining on new data
> - New pose sequence data can be collected from camera feeds and labeled for training
> - The trained model (`activity_lstm.pt`) is automatically loaded by the classifier

---

## 10. Future Scope

SurveillX has a clear path for future enhancements:

1. **Mobile App** — React Native / Flutter companion app for teachers to view attendance and alerts on their phones

2. **Multi-Camera Tracking** — Track individuals across multiple cameras using Re-Identification (ReID) models

3. **Emotion Detection** — Add facial expression analysis to gauge student engagement and attention levels

4. **Automated Timetable Integration** — Connect with university timetable systems to automatically associate attendance with specific courses

5. **Cloud Dashboard** — Optional cloud-based analytics dashboard for multi-campus institutions while keeping processing local

6. **Edge Deployment** — Port models to NVIDIA Jetson devices for lightweight, camera-attached processing

7. **Voice Integration** — Add speech detection to identify students asking questions or making noise

8. **Parent Notifications** — Automated SMS/email to parents when student is absent

---

## 11. References

### Frameworks & Libraries

1. **Flask** — Pallets Projects. https://flask.palletsprojects.com/
2. **InsightFace** — Deng, J., et al. "ArcFace: Additive Angular Margin Loss for Deep Face Recognition." CVPR 2019. https://github.com/deepinsight/insightface
3. **Ultralytics YOLO** — Jocher, G., et al. "YOLOv8 — You Only Look Once." https://github.com/ultralytics/ultralytics
4. **PyTorch** — Paszke, A., et al. "PyTorch: An Imperative Style, High-Performance Deep Learning Library." NeurIPS 2019. https://pytorch.org/
5. **Chart.js** — https://www.chartjs.org/
6. **Font Awesome** — https://fontawesome.com/
7. **Flask-SocketIO** — https://flask-socketio.readthedocs.io/

### Research Papers

8. **ArcFace**: Deng, J., Guo, J., Xue, N., & Zafeiriou, S. (2019). "ArcFace: Additive Angular Margin Loss for Deep Face Recognition." IEEE Conference on Computer Vision and Pattern Recognition (CVPR).

9. **YOLO**: Redmon, J., & Farhadi, A. (2018). "YOLOv3: An Incremental Improvement." arXiv preprint arXiv:1804.02767.

10. **LSTM**: Hochreiter, S., & Schmidhuber, J. (1997). "Long Short-Term Memory." Neural Computation, 9(8), 1735–1780.

11. **Pose Estimation**: Cao, Z., et al. (2019). "OpenPose: Realtime Multi-Person 2D Pose Estimation using Part Affinity Fields." IEEE TPAMI.

---

*This document is part of the SurveillX project by Team SurveillX. All rights reserved.*
