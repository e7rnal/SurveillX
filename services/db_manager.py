"""
Database Manager for SurveillX
Handles all database operations using psycopg2
"""

import psycopg2
import psycopg2.extras
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, database_url):
        """Initialize database connection"""
        self.database_url = database_url
        self.conn = None
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def execute_query(self, query, params=None, fetch=True, commit=False):
        """Execute a database query"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                
                if commit:
                    self.conn.commit()
                
                if fetch:
                    return cursor.fetchall()
                return None
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Database error: {e}")
            raise
    
    # ==================== STUDENT OPERATIONS ====================
    
    def get_all_students(self):
        """Get all students"""
        query = """
            SELECT 
                *,
                (face_encoding IS NOT NULL) as has_face_encoding
            FROM students 
            ORDER BY created_at DESC
        """
        return self.execute_query(query)
    
    def get_student_by_id(self, student_id):
        """Get student by ID"""
        query = """
            SELECT 
                *,
                (face_encoding IS NOT NULL) as has_face_encoding
            FROM students 
            WHERE id = %s
        """
        results = self.execute_query(query, (student_id,))
        return results[0] if results else None
    
    def get_student_by_roll_no(self, roll_no):
        """Get student by roll number"""
        query = "SELECT * FROM students WHERE roll_no = %s"
        results = self.execute_query(query, (roll_no,))
        return results[0] if results else None
    
    def add_student(self, name, roll_no, contact_no, class_name, face_encoding):
        """Add new student"""
        query = """
            INSERT INTO students (name, roll_no, contact_no, class, face_encoding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        encoding_json = json.dumps(face_encoding) if face_encoding else None
        result = self.execute_query(
            query,
            (name, roll_no, contact_no, class_name, encoding_json),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def update_student(self, student_id, **kwargs):
        """Update student information"""
        allowed_fields = ['name', 'roll_no', 'contact_no', 'class', 'face_encoding']
        updates = []
        params = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'face_encoding' and value:
                    value = json.dumps(value)
                updates.append(f"{field} = %s")
                params.append(value)
        
        if not updates:
            return False
        
        params.append(student_id)
        query = f"UPDATE students SET {', '.join(updates)} WHERE id = %s"
        self.execute_query(query, params, fetch=False, commit=True)
        return True
    
    def delete_student(self, student_id):
        """Delete student"""
        query = "DELETE FROM students WHERE id = %s"
        self.execute_query(query, (student_id,), fetch=False, commit=True)
        return True
    
    # ==================== ATTENDANCE OPERATIONS ====================
    
    def check_recent_attendance(self, student_id, minutes=30):
        """
        Check if student has attendance marked recently
        
        Args:
            student_id: Student ID to check
            minutes: Time window in minutes (default 30)
            
        Returns:
            True if attendance exists within the time window, False otherwise
        """
        query = """
            SELECT id FROM attendance_logs
            WHERE student_id = %s
            AND timestamp > NOW() - INTERVAL '%s minutes'
            ORDER BY timestamp DESC
            LIMIT 1
        """
        result = self.execute_query(query, (student_id, minutes))
        return len(result) > 0

    def mark_attendance(self, student_id, timestamp=None):
        """Mark student attendance"""
        if timestamp is None:
            timestamp = datetime.now()
        
        query = """
            INSERT INTO attendance_logs (student_id, timestamp)
            VALUES (%s, %s)
            RETURNING id
        """
        result = self.execute_query(
            query,
            (student_id, timestamp),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_attendance(self, date=None, student_id=None, limit=100):
        """Get attendance records, deduplicated to first check-in per student per day"""
        # When filtering by date, show only the earliest check-in per student
        if date and not student_id:
            query = """
                SELECT * FROM (
                    SELECT DISTINCT ON (a.student_id)
                        a.id, a.student_id, a.timestamp, 
                        s.name as student_name, s.roll_no, s.class
                    FROM attendance_logs a
                    JOIN students s ON a.student_id = s.id
                    WHERE DATE(a.timestamp) = %s
                    ORDER BY a.student_id, a.timestamp ASC
                ) sub
                ORDER BY sub.timestamp DESC
                LIMIT %s
            """
            return self.execute_query(query, (date, limit))
        
        # For student-specific or unfiltered queries, return all records
        query = """
            SELECT a.id, a.student_id, a.timestamp, 
                   s.name as student_name, s.roll_no, s.class
            FROM attendance_logs a
            JOIN students s ON a.student_id = s.id
        """
        params = []
        conditions = []
        
        if date:
            conditions.append("DATE(a.timestamp) = %s")
            params.append(date)
        
        if student_id:
            conditions.append("a.student_id = %s")
            params.append(student_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY a.timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def get_attendance_range(self, from_date, to_date, limit=1000):
        """Get attendance records across a date range (from_date to to_date inclusive),
        deduplicated to first check-in per student per day."""
        query = """
            SELECT * FROM (
                SELECT DISTINCT ON (a.student_id, DATE(a.timestamp))
                    a.id, a.student_id, a.timestamp,
                    s.name as student_name, s.roll_no, s.class
                FROM attendance_logs a
                JOIN students s ON a.student_id = s.id
                WHERE DATE(a.timestamp) BETWEEN %s AND %s
                ORDER BY a.student_id, DATE(a.timestamp), a.timestamp ASC
            ) sub
            ORDER BY sub.timestamp DESC
            LIMIT %s
        """
        return self.execute_query(query, (from_date, to_date, limit))

    def get_attendance_stats(self, date=None):
        """Get attendance statistics"""
        query = """
            SELECT 
                COUNT(DISTINCT student_id) as total_present,
                COUNT(*) as total_records
            FROM attendance_logs
        """
        if date:
            query += " WHERE DATE(timestamp) = %s"
            return self.execute_query(query, (date,))
        return self.execute_query(query)
    
    # ==================== ALERT OPERATIONS ====================

    
    def create_alert(self, event_type, camera_id, clip_path, severity, metadata):
        """Create new alert"""
        query = """
            INSERT INTO alerts_logs (event_type, camera_id, clip_path, severity, metadata)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        metadata_json = json.dumps(metadata) if metadata else None
        
        result = self.execute_query(
            query,
            (event_type, camera_id, clip_path, severity, metadata_json),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_alerts(self, severity=None, event_type=None, limit=100):
        """Get alerts"""
        query = "SELECT * FROM alerts_logs"
        params = []
        conditions = []
        
        if severity:
            conditions.append("severity = %s")
            params.append(severity)
        
        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))
    
    def get_alert_by_id(self, alert_id):
        """Get alert by ID"""
        query = "SELECT * FROM alerts_logs WHERE id = %s"
        results = self.execute_query(query, (alert_id,))
        return results[0] if results else None
    
    def clear_alerts(self):
        """Clear all alerts"""
        query = "DELETE FROM alerts_logs"
        self.execute_query(query, fetch=False, commit=True)
        return True
    
    def dismiss_alert(self, alert_id):
        """Dismiss/resolve an alert by marking it as dismissed"""
        query = "UPDATE alerts_logs SET dismissed = TRUE WHERE id = %s"
        self.execute_query(query, (alert_id,), fetch=False, commit=True)
        return True
    
    def delete_alert(self, alert_id):
        """Delete an alert permanently"""
        query = "DELETE FROM alerts_logs WHERE id = %s"
        self.execute_query(query, (alert_id,), fetch=False, commit=True)
        return True
    
    # ==================== CAMERA OPERATIONS ====================
    
    def get_all_cameras(self):
        """Get all cameras"""
        query = "SELECT * FROM cameras ORDER BY id"
        return self.execute_query(query)
    
    def get_camera_by_id(self, camera_id):
        """Get camera by ID"""
        query = "SELECT * FROM cameras WHERE id = %s"
        results = self.execute_query(query, (camera_id,))
        return results[0] if results else None
    
    def add_camera(self, name, location, rtsp_url, status='active'):
        """Add new camera"""
        query = """
            INSERT INTO cameras (name, location, rtsp_url, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(
            query,
            (name, location, rtsp_url, status),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def update_camera_status(self, camera_id, status):
        """Update camera status"""
        query = "UPDATE cameras SET status = %s WHERE id = %s"
        self.execute_query(query, (status, camera_id), fetch=False, commit=True)
        return True
    
    # ==================== ENROLLMENT OPERATIONS ====================
    
    def create_enrollment_token(self, token_hash, email, roll_no, expires_at):
        """Create enrollment token"""
        query = """
            INSERT INTO enrollment_tokens (token_hash, email, roll_no, expires_at)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(
            query,
            (token_hash, email, roll_no, expires_at),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_enrollment_token(self, token_hash):
        """Get enrollment token"""
        query = "SELECT * FROM enrollment_tokens WHERE token_hash = %s"
        results = self.execute_query(query, (token_hash,))
        return results[0] if results else None
    
    def mark_token_used(self, token_id):
        """Mark token as used"""
        query = "UPDATE enrollment_tokens SET used = TRUE WHERE id = %s"
        self.execute_query(query, (token_id,), fetch=False, commit=True)
    
    def update_token_status(self, token_id, status):
        """Update token status"""
        query = "UPDATE enrollment_tokens SET status = %s WHERE id = %s"
        self.execute_query(query, (status, token_id), fetch=False, commit=True)
    
    def create_pending_enrollment(self, token_id, name, roll_no, contact_no, class_name, face_encoding, sample_images):
        """Create pending enrollment"""
        query = """
            INSERT INTO pending_enrollments 
            (token_id, name, roll_no, contact_no, class, face_encoding, sample_images)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        encoding_json = json.dumps(face_encoding) if face_encoding else None
        images_json = json.dumps(sample_images) if sample_images else None
        
        result = self.execute_query(
            query,
            (token_id, name, roll_no, contact_no, class_name, encoding_json, images_json),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_pending_enrollments(self):
        """Get all pending enrollments (with or without token)"""
        query = """
            SELECT pe.*, COALESCE(et.email, '') as email
            FROM pending_enrollments pe
            LEFT JOIN enrollment_tokens et ON pe.token_id = et.id
            WHERE pe.status IN ('pending', 'pending_approval')
            ORDER BY pe.submitted_at DESC
        """
        return self.execute_query(query)
    
    def get_pending_enrollment_by_id(self, enrollment_id):
        """Get pending enrollment by ID (with or without token)"""
        query = """
            SELECT pe.*, COALESCE(et.email, '') as email
            FROM pending_enrollments pe
            LEFT JOIN enrollment_tokens et ON pe.token_id = et.id
            WHERE pe.id = %s
        """
        results = self.execute_query(query, (enrollment_id,))
        return results[0] if results else None
    
    def approve_enrollment(self, enrollment_id):
        """Approve enrollment and create student"""
        enrollment = self.get_pending_enrollment_by_id(enrollment_id)
        if not enrollment:
            return None
        
        # Create student
        student_id = self.add_student(
            name=enrollment['name'],
            roll_no=enrollment['roll_no'],
            contact_no=enrollment['contact_no'],
            class_name=enrollment['class'],
            face_encoding=json.loads(enrollment['face_encoding']) if enrollment['face_encoding'] else None
        )
        
        # Update enrollment status
        query = "UPDATE pending_enrollments SET status = 'approved' WHERE id = %s"
        self.execute_query(query, (enrollment_id,), fetch=False, commit=True)
        
        # Mark token as used
        self.mark_token_used(enrollment['token_id'])
        
        return student_id
    
    def reject_enrollment(self, enrollment_id, reason):
        """Reject enrollment"""
        query = """
            UPDATE pending_enrollments 
            SET status = 'rejected', rejection_reason = %s 
            WHERE id = %s
        """
        self.execute_query(query, (reason, enrollment_id), fetch=False, commit=True)
        return True
    
    # ==================== STATISTICS ====================
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        stats = {}
        
        # Total students
        result = self.execute_query("SELECT COUNT(*) as count FROM students")
        stats['total_students'] = result[0]['count'] if result else 0
        
        # Today's attendance
        result = self.execute_query(
            "SELECT COUNT(DISTINCT student_id) as count FROM attendance_logs WHERE DATE(timestamp) = CURRENT_DATE"
        )
        stats['today_attendance'] = result[0]['count'] if result else 0
        
        # Active cameras
        result = self.execute_query("SELECT COUNT(*) as count FROM cameras WHERE status = 'active'")
        stats['active_cameras'] = result[0]['count'] if result else 0
        
        # Recent alerts (unresolved only)
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM alerts_logs WHERE timestamp > NOW() - INTERVAL '24 hours' AND (status IS NULL OR status = 'unresolved')"
        )
        stats['recent_alerts'] = result[0]['count'] if result else 0

        # Enrolled face count
        result = self.execute_query(
            "SELECT COUNT(DISTINCT s.id) as count FROM students s WHERE s.face_encoding IS NOT NULL"
        )
        stats['enrolled_faces'] = result[0]['count'] if result else 0
        
        return stats
    
    # ==================== STUDENT FACES ====================
    
    def add_student_face(self, student_id, photo_path):
        """Add a face photo for a student"""
        query = """
            INSERT INTO student_faces (student_id, photo_path)
            VALUES (%s, %s)
            RETURNING id
        """
        result = self.execute_query(query, (student_id, photo_path), commit=True)
        return result[0]['id'] if result else None
    
    def get_student_faces(self, student_id):
        """Get all face photos for a student"""
        query = """
            SELECT id, student_id, photo_path, created_at
            FROM student_faces
            WHERE student_id = %s
            ORDER BY created_at DESC
        """
        results = self.execute_query(query, (student_id,))
        for r in results:
            if isinstance(r.get('created_at'), datetime):
                r['created_at'] = r['created_at'].isoformat()
        return results
    
    def delete_student_face(self, face_id):
        """Delete a student face photo"""
        # Get path first for file cleanup
        query = "SELECT photo_path FROM student_faces WHERE id = %s"
        result = self.execute_query(query, (face_id,))
        path = result[0]['photo_path'] if result else None
        
        query = "DELETE FROM student_faces WHERE id = %s"
        self.execute_query(query, (face_id,), fetch=False, commit=True)
        return path
    
    def get_student_face_count(self, student_id):
        """Count enrolled face photos"""
        query = "SELECT COUNT(*) as count FROM student_faces WHERE student_id = %s"
        result = self.execute_query(query, (student_id,))
        return result[0]['count'] if result else 0
    
    # ==================== ENHANCED ALERTS ====================
    
    def create_alert_with_snapshot(self, event_type, camera_id, clip_path, severity, metadata, snapshot_path=None, student_id=None):
        """Create alert with optional snapshot"""
        query = """
            INSERT INTO alerts_logs (event_type, camera_id, clip_path, severity, metadata, snapshot_path, student_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'unresolved')
            RETURNING id
        """
        metadata_json = json.dumps(metadata) if metadata else None
        result = self.execute_query(
            query,
            (event_type, camera_id, clip_path, severity, metadata_json, snapshot_path, student_id),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_alerts_paginated(self, severity=None, event_type=None, status=None, date=None, page=1, per_page=10):
        """Get alerts with pagination and filters"""
        query = "SELECT *, COUNT(*) OVER() as total_count FROM alerts_logs"
        params = []
        conditions = []
        
        if severity:
            conditions.append("severity = %s")
            params.append(severity)
        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)
        if status:
            if status == 'unresolved':
                conditions.append("(status IS NULL OR status = 'unresolved')")
            else:
                conditions.append("status = %s")
                params.append(status)
        if date:
            conditions.append("DATE(timestamp) = %s")
            params.append(date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])
        
        results = self.execute_query(query, tuple(params))
        total = results[0]['total_count'] if results else 0
        
        # Clean up total_count from each row
        for r in results:
            r.pop('total_count', None)
        
        return results, total
    
    def update_alert_status(self, alert_id, status):
        """Update alert status (resolved, false_alarm)"""
        query = """
            UPDATE alerts_logs 
            SET status = %s, resolved_at = NOW()
            WHERE id = %s
        """
        self.execute_query(query, (status, alert_id), fetch=False, commit=True)
        return True
    
    # ==================== MANUAL ATTENDANCE ====================
    
    def mark_manual_attendance(self, student_id, date, status='present', note=None, marked_by='admin'):
        """Mark manual attendance override"""
        query = """
            INSERT INTO attendance_manual (student_id, date, status, note, marked_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute_query(
            query,
            (student_id, date, status, note, marked_by),
            commit=True
        )
        return result[0]['id'] if result else None
    
    def get_absent_students(self, date):
        """Get students who are NOT present on a given date"""
        query = """
            SELECT s.id, s.name, s.roll_no, s.class,
                   (s.face_encoding IS NOT NULL) as has_face_encoding
            FROM students s
            WHERE s.id NOT IN (
                SELECT DISTINCT student_id FROM attendance_logs
                WHERE DATE(timestamp) = %s
            )
            AND s.id NOT IN (
                SELECT DISTINCT student_id FROM attendance_manual
                WHERE date = %s AND status = 'present'
            )
            ORDER BY s.name
        """
        return self.execute_query(query, (date, date))
    
    def get_student_attendance_history(self, student_id, limit=30):
        """Get attendance history for a specific student"""
        query = """
            SELECT a.id, a.timestamp, 'auto' as source
            FROM attendance_logs a
            WHERE a.student_id = %s
            ORDER BY a.timestamp DESC
            LIMIT %s
        """
        results = self.execute_query(query, (student_id, limit))
        for r in results:
            if isinstance(r.get('timestamp'), datetime):
                r['timestamp'] = r['timestamp'].isoformat()
        return results
    
    # ==================== NOTIFICATION SETTINGS ====================
    
    def get_notification_settings(self):
        """Get notification settings"""
        query = "SELECT * FROM notification_settings LIMIT 1"
        results = self.execute_query(query)
        return results[0] if results else None
    
    def update_notification_settings(self, email, notify_high, notify_medium):
        """Update notification settings"""
        query = """
            UPDATE notification_settings
            SET email = %s, notify_high = %s, notify_medium = %s, updated_at = NOW()
            WHERE id = (SELECT id FROM notification_settings LIMIT 1)
        """
        self.execute_query(query, (email, notify_high, notify_medium), fetch=False, commit=True)
        return True

    def get_attendance_trend(self, days=7):
        """Get daily attendance count for the last N days (unique students per day)"""
        query = """
            SELECT d.day::date as date, COALESCE(cnt.total, 0) as count
            FROM generate_series(
                CURRENT_DATE - INTERVAL '%s days',
                CURRENT_DATE,
                INTERVAL '1 day'
            ) d(day)
            LEFT JOIN (
                SELECT DATE(timestamp) as day, COUNT(DISTINCT student_id) as total
                FROM attendance_logs
                WHERE DATE(timestamp) >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(timestamp)
            ) cnt ON d.day::date = cnt.day
            ORDER BY d.day ASC
        """
        return self.execute_query(query, (days, days))

    def get_alert_distribution(self, days=30):
        """Get alert counts grouped by event_type for the last N days"""
        query = """
            SELECT event_type, COUNT(*) as count
            FROM alerts_log
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY event_type
            ORDER BY count DESC
        """
        return self.execute_query(query, (days,))

    def get_absent_students(self, date=None):
        """Get students not present on a given date"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        query = """
            SELECT s.id, s.name, s.roll_no, s.class
            FROM students s
            WHERE s.id NOT IN (
                SELECT DISTINCT student_id FROM attendance_logs
                WHERE DATE(timestamp) = %s
            )
            ORDER BY s.name
        """
        return self.execute_query(query, (date,))
