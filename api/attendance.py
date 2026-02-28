"""Attendance API — with manual mark, absent list, late detection"""
from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required
from datetime import datetime
import csv
import io

attendance_bp = Blueprint('attendance', __name__)

# 9:00 AM IST = 03:30 UTC
LATE_HOUR_UTC = 3
LATE_MINUTE_UTC = 30


@attendance_bp.route('/', methods=['GET'])
@jwt_required()
def get_attendance():
    try:
        db = current_app.db
        date = request.args.get('date')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        student_id = request.args.get('student_id')
        search = request.args.get('search', '').strip()
        limit = int(request.args.get('limit', 500))

        # Date range query
        if from_date and to_date:
            records = db.get_attendance_range(from_date, to_date, limit=limit)
        else:
            records = db.get_attendance(date=date, student_id=student_id, limit=limit)

        if search:
            search_lower = search.lower()
            records = [r for r in records if
                       search_lower in (r.get('student_name', '') or '').lower() or
                       search_lower in str(r.get('roll_no', ''))]

        # Serialize timestamps and add status
        for r in records:
            if isinstance(r.get('timestamp'), datetime):
                ts = r['timestamp']
                # Check if late (after 9:00 AM IST = 03:30 UTC)
                if ts.hour > LATE_HOUR_UTC or (ts.hour == LATE_HOUR_UTC and ts.minute > LATE_MINUTE_UTC):
                    r['status'] = 'late'
                else:
                    r['status'] = 'present'
                r['timestamp'] = ts.isoformat() + 'Z'
            else:
                r['status'] = 'present'
            r['source'] = 'auto'

        return jsonify({"records": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_attendance():
    try:
        db = current_app.db
        today = datetime.now().strftime('%Y-%m-%d')
        records = db.get_attendance(date=today, limit=200)

        for r in records:
            if isinstance(r.get('timestamp'), datetime):
                ts = r['timestamp']
                if ts.hour > LATE_HOUR_UTC or (ts.hour == LATE_HOUR_UTC and ts.minute > LATE_MINUTE_UTC):
                    r['status'] = 'late'
                else:
                    r['status'] = 'present'
                r['timestamp'] = ts.isoformat() + 'Z'
            else:
                r['status'] = 'present'

        return jsonify({"records": records, "date": today})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/mark', methods=['POST'])
@jwt_required()
def mark_attendance():
    try:
        data = request.get_json()
        db = current_app.db

        if db.check_recent_attendance(data['student_id'], minutes=1440):
            return jsonify({"message": "Already marked recently"}), 200

        attendance_id = db.mark_attendance(student_id=data['student_id'])
        return jsonify({"attendance_id": attendance_id, "message": "Attendance marked"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/manual', methods=['POST'])
@jwt_required()
def mark_manual():
    """Manually mark a student as present/absent/late with optional note."""
    try:
        data = request.get_json()
        db = current_app.db

        student_id = data.get('student_id')
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        status = data.get('status', 'present')
        note = data.get('note', '')

        if not student_id:
            return jsonify({"error": "student_id required"}), 400

        if status not in ('present', 'absent', 'late'):
            return jsonify({"error": "status must be present, absent, or late"}), 400

        # If marking present, also add to attendance_logs for consistency
        if status == 'present':
            db.mark_attendance(student_id=student_id)

        record_id = db.mark_manual_attendance(
            student_id=student_id,
            date=date,
            status=status,
            note=note,
            marked_by='admin'
        )

        return jsonify({
            "id": record_id,
            "message": f"Student manually marked as {status}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/absent', methods=['GET'])
@jwt_required()
def get_absent():
    """Get list of students not present on given date."""
    try:
        db = current_app.db
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        absent = db.get_absent_students(date)
        return jsonify({"absent": absent, "date": date, "count": len(absent)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/stats', methods=['GET'])
@jwt_required()
def attendance_stats():
    """Today's attendance stats."""
    try:
        db = current_app.db
        today = datetime.now().strftime('%Y-%m-%d')
        stats = db.get_attendance_stats(date=today)
        total_students_result = db.execute_query("SELECT COUNT(*) as count FROM students")
        total_students = total_students_result[0]['count'] if total_students_result else 0

        present = stats[0]['total_present'] if stats else 0
        return jsonify({
            "date": today,
            "total_students": total_students,
            "present": present,
            "absent": total_students - present,
            "percentage": round((present / max(total_students, 1)) * 100, 1),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/trend', methods=['GET'])
@jwt_required()
def attendance_trend():
    """Attendance trend for dashboard chart (last 7 days)."""
    try:
        db = current_app.db
        days = int(request.args.get('days', 7))
        trend = db.get_attendance_trend(days=days)
        # Serialize dates
        for t in trend:
            if hasattr(t.get('date'), 'isoformat'):
                t['date'] = t['date'].isoformat()
        return jsonify({"trend": trend})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/export', methods=['GET'])
@jwt_required()
def export_attendance():
    """Export attendance as CSV for a given date."""
    try:
        db = current_app.db
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        records = db.get_attendance(date=date, limit=10000)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['#', 'Student Name', 'Roll No', 'Class', 'Time', 'Status'])

        for i, r in enumerate(records, 1):
            ts = r.get('timestamp', '')
            status = 'Present'
            if isinstance(ts, datetime):
                if ts.hour > LATE_HOUR_UTC or (ts.hour == LATE_HOUR_UTC and ts.minute > LATE_MINUTE_UTC):
                    status = 'Late'
                ts = ts.strftime('%I:%M %p')
            writer.writerow([
                i,
                r.get('student_name', ''),
                r.get('roll_no', ''),
                r.get('class', ''),
                ts,
                status,
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=attendance_{date}.csv'
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@attendance_bp.route('/absent', methods=['GET'])
@jwt_required()
def absent_students():
    """Get students not present on a given date."""
    try:
        db = current_app.db
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        students = db.get_absent_students(date=date)
        return jsonify({"students": students, "date": date})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
