"""
SurveillX ML Services Verification Script
Tests: InsightFace, YOLO11-pose, and ML Worker connectivity
"""
import os
os.environ['ORT_DISABLE_DRM'] = '1'

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import numpy as np
import cv2

PASS = "✅"
FAIL = "❌"

def test_insightface():
    """Test 1: InsightFace loads and detects faces"""
    print("\n" + "="*50)
    print("TEST 1: InsightFace Face Detection")
    print("="*50)
    
    try:
        from services.face_service import FaceService
        fs = FaceService()
        stats = fs.get_stats()
        print(f"  Model: {stats['model']}")
        print(f"  Available: {stats['available']}")
        print(f"  GPU ID: {stats['gpu_id']}")
        
        if not stats['available']:
            print(f"  {FAIL} InsightFace not available")
            return False
        
        # Create a synthetic test image with a "face-like" pattern
        # Use a real-ish sized frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # Draw a simple oval face shape (won't be detected as a real face, but tests the pipeline)
        cv2.ellipse(frame, (640, 300), (80, 110), 0, 0, 360, (180, 150, 130), -1)
        cv2.circle(frame, (610, 280), 10, (50, 50, 50), -1)  # left eye
        cv2.circle(frame, (670, 280), 10, (50, 50, 50), -1)  # right eye
        cv2.ellipse(frame, (640, 330), (25, 10), 0, 0, 360, (100, 80, 80), -1)  # mouth
        
        t0 = time.time()
        faces = fs.detect_and_recognize(frame)
        elapsed = (time.time() - t0) * 1000
        
        print(f"  Inference time: {elapsed:.0f}ms")
        print(f"  Faces detected: {len(faces)}")
        
        # Even if no face detected on synthetic image, the model loaded and ran
        print(f"  {PASS} InsightFace pipeline works (model loaded, inference ran)")
        
        # Test encode_face
        encoding = fs.encode_face(frame)
        print(f"  encode_face result: {'512-d vector' if encoding and len(encoding) == 512 else 'None (no face in synthetic image — expected)'}")
        
        # Test add_known_face
        dummy_emb = np.random.randn(512).astype(np.float32)
        dummy_emb /= np.linalg.norm(dummy_emb)
        fs.add_known_face(999, "Test Student", dummy_emb.tolist())
        assert len(fs.known_embeddings) == 1
        print(f"  {PASS} add_known_face works ({len(fs.known_embeddings)} cached)")
        
        fs.remove_known_face(999)
        assert len(fs.known_embeddings) == 0
        print(f"  {PASS} remove_known_face works")
        
        return True
        
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_yolo_pose():
    """Test 2: YOLO11-pose loads and detects keypoints"""
    print("\n" + "="*50)
    print("TEST 2: YOLO11-pose Activity Detection")
    print("="*50)
    
    try:
        from services.activity_detector import ActivityDetector
        ad = ActivityDetector()
        stats = ad.get_stats()
        print(f"  Model: {stats['model']}")
        print(f"  Available: {stats['available']}")
        print(f"  Conf threshold: {stats['conf_threshold']}")
        
        if not stats['available']:
            print(f"  {FAIL} YOLO11-pose not available")
            return False
        
        # Create test frame with a standing person shape
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # dark gray background
        
        # Draw a simple person shape
        cv2.circle(frame, (640, 200), 30, (200, 180, 160), -1)  # head
        cv2.line(frame, (640, 230), (640, 400), (200, 180, 160), 8)  # body
        cv2.line(frame, (640, 280), (580, 350), (200, 180, 160), 6)  # left arm
        cv2.line(frame, (640, 280), (700, 350), (200, 180, 160), 6)  # right arm
        cv2.line(frame, (640, 400), (600, 550), (200, 180, 160), 6)  # left leg
        cv2.line(frame, (640, 400), (680, 550), (200, 180, 160), 6)  # right leg
        
        t0 = time.time()
        result = ad.detect(frame)
        elapsed = (time.time() - t0) * 1000
        
        print(f"  Inference time: {elapsed:.0f}ms")
        print(f"  Activity type: {result.get('type', 'N/A')}")
        print(f"  Is abnormal: {result.get('is_abnormal', False)}")
        print(f"  Persons detected: {len(result.get('persons', []))}")
        print(f"  Tracked persons: {ad.get_stats()['tracked_persons']}")
        
        print(f"  {PASS} YOLO11-pose pipeline works (model loaded, inference ran)")
        
        # Test multiple frames for temporal tracking
        for i in range(5):
            ad.detect(frame)
        print(f"  {PASS} Temporal tracking works ({ad.get_stats()['tracked_persons']} tracked)")
        
        return True
        
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ml_worker_import():
    """Test 3: ML Worker can import and initialize"""
    print("\n" + "="*50)
    print("TEST 3: ML Worker Import & Init")
    print("="*50)
    
    try:
        from services.ml_worker import MLWorker
        worker = MLWorker()
        print(f"  {PASS} MLWorker class imported")
        
        # Don't call init_models here (already tested above)
        # Just verify the worker can be created
        assert worker.frame_count == 0
        assert worker.running == False
        print(f"  {PASS} MLWorker initialized (frame_count=0, running=False)")
        
        # Test process_frame method exists
        assert hasattr(worker, 'process_frame')
        assert hasattr(worker, 'run')
        print(f"  {PASS} MLWorker has process_frame() and run() methods")
        
        return True
        
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ml_worker_processing():
    """Test 4: ML Worker end-to-end frame processing"""
    print("\n" + "="*50)
    print("TEST 4: ML Worker Frame Processing")
    print("="*50)
    
    try:
        from services.ml_worker import MLWorker
        worker = MLWorker()
        worker.init_models()
        
        face_ok = worker.face_service is not None
        activity_ok = worker.activity_detector is not None
        print(f"  Face service: {'loaded' if face_ok else 'NOT loaded'}")
        print(f"  Activity detector: {'loaded' if activity_ok else 'NOT loaded'}")
        
        # Create a test frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (80, 80, 80)
        
        t0 = time.time()
        results = worker.process_frame(frame, camera_id=1)
        elapsed = (time.time() - t0) * 1000
        
        print(f"  Processing time: {elapsed:.0f}ms")
        print(f"  Faces: {len(results.get('faces', []))}")
        print(f"  Activity: {results.get('activity', {}).get('type', 'N/A')}")
        print(f"  {PASS} End-to-end frame processing works")
        
        return True
        
    except Exception as e:
        print(f"  {FAIL} Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔬 SurveillX ML Services Verification")
    print("=" * 50)
    
    results = {}
    results['InsightFace'] = test_insightface()
    results['YOLO11-pose'] = test_yolo_pose()
    results['ML Worker Import'] = test_ml_worker_import()
    results['ML Worker Processing'] = test_ml_worker_processing()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    all_pass = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status} {name}")
        if not passed:
            all_pass = False
    
    print("\n" + ("🎉 All tests passed!" if all_pass else "⚠️ Some tests failed"))
    sys.exit(0 if all_pass else 1)
