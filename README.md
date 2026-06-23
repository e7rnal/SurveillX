# SurveillX

Smart surveillance and attendance system for educational institutions using face recognition and activity detection.

## Overview

SurveillX provides:

* Automatic attendance using face recognition
* Live video streaming from cameras
* Detection of abnormal activities such as running, fighting, and loitering
* Student self-enrollment through links or QR codes
* Alert generation for suspicious events

## Architecture

```
Laptop Camera (stream_client)
           |
           | WebSocket
           v
      Flask Server (app.py)
           |
    ------------------------
    |          |          |
Face Service PostgreSQL Frontend
```

## Project Structure

```
surveillx-backend/
├── app.py
├── config.py
├── api/
├── services/
├── client/
├── templates/
├── static/
├── scripts/
└── logs/
```

## Installation

Clone the repository:

```bash
git clone https://github.com/e7rnal/SurveillX.git
cd SurveillX
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Start the server:

```bash
python app.py
```

## Client Setup

```bash
cd client
pip install -r requirements.txt
python stream_client.py --server http://your-server-ip:5000
```

## Main Components

### Authentication

* User login with JWT authentication.

### Student Management

* Add students
* Update student information
* Delete students
* View records

### Attendance

* View attendance records
* Get today's attendance
* Mark attendance

### Alerts

* View alerts
* Filter alerts
* Resolve alerts

### Enrollment

* Generate enrollment links
* Verify tokens
* Submit enrollment requests
* Approve or reject requests

## Database Tables

* students
* attendance_logs
* alerts
* enrollment_tokens
* pending_enrollments
* admin_users

## Environment Variables

```bash
DATABASE_URL=

JWT_SECRET_KEY=

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
SES_SENDER_EMAIL=

EMAIL_DEVELOPMENT_MODE=true
```

## Current Progress

### Completed

* User authentication
* Student management
* Attendance records
* Alert management
* Live monitor page
* Video streaming client
* WebSocket streaming
* Enrollment module
* Demo data generation

### In Progress

* Face recognition integration
* Face matching during streaming
* Activity detection
* Video clip recording
* Email notifications
* Mobile responsiveness
* HTTPS configuration
* Deployment documentation

## Troubleshooting

| Problem                    | Solution                     |
| -------------------------- | ---------------------------- |
| Camera not opening         | Try another camera index     |
| WebSocket connection fails | Verify port 5000 is open     |
| Login fails                | Check admin user in database |
| No video stream            | Inspect browser console      |

