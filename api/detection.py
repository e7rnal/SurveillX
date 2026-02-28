"""
Detection Testing API — Upload labelled video clips and run activity detection.
Returns a timeline of detected activities with timestamps, confidence scores,
and per-frame keypoint data for skeleton visualisation.
Supports labelled uploads for LSTM model retraining.
"""
import os
import time
import json
import uuid
import glob
import threading
import cv2
import logging
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

detection_bp = Blueprint('detection', __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'test_clips')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'mpg', 'mpeg'}
ALLOWED_LABELS = {'fighting', 'running', 'falling', 'loitering', 'no_activity', 'no_person'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@detection_bp.route('/test-video', methods=['POST'])
@jwt_required()
def test_video():
    """
    Upload a labelled video clip and run activity detection on it.
    Returns a timeline of detected activities plus a video_url for playback.

    Form fields:
      - video: the video file
      - label: activity label (fighting/running/falling/loitering/no_activity/no_person)
      - person_count: integer 0-12 or 'crowd'
      - sample_fps: how many frames per second to analyze (default 10)
    """
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"Unsupported format. Use: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Parse label and person count (optional — for auto-detect mode, skip labeling)
    label = request.form.get('label', '').strip().lower()
    if label and label not in ALLOWED_LABELS:
        return jsonify({"error": f"Invalid label. Use: {', '.join(sorted(ALLOWED_LABELS))}"}), 400
    if not label:
        label = 'auto'

    person_count_raw = request.form.get('person_count', '').strip().lower()
    if person_count_raw == 'crowd':
        person_count = 'crowd'
    elif person_count_raw:
        try:
            person_count = int(person_count_raw)
            if person_count < 0 or person_count > 12:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "person_count must be 0-12 or 'crowd'"}), 400
    else:
        person_count = 'auto'

    # Parse optional params
    sample_fps = float(request.form.get('sample_fps', 10))

    # Save uploaded file
    ext = file.filename.rsplit('.', 1)[1].lower()
    file_id = uuid.uuid4().hex[:8]
    safe_orig = secure_filename(file.filename)
    filename = f"test_{file_id}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    try:
        # Check file size
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            os.remove(filepath)
            return jsonify({"error": "File too large (max 100MB)"}), 400

        # Save metadata sidecar
        meta = {
            'file_id': file_id,
            'original_name': safe_orig,
            'filename': filename,
            'label': label,
            'person_count': person_count,
            'uploaded_at': time.time(),
        }
        meta_path = os.path.join(UPLOAD_DIR, f"test_{file_id}.json")
        with open(meta_path, 'w') as mf:
            json.dump(meta, mf, indent=2)

        # Transcode to MP4 if needed (for browser playback)
        playback_path = filepath
        if ext not in ('mp4', 'webm'):
            mp4_path = os.path.join(UPLOAD_DIR, f"test_{file_id}.mp4")
            transcode_ok = _transcode_to_mp4(filepath, mp4_path)
            if transcode_ok:
                playback_path = mp4_path

        # Process video
        results = process_video_clip(filepath, sample_fps=sample_fps)

        # Add video URL for playback
        playback_name = os.path.basename(playback_path)
        results['video_url'] = f'/uploads/test_clips/{playback_name}'

        # Include label metadata in response
        results['label'] = meta

        return jsonify(results)

    except Exception as e:
        logger.error(f"Detection error: {e}")
        return jsonify({"error": str(e)}), 500


@detection_bp.route('/cleanup/<file_id>', methods=['DELETE'])
@jwt_required()
def cleanup_video(file_id):
    """Delete a test video and its metadata sidecar."""
    removed = 0
    for f in glob.glob(os.path.join(UPLOAD_DIR, f"test_{file_id}.*")):
        _safe_remove(f)
        removed += 1
    return jsonify({"removed": removed})


@detection_bp.route('/history', methods=['GET'])
@jwt_required()
def list_test_videos():
    """List previously processed test videos that are still on disk."""
    videos = []
    for f in sorted(glob.glob(os.path.join(UPLOAD_DIR, 'test_*.*')), key=os.path.getmtime, reverse=True):
        name = os.path.basename(f)
        if name.endswith('.json'):
            continue
        stat = os.stat(f)
        videos.append({
            'filename': name,
            'url': f'/uploads/test_clips/{name}',
            'size_mb': round(stat.st_size / 1024 / 1024, 1),
            'modified': stat.st_mtime,
        })
    return jsonify(videos[:20])  # last 20


@detection_bp.route('/labeled-clips', methods=['GET'])
@jwt_required()
def list_labeled_clips():
    """List all uploaded clips with their label metadata."""
    clips = []
    for meta_file in sorted(glob.glob(os.path.join(UPLOAD_DIR, 'test_*.json')),
                            key=os.path.getmtime, reverse=True):
        try:
            with open(meta_file) as mf:
                meta = json.load(mf)
        except Exception:
            continue

        file_id = meta.get('file_id', '')
        # Find the actual video file
        video_file = None
        for ext in ALLOWED_EXTENSIONS:
            candidate = os.path.join(UPLOAD_DIR, f"test_{file_id}.{ext}")
            if os.path.exists(candidate):
                video_file = candidate
                break

        if not video_file:
            continue

        stat = os.stat(video_file)
        # Check for playback mp4
        mp4_path = os.path.join(UPLOAD_DIR, f"test_{file_id}.mp4")
        if os.path.exists(mp4_path):
            playback_url = f'/uploads/test_clips/test_{file_id}.mp4'
        else:
            playback_url = f'/uploads/test_clips/{os.path.basename(video_file)}'

        clips.append({
            'file_id': file_id,
            'original_name': meta.get('original_name', ''),
            'filename': os.path.basename(video_file),
            'label': meta.get('label', 'unknown'),
            'person_count': meta.get('person_count', '?'),
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'uploaded_at': meta.get('uploaded_at', 0),
            'url': playback_url,
        })

    return jsonify(clips)


@detection_bp.route('/labeled-clip/<file_id>', methods=['DELETE'])
@jwt_required()
def delete_labeled_clip(file_id):
    """Delete a specific labeled clip and all associated files."""
    removed = 0
    for f in glob.glob(os.path.join(UPLOAD_DIR, f"test_{file_id}.*")):
        _safe_remove(f)
        removed += 1
    if removed == 0:
        return jsonify({"error": "Clip not found"}), 404
    return jsonify({"removed": removed, "file_id": file_id})


@detection_bp.route('/retrain', methods=['POST'])
@jwt_required()
def retrain_model():
    """Trigger LSTM model retraining using all labeled clips."""
    # Count available labeled clips
    meta_files = glob.glob(os.path.join(UPLOAD_DIR, 'test_*.json'))
    if len(meta_files) < 5:
        return jsonify({
            "error": f"Need at least 5 labeled clips to retrain. Currently have {len(meta_files)}."
        }), 400

    # Check if retrain is already running
    lock_file = os.path.join(UPLOAD_DIR, '.retrain_lock')
    if os.path.exists(lock_file):
        return jsonify({"error": "Retraining is already in progress"}), 409

    # Start retraining in background thread
    def _run_retrain():
        try:
            with open(lock_file, 'w') as lf:
                lf.write(str(time.time()))
            from engines.activity_detection.retrain import retrain_from_labeled_clips
            retrain_from_labeled_clips(UPLOAD_DIR)
        except Exception as e:
            logger.error(f"Retrain failed: {e}", exc_info=True)
        finally:
            _safe_remove(lock_file)

    thread = threading.Thread(target=_run_retrain, daemon=True)
    thread.start()

    return jsonify({
        "status": "started",
        "clips_count": len(meta_files),
        "message": f"Retraining started with {len(meta_files)} labeled clips. This may take several minutes."
    })


@detection_bp.route('/retrain-status', methods=['GET'])
@jwt_required()
def retrain_status():
    """Check if retraining is currently running."""
    lock_file = os.path.join(UPLOAD_DIR, '.retrain_lock')
    is_running = os.path.exists(lock_file)
    return jsonify({"running": is_running})


@detection_bp.route('/process-clip', methods=['POST'])
@jwt_required()
def process_saved_clip():
    """
    Process a saved clip by its relative path.
    Body: { "clip_path": "fight_10s.mp4", "sample_fps": 5 }
    """
    data = request.get_json(silent=True) or {}
    clip_path = data.get('clip_path', '')
    sample_fps = float(data.get('sample_fps', 5))

    if not clip_path:
        return jsonify({"error": "clip_path required"}), 400

    # Security: ensure path doesn't escape the upload directory
    safe_path = os.path.normpath(os.path.join(UPLOAD_DIR, clip_path))
    if not safe_path.startswith(os.path.normpath(UPLOAD_DIR)):
        return jsonify({"error": "Invalid clip path"}), 400

    if not os.path.exists(safe_path):
        return jsonify({"error": f"Clip not found: {clip_path}"}), 404

    try:
        results = process_video_clip(safe_path, sample_fps=sample_fps)

        # Add video URL for playback
        ext = clip_path.rsplit('.', 1)[-1].lower() if '.' in clip_path else ''
        if ext in ('mp4', 'webm'):
            results['video_url'] = f'/uploads/test_clips/{clip_path}'
        else:
            # Try to transcode for playback
            mp4_name = os.path.splitext(os.path.basename(clip_path))[0] + '_playback.mp4'
            mp4_path = os.path.join(UPLOAD_DIR, mp4_name)
            if _transcode_to_mp4(safe_path, mp4_path):
                results['video_url'] = f'/uploads/test_clips/{mp4_name}'
            else:
                results['video_url'] = f'/uploads/test_clips/{clip_path}'

        return jsonify(results)

    except Exception as e:
        logger.error(f"Process clip error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@detection_bp.route('/batch-test', methods=['POST'])
@jwt_required()
def batch_test():
    """
    Run accuracy test against all labeled clips.
    Uses JSON metadata for expected labels instead of filename parsing.
    """
    data = request.get_json(silent=True) or {}
    sample_fps = float(data.get('sample_fps', 10))
    results = []

    # Map labels to expected detection types
    label_to_expected = {
        'fighting': 'fighting', 'running': 'running', 'falling': 'falling',
        'loitering': 'loitering', 'no_activity': 'normal', 'no_person': 'normal',
    }

    for meta_file in sorted(glob.glob(os.path.join(UPLOAD_DIR, 'test_*.json'))):
        try:
            with open(meta_file) as mf:
                meta = json.load(mf)
        except Exception:
            continue

        file_id = meta.get('file_id', '')
        label = meta.get('label', 'unknown')
        expected = label_to_expected.get(label, 'normal')

        # Find video file
        video_file = None
        for ext in ALLOWED_EXTENSIONS:
            candidate = os.path.join(UPLOAD_DIR, f"test_{file_id}.{ext}")
            if os.path.exists(candidate):
                video_file = candidate
                break
        if not video_file:
            continue

        try:
            r = process_video_clip(video_file, sample_fps=sample_fps)
            detected = r['summary']['activity_types_found']
            abnormal = r['summary']['abnormal_detections']

            # Determine correctness
            if expected == 'normal':
                correct = abnormal == 0
            else:
                correct = expected in detected or abnormal > 0

            results.append({
                'file': meta.get('original_name', os.path.basename(video_file)),
                'label': label,
                'expected': expected,
                'detected': detected,
                'correct': correct,
                'status': r['summary']['status'],
                'detections': r['summary']['total_detections'],
                'abnormal': abnormal,
                'max_persons': r['summary']['max_persons_detected'],
                'duration': r['video_info']['duration_sec'],
                'processing_time': r['processing']['processing_time_sec'],
            })
        except Exception as e:
            results.append({
                'file': meta.get('original_name', file_id),
                'label': label, 'expected': expected,
                'detected': [], 'correct': False,
                'error': str(e),
            })

    correct_count = sum(1 for r in results if r.get('correct', False))
    accuracy = round(correct_count / len(results) * 100, 1) if results else 0

    return jsonify({
        'results': results,
        'total': len(results),
        'correct': correct_count,
        'accuracy': accuracy,
    })


def _transcode_to_mp4(src, dst):
    """Transcode video to MP4 (H.264) for browser compatibility."""
    try:
        import subprocess
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', src, '-c:v', 'libx264', '-preset', 'fast',
             '-crf', '28', '-c:a', 'aac', '-movflags', '+faststart', dst],
            capture_output=True, timeout=120,
        )
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Transcode failed: {e}")
        return False


def _safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except:
        pass


def process_video_clip(filepath, sample_fps=10):
    """
    Process a video file frame-by-frame through the activity detector.
    Returns a timeline of detected activities with per-frame keypoint data.
    """
    from services.activity_detector import ActivityDetector

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise ValueError("Could not open video file")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize detector
    detector = ActivityDetector(model_name='yolov8s-pose.pt', gpu_id=0)

    # Process every Nth frame based on requested sample_fps
    sample_fps = max(1, min(sample_fps, fps))  # clamp
    process_every = max(1, int(fps / sample_fps))

    timeline = []
    frame_results = []  # per-frame detail
    frame_idx = 0
    processed = 0
    start_time = time.time()
    current_activity = None
    max_persons = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % process_every == 0:
            try:
                result = detector.detect(frame)
                activity_type = result.get('type', 'normal')
                is_abnormal = result.get('is_abnormal', False)
                confidence = result.get('confidence', 0)
                severity = result.get('severity', 'low')
                description = result.get('description', '')
                persons = result.get('persons', [])
                person_count = len(persons)
                max_persons = max(max_persons, person_count)

                timestamp_sec = frame_idx / fps

                # Store per-frame result with skeleton data for visualization
                frame_result = {
                    'frame': frame_idx,
                    'time': round(timestamp_sec, 2),
                    'activity': activity_type,
                    'abnormal': is_abnormal,
                    'confidence': round(confidence, 3),
                    'severity': severity,
                    'persons': person_count,
                }

                # Include simplified skeleton data (keypoints + bbox) for overlay
                if persons:
                    frame_result['skeletons'] = []
                    for p in persons:
                        skel = {}
                        if p.get('keypoints'):
                            skel['keypoints'] = p['keypoints']
                        if p.get('confidences'):
                            skel['confidences'] = p['confidences']
                        if p.get('bbox'):
                            skel['bbox'] = p['bbox']
                        frame_result['skeletons'].append(skel)

                frame_results.append(frame_result)

                # Track activity segments (merge consecutive same-type)
                if activity_type != current_activity:
                    if current_activity and current_activity != 'normal':
                        # Close previous segment
                        timeline[-1]['end_time'] = round(timestamp_sec, 2)
                        timeline[-1]['end_frame'] = frame_idx

                    if activity_type != 'normal' or is_abnormal:
                        timeline.append({
                            'activity': activity_type,
                            'is_abnormal': is_abnormal,
                            'severity': severity,
                            'confidence': round(confidence, 3),
                            'description': description,
                            'start_time': round(timestamp_sec, 2),
                            'start_frame': frame_idx,
                            'end_time': round(timestamp_sec, 2),
                            'end_frame': frame_idx,
                            'person_count': person_count,
                        })
                    current_activity = activity_type
                elif current_activity and current_activity != 'normal' and len(timeline) > 0:
                    # Extend current segment
                    timeline[-1]['end_time'] = round(timestamp_sec, 2)
                    timeline[-1]['end_frame'] = frame_idx
                    timeline[-1]['person_count'] = max(timeline[-1]['person_count'], person_count)
                    # Update confidence to max seen
                    if confidence > timeline[-1]['confidence']:
                        timeline[-1]['confidence'] = round(confidence, 3)

                processed += 1

            except Exception as e:
                logger.debug(f"Frame {frame_idx} detection error: {e}")

        frame_idx += 1

    cap.release()
    processing_time = round(time.time() - start_time, 2)

    # Summary statistics
    abnormal_count = sum(1 for t in timeline if t['is_abnormal'])
    activity_types = list(set(t['activity'] for t in timeline))

    return {
        'video_info': {
            'filename': os.path.basename(filepath),
            'resolution': f'{width}x{height}',
            'fps': round(fps, 1),
            'total_frames': total_frames,
            'duration_sec': round(duration, 2),
            'duration_str': f'{int(duration // 60)}:{int(duration % 60):02d}',
        },
        'processing': {
            'frames_processed': processed,
            'process_every_n': process_every,
            'sample_fps': round(sample_fps, 1),
            'processing_time_sec': processing_time,
            'fps_achieved': round(processed / processing_time, 1) if processing_time > 0 else 0,
        },
        'summary': {
            'total_detections': len(timeline),
            'abnormal_detections': abnormal_count,
            'activity_types_found': activity_types,
            'max_persons_detected': max_persons,
            'status': 'abnormal_detected' if abnormal_count > 0 else 'all_normal',
        },
        'timeline': timeline,
        'frame_results': frame_results,
    }
