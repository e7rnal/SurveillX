"""Attendance API"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from datetime import datetime

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/', methods=['GET'])
@jwt_required()
def get_attendance():
    try:
        db = current_app.db
        date = request.args.get('date')
        student_id = request.args.get('student_id')
        limit = int(request.args.get('limit', 100))
        
        records = db.get_attendance(date=date, student_id=student_id, limit=limit)
        return jsonify({"records": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_attendance():
    try:
        db = current_app.db
        today = datetime.now().strftime('%Y-%m-%d')
        records = db.get_attendance(date=today, limit=100)
        return jsonify({"records": records, "date": today})
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

