"""
Pose Extractor — batch-process video clips through YOLOv8s-pose to produce
normalised keypoint sequences for LSTM training.

For each video:
  1. Sample frames at a target FPS (default 10)
  2. Run YOLOv8s-pose to get per-person keypoints
  3. Pick the primary person (or pair for multi-person activities)
  4. Normalize keypoints relative to hip centre (translation-invariant)
  5. Produce sliding windows of 30 frames → each window is one sample

Output: .npz files with arrays:
  - sequences: (N, 30, 51)  — N sliding windows
  - labels:    (N,)          — integer class labels
"""
import os
import sys
import json
import glob
import random
import logging
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# COCO keypoint order (17 keypoints)
COCO_KP_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]

# Class label mapping
CLASS_MAP = {'normal': 0, 'fighting': 1, 'running': 2, 'falling': 3}
CLASS_NAMES = {v: k for k, v in CLASS_MAP.items()}

# Indices for hip centre (used for normalisation)
LEFT_HIP_IDX = 11
RIGHT_HIP_IDX = 12

SEQ_LEN = 30        # frames per sequence
STRIDE = 15          # sliding window stride (50% overlap)
TARGET_FPS = 10      # sample rate from video


def normalise_keypoints(kps: np.ndarray) -> np.ndarray:
    """
    Normalise keypoints relative to hip centre.

    Args:
        kps: (17, 3) array of [x, y, confidence]
    Returns:
        (51,) flattened array with hip-centred x,y and original confidence
    """
    # Hip centre
    hip_x = (kps[LEFT_HIP_IDX, 0] + kps[RIGHT_HIP_IDX, 0]) / 2
    hip_y = (kps[LEFT_HIP_IDX, 1] + kps[RIGHT_HIP_IDX, 1]) / 2

    # Compute body scale from shoulder width for scale-invariance
    left_shoulder = kps[5, :2]
    right_shoulder = kps[6, :2]
    body_scale = np.linalg.norm(left_shoulder - right_shoulder)
    if body_scale < 10:  # fallback if shoulders not detected
        body_scale = 100.0

    normalised = np.zeros_like(kps)
    normalised[:, 0] = (kps[:, 0] - hip_x) / body_scale
    normalised[:, 1] = (kps[:, 1] - hip_y) / body_scale
    normalised[:, 2] = kps[:, 2]  # keep confidence as-is

    return normalised.flatten()  # (51,)


def extract_keypoints_from_video(
    video_path: str,
    model: YOLO,
    target_fps: int = TARGET_FPS,
    max_persons: int = 2,
) -> List[np.ndarray]:
    """
    Extract per-frame keypoints from a video.

    Returns list of (51,) arrays for single-person activities,
    or (102,) arrays for two-person activities (fighting).
    For multi-person, we concatenate the two closest persons.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning(f"Cannot open: {video_path}")
        return []

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 25.0

    frame_interval = max(1, int(video_fps / target_fps))
    frames_keypoints = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            # Run pose detection
            results = model(frame, verbose=False)

            if results and len(results) > 0 and results[0].keypoints is not None:
                kps_data = results[0].keypoints.data.cpu().numpy()  # (N, 17, 3)

                if len(kps_data) == 0:
                    # No person detected — zero frame
                    frames_keypoints.append(np.zeros(51))
                elif max_persons == 1 or len(kps_data) == 1:
                    # Single person — normalise and flatten
                    frames_keypoints.append(normalise_keypoints(kps_data[0]))
                else:
                    # Multi-person: pick the two with highest confidence
                    confs = [kp[:, 2].mean() for kp in kps_data]
                    sorted_idx = np.argsort(confs)[::-1][:2]
                    kp1 = normalise_keypoints(kps_data[sorted_idx[0]])
                    if len(sorted_idx) >= 2:
                        kp2 = normalise_keypoints(kps_data[sorted_idx[1]])
                    else:
                        kp2 = np.zeros(51)
                    # For single-person model, just use first person
                    frames_keypoints.append(kp1)
            else:
                frames_keypoints.append(np.zeros(51))

        frame_idx += 1

    cap.release()
    return frames_keypoints


def extract_keypoints_from_image_dir(
    image_dir: str,
    model: YOLO,
    frame_skip: int = 1,
) -> List[np.ndarray]:
    """
    Extract keypoints from a directory of image frames (e.g. UR Fall dataset).

    Args:
        image_dir: directory containing sequentially-named image files
        model: YOLOv8-pose model
        frame_skip: process every Nth frame
    Returns:
        list of (51,) normalised keypoint arrays
    """
    # Gather and sort image files
    exts = ('*.png', '*.jpg', '*.jpeg', '*.bmp')
    images = []
    for ext in exts:
        images.extend(glob.glob(os.path.join(image_dir, ext)))
    images.sort()

    if not images:
        return []

    frames_keypoints = []
    for i, img_path in enumerate(images):
        if i % frame_skip != 0:
            continue

        frame = cv2.imread(img_path)
        if frame is None:
            frames_keypoints.append(np.zeros(51))
            continue

        results = model(frame, verbose=False)

        if results and len(results) > 0 and results[0].keypoints is not None:
            kps_data = results[0].keypoints.data.cpu().numpy()
            if len(kps_data) > 0:
                frames_keypoints.append(normalise_keypoints(kps_data[0]))
            else:
                frames_keypoints.append(np.zeros(51))
        else:
            frames_keypoints.append(np.zeros(51))

    return frames_keypoints


def create_sequences(
    keypoints: List[np.ndarray],
    seq_len: int = SEQ_LEN,
    stride: int = STRIDE,
) -> np.ndarray:
    """
    Create sliding window sequences from frame-level keypoints.

    Args:
        keypoints: list of (51,) arrays
        seq_len: window length
        stride: step between windows
    Returns:
        (N, seq_len, 51) array
    """
    if len(keypoints) < seq_len:
        # Pad short videos with zeros
        padding = [np.zeros(51)] * (seq_len - len(keypoints))
        keypoints = keypoints + padding
        return np.array([keypoints])

    sequences = []
    for i in range(0, len(keypoints) - seq_len + 1, stride):
        seq = np.array(keypoints[i:i + seq_len])
        sequences.append(seq)

    return np.array(sequences) if sequences else np.zeros((0, seq_len, 51))


def process_dataset(
    dataset_dirs: List[dict],
    output_dir: str,
    model_path: str = 'yolov8s-pose.pt',
    target_fps: int = TARGET_FPS,
    seq_len: int = SEQ_LEN,
    stride: int = STRIDE,
    max_videos: int = 0,
):
    """
    Process multiple dataset directories and save extracted sequences.

    Args:
        dataset_dirs: list of dicts, each with:
            - 'path': directory containing videos or image subdirectories
            - 'label': class name (e.g. 'fighting', 'falling')
            - 'type': 'videos' (default) or 'image_dirs'
        output_dir: where to save .npz files
        model_path: YOLOv8-pose model path
        target_fps: sampling rate for videos
        seq_len: sequence length
        stride: sliding window stride
        max_videos: limit per class (0 = no limit)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load YOLOv8-pose model
    logger.info(f"Loading YOLO model: {model_path}")
    model = YOLO(model_path)

    all_sequences = []
    all_labels = []
    stats = {}

    for ds in dataset_dirs:
        source_dir = ds['path']
        label_name = ds['label']
        label_id = CLASS_MAP.get(label_name, 0)
        source_type = ds.get('type', 'videos')

        class_seqs = 0
        source_count = 0

        if source_type == 'image_dirs':
            # UR Fall style: each subdirectory is one clip
            subdirs = sorted([
                os.path.join(source_dir, d)
                for d in os.listdir(source_dir)
                if os.path.isdir(os.path.join(source_dir, d))
            ])

            if max_videos > 0 and len(subdirs) > max_videos:
                random.seed(42)
                subdirs = random.sample(subdirs, max_videos)

            logger.info(f"Processing {len(subdirs)} image dirs for class '{label_name}' from {source_dir}")
            source_count = len(subdirs)

            for si, sdir in enumerate(subdirs):
                if (si + 1) % 10 == 0 or si == 0:
                    logger.info(f"  [{label_name}] {si+1}/{len(subdirs)}: {os.path.basename(sdir)}")

                keypoints = extract_keypoints_from_image_dir(sdir, model, frame_skip=2)
                if not keypoints:
                    continue

                sequences = create_sequences(keypoints, seq_len, stride)
                if sequences.shape[0] == 0:
                    continue

                labels = np.full(sequences.shape[0], label_id, dtype=np.int64)
                all_sequences.append(sequences)
                all_labels.append(labels)
                class_seqs += sequences.shape[0]

        else:
            # Standard video files
            videos = []
            for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.webm', '*.mpg', '*.mpeg']:
                videos.extend(glob.glob(os.path.join(source_dir, ext)))
            videos.sort()

            if max_videos > 0 and len(videos) > max_videos:
                random.seed(42)
                videos = random.sample(videos, max_videos)

            logger.info(f"Processing {len(videos)} videos for class '{label_name}' from {source_dir}")
            source_count = len(videos)

            for vi, vpath in enumerate(videos):
                if (vi + 1) % 50 == 0 or vi == 0:
                    logger.info(f"  [{label_name}] {vi+1}/{len(videos)}: {os.path.basename(vpath)}")

                keypoints = extract_keypoints_from_video(vpath, model, target_fps)
                if not keypoints:
                    continue

                sequences = create_sequences(keypoints, seq_len, stride)
                if sequences.shape[0] == 0:
                    continue

                labels = np.full(sequences.shape[0], label_id, dtype=np.int64)
                all_sequences.append(sequences)
                all_labels.append(labels)
                class_seqs += sequences.shape[0]

        prev = stats.get(label_name, {'sources': 0, 'sequences': 0})
        stats[label_name] = {
            'sources': prev['sources'] + source_count,
            'sequences': prev['sequences'] + class_seqs,
        }
        logger.info(f"  {label_name}: {source_count} sources → {class_seqs} sequences")

    # Concatenate and save
    if all_sequences:
        X = np.concatenate(all_sequences, axis=0)
        y = np.concatenate(all_labels, axis=0)

        # Shuffle
        indices = np.arange(len(X))
        np.random.seed(42)
        np.random.shuffle(indices)
        X = X[indices]
        y = y[indices]

        # Save
        output_path = os.path.join(output_dir, 'pose_sequences.npz')
        np.savez_compressed(output_path, sequences=X, labels=y)
        logger.info(f"Saved {X.shape[0]} sequences to {output_path}")
        logger.info(f"  Shape: X={X.shape}, y={y.shape}")

        # Save stats
        stats_path = os.path.join(output_dir, 'extraction_stats.json')
        stats['total_sequences'] = int(X.shape[0])
        stats['class_distribution'] = {
            CLASS_NAMES[i]: int((y == i).sum()) for i in range(len(CLASS_MAP))
        }
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Stats saved to {stats_path}")
    else:
        logger.error("No sequences extracted!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract pose sequences from video datasets')
    parser.add_argument('--config', type=str, help='JSON config file with dataset dirs')
    parser.add_argument('--output', type=str, default='/mnt/data/training',
                        help='Output directory for .npz files')
    parser.add_argument('--model', type=str, default='/home/ubuntu/surveillx-backend/yolov8s-pose.pt',
                        help='YOLOv8-pose model path')
    parser.add_argument('--fps', type=int, default=TARGET_FPS)
    parser.add_argument('--seq-len', type=int, default=SEQ_LEN)
    parser.add_argument('--stride', type=int, default=STRIDE)
    parser.add_argument('--max-videos', type=int, default=0,
                        help='Max videos per class (0=all)')
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            dataset_dirs = json.load(f)
    else:
        # Default: process all available datasets
        dataset_dirs = [
            # Fighting — Surv Fight + RWF-2000
            {'path': '/mnt/data/datasets/surv-fight/fight', 'label': 'fighting', 'type': 'videos'},
            {'path': '/mnt/data/datasets/rwf2000/train/Fight', 'label': 'fighting', 'type': 'videos'},
            {'path': '/mnt/data/datasets/rwf2000/val/Fight', 'label': 'fighting', 'type': 'videos'},
            # Normal — Surv noFight + RWF-2000 NonFight + UR Fall ADL
            {'path': '/mnt/data/datasets/surv-fight/noFight', 'label': 'normal', 'type': 'videos'},
            {'path': '/mnt/data/datasets/rwf2000/train/NonFight', 'label': 'normal', 'type': 'videos'},
            {'path': '/mnt/data/datasets/rwf2000/val/NonFight', 'label': 'normal', 'type': 'videos'},
            # Falling — UR Fall (image directories, fall-* subdirs)
            {'path': '/mnt/data/datasets/urfall/fall', 'label': 'falling', 'type': 'image_dirs'},
            # Normal — UR Fall ADL (image directories, adl-* subdirs)  
            {'path': '/mnt/data/datasets/urfall/adl', 'label': 'normal', 'type': 'image_dirs'},
        ]
        # Filter out non-existent directories
        dataset_dirs = [d for d in dataset_dirs if os.path.exists(d['path'])]

    process_dataset(
        dataset_dirs=dataset_dirs,
        output_dir=args.output,
        model_path=args.model,
        target_fps=args.fps,
        seq_len=args.seq_len,
        stride=args.stride,
        max_videos=args.max_videos,
    )
