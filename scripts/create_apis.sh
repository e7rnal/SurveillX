#!/bin/bash
# SurveillX Recovery Script - Creates all remaining API files

echo "🔧 Creating all API endpoint files..."

# Create auth.py
cat > /opt/dlami/nvme/surveillx-backend/api/auth.py << 'EOF'
"""Authentication API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
import bcrypt

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    try:
        db = current_app.db
        query = "SELECT * FROM admin_users WHERE username = %s"
        results = db.execute_query(query, (username,))
        
        if not results:
            return jsonify({"error": "Invalid credentials"}), 401
        
        user = results[0]
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            access_token = create_access_token(identity=username)
            return jsonify({
                "token": access_token,
                "user": {
                    "username": user['username'],
                    "role": user['role']
                }
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

# Create students.py
cat > /opt/dlami/nvme/surveillx-backend/api/students.py << 'EOF'
"""Students API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

students_bp = Blueprint('students', __name__)

@students_bp.route('/', methods=['GET'])
@jwt_required()
def get_students():
    try:
        db = current_app.db
        students = db.get_all_students()
        return jsonify({"students": students})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/<int:student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    try:
        db = current_app.db
        student = db.get_student_by_id(student_id)
        if student:
            return jsonify({"student": student})
        return jsonify({"error": "Student not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@students_bp.route('/', methods=['POST'])
@jwt_required()
def add_student():
    try:
        data = request.get_json()
        db = current_app.db
        student_id = db.add_student(
            name=data['name'],
            roll_no=data['roll_no'],
            contact_no=data.get('contact_no'),
            class_name=data.get('class'),
            face_encoding=data.get('face_encoding')
        )
        return jsonify({"student_id": student_id, "message": "Student added successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

# Create attendance.py
cat > /opt/dlami/nvme/surveillx-backend/api/attendance.py << 'EOF'
"""Attendance API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

attendance_bp = Blueprint('attendance', __name__)

@students_bp.route('/', methods=['GET'])
@jwt_required()
def get_attendance():
    try:
        db = current_app.db
        date = request.args.get('date')
        student_id = request.args.get('student_id')
        limit = int(request.args.get('limit', 100))
        
        attendance = db.get_attendance(date=date, student_id=student_id, limit=limit)
        return jsonify({"attendance": attendance})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@attendance_bp.route('/mark', methods=['POST'])
@jwt_required()
def mark_attendance():
    try:
        data = request.get_json()
        db = current_app.db
        attendance_id = db.mark_attendance(student_id=data['student_id'])
        return jsonify({"attendance_id": attendance_id, "message": "Attendance marked"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

# Create alerts.py
cat > /opt/dlami/nvme/surveillx-backend/api/alerts.py << 'EOF'
"""Alerts API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

alerts_bp = Blueprint('alerts', __name__)

@alerts_bp.route('/', methods=['GET'])
@jwt_required()
def get_alerts():
    try:
        db = current_app.db
        severity = request.args.get('severity')
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 100))
        
        alerts = db.get_alerts(severity=severity, event_type=event_type, limit=limit)
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    try:
        db = current_app.db
        alert = db.get_alert_by_id(alert_id)
        if alert:
            return jsonify({"alert": alert})
        return jsonify({"error": "Alert not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

# Create cameras.py
cat > /opt/dlami/nvme/surveillx-backend/api/cameras.py << 'EOF'
"""Cameras API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required

cameras_bp = Blueprint('cameras', __name__)

@cameras_bp.route('/', methods=['GET'])
@jwt_required()
def get_cameras():
    try:
        db = current_app.db
        cameras = db.get_all_cameras()
        return jsonify({"cameras": cameras})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

# Create stats.py
cat > /opt/dlami/nvme/surveillx-backend/api/stats.py << 'EOF'
"""Statistics API"""
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        db = current_app.db
        stats = db.get_dashboard_stats()
        return jsonify({"stats": stats})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
EOF

echo "✅ All API files created successfully!"
