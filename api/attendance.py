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
