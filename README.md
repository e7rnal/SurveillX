# SurveillX

A smart surveillance and attendance system built for educational institutions. It uses face recognition to automate attendance, streams live video over WebSocket, and flags abnormal activities like running, fighting, and loitering.

I built this during my final year of BCA to solve a real problem — manual attendance is slow, proxy attendance is common, and most institutions have no automated way to detect incidents on camera.

---

## What it does

- Marks attendance automatically by recognising registered student faces in a live camera feed
- Streams video from a laptop/camera client to the server over WebSocket
- Detects abnormal activity (running, fighting, loitering) and generates alerts
- Lets students self-enroll via a unique link or QR code
- Gives admins a dashboard to view attendance, review alerts, and manage students
- Sends email notifications for critical alerts via AWS SES

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SocketIO |
| Face recognition | face_recognition library, OpenCV |
| Activity detection | OpenCV (background subtraction, contour analysis) |
| Database | PostgreSQL |
| Auth | JWT (JSON Web Tokens) |
| Video transport | WebSocket |
| Cloud | AWS EC2 (Ubuntu), AWS S3, AWS SES |
| Client | Python stream client (stream_client.py) |

---

## Architecture

```
Laptop Camera
     |
     |  WebSocket
     v
Flask Server (app.py)         <-- runs on AWS EC2 (Ubuntu)
     |
     |-- Face Service          (recognition + matching)
     |-- Activity Detector     (OpenCV-based)
     |-- PostgreSQL            (students, attendance, alerts)
     |-- AWS S3                (frame storage, video clips)
     |-- AWS SES               (email alerts)
     |
     v
Admin Dashboard (browser)
```

The camera client and server are separate. The client captures frames and streams them to the server. The server handles all processing — face matching, activity detection, database writes, alert generation.

---

## Project structure

```
surveillx-backend/
├── app.py                  # entry point, Flask app and SocketIO setup
├── config.py               # environment config loader
├── api/                    # route handlers (auth, students, attendance, alerts)
├── services/               # face service, activity detection, email service
├── client/                 # stream_client.py — runs on the camera machine
│   └── requirements.txt
├── templates/              # HTML templates (admin dashboard, monitor page)
├── static/                 # CSS, JS
├── scripts/                # database seed, demo data generation
└── logs/                   # application logs
```

---

## Setup

**Requirements:** Python 3.9+, PostgreSQL, an AWS account

Clone the repo:

```bash
git clone https://github.com/e7rnal/SurveillX.git
cd SurveillX
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment file and fill in your values:

```bash
cp .env.example .env
```

Environment variables you need to set:

```
DATABASE_URL=postgresql://user:password@localhost:5432/surveillx
JWT_SECRET_KEY=your-secret-key
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
SES_SENDER_EMAIL=
EMAIL_DEVELOPMENT_MODE=true
```

Run the server:

```bash
python app.py
```

---

## Camera client setup

Run this on the machine with the camera (can be a different machine from the server):

```bash
cd client
pip install -r requirements.txt
python stream_client.py --server http://your-server-ip:5000
```

The client captures frames and streams them to the Flask server over WebSocket. The server does all the heavy processing.

---

## AWS deployment

The server runs on an AWS EC2 instance (Ubuntu). Here is roughly how the deployment is set up:

- EC2: Ubuntu 22.04 LTS, g4dn.xlarge (GPU instance for faster face recognition)
- Security groups: inbound rules for port 5000 (Flask), 22 (SSH), 80/443 (HTTP/HTTPS); outbound unrestricted
- S3 bucket: used for storing captured frames and video clips; attached to the EC2 instance via IAM role and AWS CLI
- SES: used to send alert emails; sender email verified in AWS SES console
- Connect to server: `ssh -i your-key.pem ubuntu@your-ec2-public-ip`
- Code deployment: `git pull origin main` on the server after pushing changes

---

## Database tables

| Table | Purpose |
|---|---|
| students | Student records and face encodings |
| attendance_logs | Timestamped attendance entries |
| alerts | Flagged activity events |
| enrollment_tokens | One-time tokens for self-enrollment links |
| pending_enrollments | Enrollment requests awaiting admin approval |
| admin_users | Admin accounts |

---

## Features

**Authentication**
JWT-based login for admin users. Tokens expire and must be refreshed.

**Student management**
Add, update, delete students. Each student record stores a face encoding generated at enrollment time.

**Attendance**
Attendance is marked automatically when a registered face is matched in the live stream. Admins can also view historical records and today's summary.

**Alerts**
When the activity detector flags something — running, fighting, or loitering — an alert is created with a timestamp and optional frame capture. Admins can filter by type and mark alerts as resolved.

**Enrollment**
Admin generates an enrollment link or QR code. Student opens the link, submits their details and a photo. Admin approves or rejects the request. On approval, the face encoding is generated and stored.

---

## Troubleshooting

| Problem | What to check |
|---|---|
| Camera not detected | Try changing the camera index in stream_client.py (0, 1, 2) |
| WebSocket won't connect | Make sure port 5000 is open in your EC2 security group inbound rules |
| Login failing | Verify the admin user exists in the admin_users table |
| No video in dashboard | Open browser dev tools console and check for WebSocket errors |
| Face not being recognised | Check that the student's face encoding was generated correctly at enrollment |
| AWS SES emails not sending | Confirm the sender email is verified in SES and EMAIL_DEVELOPMENT_MODE is false |
