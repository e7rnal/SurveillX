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
        query = "SELECT * FROM students ORDER BY created_at DESC"
        return self.execute_query(query)
    
    def get_student_by_id(self, student_id):
        """Get student by ID"""
        query = "SELECT * FROM students WHERE id = %s"
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
        """Get attendance records"""
        query = """
            SELECT a.*, s.name, s.roll_no, s.class
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
        """Get all pending enrollments"""
        query = """
            SELECT pe.*, et.email
            FROM pending_enrollments pe
            JOIN enrollment_tokens et ON pe.token_id = et.id
            WHERE pe.status = 'pending'
            ORDER BY pe.submitted_at DESC
        """
        return self.execute_query(query)
    
    def get_pending_enrollment_by_id(self, enrollment_id):
        """Get pending enrollment by ID"""
        query = """
            SELECT pe.*, et.email
            FROM pending_enrollments pe
            JOIN enrollment_tokens et ON pe.token_id = et.id
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
        
        # Recent alerts
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM alerts_logs WHERE timestamp > NOW() - INTERVAL '24 hours'"
        )
        stats['recent_alerts'] = result[0]['count'] if result else 0
        
        return stats
