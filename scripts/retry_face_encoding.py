#!/usr/bin/env python3
"""
Retry face encoding generation for students missing embeddings
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import json
import base64
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def decode_photo(photo_data):
    """Decode base64 photo to numpy array"""
    try:
        if isinstance(photo_data, dict):
            photo_data = photo_data.get('data', '')
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',', 1)[1]
        img_bytes = base64.b64decode(photo_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.error(f"Error decoding photo: {e}")
        return None

def retry_student_encoding(student_id):
    """Retry generating face encoding for a student"""
    with app.app_context():
        from services.face_recognition_service import FaceRecognitionService
        from config import Config
        
        db = app.db
        config = Config()
        face_service = FaceRecognitionService(config)
        
        if not face_service or not face_service.app:
            logger.error("Face service not available!")
            return False
        
        # Get student
        student = db.get_student_by_id(student_id)
        if not student:
            logger.error(f"Student {student_id} not found")
            return False
        
        logger.info(f"Student: {student['name']} (ID: {student_id})")
        logger.info(f"Current face_encoding: {'EXISTS' if student.get('face_encoding') else 'MISSING'}")
        
        # Find the corresponding pending enrollment
        query = "SELECT * FROM pending_enrollments WHERE name = %s AND status = 'approved' ORDER BY id DESC LIMIT 1"
        result = db.execute_query(query, (student['name'],))
       
        if not result:
            logger.error(f"No approved enrollment found for {student['name']}")
            return False
        
        enrollment = result[0]
        logger.info(f"Found enrollment ID: {enrollment['id']}")
        
        sample_images = enrollment.get('sample_images')
        if not sample_images:
            logger.error("No sample images in enrollment!")
            return False
        
        sample_images = enrollment.get('sample_images')
        if not sample_images:
            logger.error("No sample images in enrollment!")
            return False
        
        # Decode photos
        if isinstance(sample_images, str):
            sample_images = json.loads(sample_images)
        
        logger.info(f"Decoding {len(sample_images)} photos...")
        frames = []
        for i, photo in enumerate(sample_images):
            frame = decode_photo(photo)
            if frame is not None:
                frames.append(frame)
                logger.info(f"  Photo {i+1}: {frame.shape}")
            else:
                logger.warning(f"  Photo {i+1}: FAILED TO DECODE")
        
        if not frames:
            logger.error("No valid frames decoded!")
            return False
        
        logger.info(f"Successfully decoded {len(frames)}/{len(sample_images)} photos")
        
        # Generate embedding
        logger.info("Generating face embedding...")
        result = face_service.encode_multiple(frames)
        
        if not result['embedding']:
            logger.error(f"Failed to generate embedding: {result.get('errors', 'Unknown error')}")
            return False
        
        embedding = result['embedding']
        logger.info(f"✅ Generated embedding: size={len(embedding)}, valid_count={result['valid_count']}")
        
        # Update student with embedding
        query = "UPDATE students SET face_encoding = %s WHERE id = %s"
        db.execute_query(query, (json.dumps(embedding), student_id), fetch=False, commit=True)
        
        # Add to face service cache
        face_service.add_known_face(student_id, student['name'], embedding)
        
        logger.info(f"✅ Successfully updated student {student_id} with face encoding!")
        logger.info(f"✅ Added to face service cache")
        
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python retry_face_encoding.py <student_id>")
        print("   or: python retry_face_encoding.py all")
        sys.exit(1)
    
    if sys.argv[1] == 'all':
        # Retry all students without face encoding
        with app.app_context():
            query = "SELECT id, name FROM students WHERE face_encoding IS NULL"
            students = app.db.execute_query(query)
            
            if not students:
                logger.info("No students missing face encodings!")
                sys.exit(0)
            
            logger.info(f"Found {len(students)} students without face encoding")
            success_count = 0
            
            for student in students:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing student ID {student['id']}")
                logger.info(f"{'='*60}")
                if retry_student_encoding(student['id']):
                    success_count += 1
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✅ Successfully processed {success_count}/{len(students)} students")
            logger.info(f"{'='*60}")
    else:
        student_id = int(sys.argv[1])
        if retry_student_encoding(student_id):
            sys.exit(0)
        else:
            sys.exit(1)
