#!/usr/bin/env python3
"""
Import students from a CSV file into the SurveillX database.

Usage:
    python scripts/import_students.py scripts/students_sample.csv

CSV format: name, roll_no, class, contact_no
Face encoding is NOT included — students can enroll their face later via the enrollment flow.
"""

import sys
import os
import csv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.db_manager import DBManager


def import_students(csv_path):
    """Import students from CSV into database."""
    if not os.path.isfile(csv_path):
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)

    db = DBManager(Config.DATABASE_URL)

    imported = 0
    skipped = 0
    errors = 0

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '').strip()
            roll_no = row.get('roll_no', '').strip()
            class_name = row.get('class', '').strip()
            contact_no = row.get('contact_no', '').strip()

            if not name or not roll_no:
                print(f"⚠️  Skipping row (missing name or roll_no): {row}")
                skipped += 1
                continue

            # Check if student with this roll_no already exists
            existing = db.get_student_by_roll_no(roll_no)
            if existing:
                print(f"⏭️  Already exists: {name} (roll {roll_no})")
                skipped += 1
                continue

            try:
                student_id = db.add_student(
                    name=name,
                    roll_no=roll_no,
                    contact_no=contact_no,
                    class_name=class_name,
                    face_encoding=None  # No face encoding from CSV
                )
                print(f"✅ Imported: {name} (roll {roll_no}, class {class_name}) → ID {student_id}")
                imported += 1
            except Exception as e:
                print(f"❌ Error importing {name}: {e}")
                errors += 1

    db.close()

    print(f"\n{'='*40}")
    print(f"📊 Import Summary")
    print(f"   Imported: {imported}")
    print(f"   Skipped:  {skipped}")
    print(f"   Errors:   {errors}")
    print(f"{'='*40}")

    return imported


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_students.py <csv_file>")
        print("Example: python scripts/import_students.py scripts/students_sample.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    import_students(csv_path)
