"""
Demo Data Seeding Script for SurveillX
Populates database with realistic test data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_manager import DBManager
from config import Config
from datetime import datetime, timedelta
import random
import json

# Sample data
STUDENT_NAMES = [
    "Vishnu Jadhav", "Rohan Sharma", "Priya Patel", "Arjun Kumar",
    "Sneha Desai", "Rahul Mehta", "Ananya Singh", "Karan Verma",
    "Ishita Reddy", "Aditya Nair", "Pooja Gupta", "Siddharth Joshi"
]

CLASSES = ["BCA - I", "BCA - II", "BCA - III", "MCA - I", "MCA - II"]

EVENT_TYPES = ["running", "fighting", "loitering", "unauthorized_entry", "suspicious_activity"]

ALERT_DESCRIPTIONS = {
    "running": "Student detected running in corridor",
    "fighting": "Physical altercation detected",
    "loitering": "Prolonged presence in restricted area",
    "unauthorized_entry": "Entry detected in restricted zone",
    "suspicious_activity": "Unusual behavior pattern detected"
}

def seed_students(db):
    """Seed student data"""
    print("Seeding students...")
    
    for i, name in enumerate(STUDENT_NAMES, 1):
        roll_no = f"2024{i:03d}"
        class_name = random.choice(CLASSES)
        contact = f"+91 98765{i:05d}"
        
        # Check if student already exists
        existing = db.get_student_by_roll_no(roll_no)
        if existing:
            print(f"  ✓ Student {name} already exists")
            continue
        
        student_id = db.add_student(
            name=name,
            roll_no=roll_no,
            contact_no=contact,
            class_name=class_name,
            face_encoding=None  # Will be added when they enroll
        )
        print(f"  ✓ Added student: {name} ({roll_no})")

def seed_attendance(db):
    """Seed attendance data for past 7 days"""
    print("\nSeeding attendance records...")
    
    students = db.get_all_students()
    if not students:
        print("  ⚠ No students found, skipping attendance")
        return
    
    # Add attendance for past 7 days
    for days_ago in range(7):
        date = datetime.now() - timedelta(days=days_ago)
        
        # Random 70-90% attendance each day
        attending_count = random.randint(int(len(students) * 0.7), int(len(students) * 0.9))
        attending_students = random.sample(students, attending_count)
        
        for student in attending_students:
            # Random time between 8 AM and 10 AM
            hour = random.randint(8, 9)
            minute = random.randint(0, 59)
            timestamp = date.replace(hour=hour, minute=minute, second=0)
            
            db.mark_attendance(student['id'], timestamp)
        
        print(f"  ✓ Added {attending_count} attendance records for {date.strftime('%Y-%m-%d')}")

def seed_alerts(db):
    """Seed security alerts"""
    print("\nSeeding security alerts...")
    
    for i in range(15):
        event_type = random.choice(EVENT_TYPES)
        camera_id = 1  # Assuming camera ID 1 exists
        severity = random.choice(["low", "medium", "high"])
        
        # Create metadata with description
        metadata = {
            "description": ALERT_DESCRIPTIONS[event_type],
            "location": random.choice(["Main Corridor", "Library", "Cafeteria", "Parking Lot", "Lab Building"]),
            "confidence": round(random.uniform(0.7, 0.95), 2)
        }
        
        # Random time in past 7 days
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        alert_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        alert_id = db.create_alert(
            event_type=event_type,
            camera_id=camera_id,
            clip_path=None,  # No actual clips yet
            severity=severity,
            metadata=metadata
        )
        print(f"  ✓ Added alert: {event_type} ({severity}) - {metadata['description']}")

def seed_enrollments(db):
    """Seed pending enrollments"""
    print("\nSeeding pending enrollments...")
    
    pending_students = [
        {"name": "Amit Patel", "email": "amit.patel@example.com", "roll_no": "2024013", "class": "BCA - II"},
        {"name": "Neha Kapoor", "email": "neha.kapoor@example.com", "roll_no": "2024014", "class": "MCA - I"},
        {"name": "Vikram Singh", "email": "vikram.singh@example.com", "roll_no": "2024015", "class": "BCA - III"},
        {"name": "Riya Sharma", "email": "riya.sharma@example.com", "roll_no": "2024016", "class": "MCA - II"},
        {"name": "Kunal Desai", "email": "kunal.desai@example.com", "roll_no": "2024017", "class": "BCA - I"},
        {"name": "Anjali Reddy", "email": "anjali.reddy@example.com", "roll_no": "2024018", "class": "BCA - II"},
        {"name": "Rohit Kumar", "email": "rohit.kumar@example.com", "roll_no": "2024019", "class": "MCA - I"},
        {"name": "Divya Nair", "email": "divya.nair@example.com", "roll_no": "2024020", "class": "BCA - III"}
    ]
    
    import hashlib
    import secrets
    
    for student in pending_students:
        # Create enrollment token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=24)
        
        token_id = db.create_enrollment_token(
            token_hash=token_hash,
            email=student['email'],
            roll_no=student['roll_no'],
            expires_at=expires_at
        )
        
        # Create pending enrollment
        enrollment_id = db.create_pending_enrollment(
            token_id=token_id,
            name=student['name'],
            roll_no=student['roll_no'],
            contact_no=f"+91 98765{random.randint(10000, 99999)}",
            class_name=student['class'],
            face_encoding=None,
            sample_images=[]
        )
        
        print(f"  ✓ Added pending enrollment: {student['name']} ({student['email']})")

def main():
    """Main seeding function"""
    print("=" * 60)
    print("SurveillX Demo Data Seeding")
    print("=" * 60)
    
    try:
        db = DBManager(Config.DATABASE_URL)
        
        seed_students(db)
        seed_attendance(db)
        seed_alerts(db)
        seed_enrollments(db)
        
        print("\n" + "=" * 60)
        print("✅ Demo data seeding completed successfully!")
        print("=" * 60)
        
        # Show summary
        stats = db.get_dashboard_stats()
        print(f"\nDatabase Summary:")
        print(f"  Students: {stats['total_students']}")
        print(f"  Today's Attendance: {stats['today_attendance']}")
        print(f"  Recent Alerts: {stats['recent_alerts']}")
        print(f"  Active Cameras: {stats['active_cameras']}")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
