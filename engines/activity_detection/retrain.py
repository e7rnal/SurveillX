"""
Retrain LSTM model using user-labeled video clips.

Reads JSON metadata sidecars from the uploads directory, extracts poses
from each labeled clip, creates training sequences, and fine-tunes
the existing LSTM model (or trains from scratch).
"""
import os
import json
import glob
import time
import shutil
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Label mapping must match classifier._lstm_classes
LABEL_MAP = {
    'fighting': 1,
    'running': 2,
    'falling': 3,
    'loitering': 0,     # treated as "normal" variant
    'no_activity': 0,   # normal
    'no_person': 0,     # normal
}

CLASS_NAMES = ['normal', 'fighting', 'running', 'falling']

# Pose extraction settings
SEQ_LEN = 30
STRIDE = 15
TARGET_FPS = 10


def retrain_from_labeled_clips(upload_dir: str):
    """
    Main entry point: scan labeled clips, extract poses, retrain LSTM.
    Called from background thread by the /retrain API endpoint.
    """
    import torch
    from engines.activity_detection.pose_extractor import (
        extract_keypoints_from_video,
        create_sequences,
    )

    logger.info("=== RETRAIN: Starting model retraining from labeled clips ===")
    start_time = time.time()

    # 1. Collect all labeled clips
    meta_files = sorted(glob.glob(os.path.join(upload_dir, 'test_*.json')))
    if not meta_files:
        logger.error("No labeled clips found")
        return

    logger.info(f"Found {len(meta_files)} labeled clips")

    # 2. Extract poses from each clip
    all_sequences = []
    all_labels = []
    label_counts = {}

    allowed_exts = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'mpg', 'mpeg'}

    for meta_path in meta_files:
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except Exception:
            continue

        file_id = meta.get('file_id', '')
        label = meta.get('label', '')
        if label not in LABEL_MAP:
            logger.warning(f"Unknown label '{label}' for {file_id}, skipping")
            continue

        label_idx = LABEL_MAP[label]

        # Find video file
        video_path = None
        for ext in allowed_exts:
            candidate = os.path.join(upload_dir, f"test_{file_id}.{ext}")
            if os.path.exists(candidate):
                video_path = candidate
                break

        if not video_path:
            logger.warning(f"Video not found for {file_id}")
            continue

        try:
            # Extract keypoints
            kps = extract_keypoints_from_video(video_path, target_fps=TARGET_FPS)
            if kps is None or len(kps) < 5:
                logger.warning(f"Too few keypoints from {file_id} ({len(kps) if kps is not None else 0} frames)")
                continue

            # Create sequences
            seqs = create_sequences(kps, seq_len=SEQ_LEN, stride=STRIDE)
            if len(seqs) == 0:
                # Pad short clips
                while len(kps) < SEQ_LEN:
                    kps = np.concatenate([kps, kps[-1:]], axis=0)
                seqs = [kps[:SEQ_LEN]]

            all_sequences.extend(seqs)
            all_labels.extend([label_idx] * len(seqs))
            label_counts[label] = label_counts.get(label, 0) + len(seqs)
            logger.info(f"  {meta.get('original_name', file_id)}: {len(seqs)} sequences → {label}")

        except Exception as e:
            logger.error(f"Error processing {file_id}: {e}")
            continue

    if len(all_sequences) < 5:
        logger.error(f"Not enough sequences ({len(all_sequences)}). Need at least 5.")
        return

    logger.info(f"Total sequences: {len(all_sequences)}")
    logger.info(f"Label distribution: {label_counts}")

    # 3. Combine with existing training data if available
    existing_data = '/mnt/data/training/activity_sequences.npz'
    if os.path.exists(existing_data):
        try:
            data = np.load(existing_data)
            existing_seqs = data['sequences']
            existing_labels = data['labels']
            logger.info(f"Loaded {len(existing_seqs)} existing sequences from training data")

            all_sequences = list(existing_seqs) + all_sequences
            all_labels = list(existing_labels) + all_labels
            logger.info(f"Combined total: {len(all_sequences)} sequences")
        except Exception as e:
            logger.warning(f"Could not load existing data: {e}")

    X = np.array(all_sequences, dtype=np.float32)
    y = np.array(all_labels, dtype=np.int64)

    # Reshape if needed (sequences should be N x SEQ_LEN x 51)
    if X.ndim == 4:
        N, T, K, C = X.shape
        X = X.reshape(N, T, K * C)

    logger.info(f"Training data shape: X={X.shape}, y={y.shape}")
    logger.info(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    # 4. Train the model
    _train_lstm(X, y, upload_dir)

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"=== RETRAIN: Complete in {elapsed}s ===")


def _train_lstm(X, y, upload_dir):
    """Train or fine-tune the LSTM model."""
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler
    from sklearn.model_selection import train_test_split
    from engines.activity_detection.lstm_model import PoseLSTM

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on device: {device}")

    # Split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Class weights for imbalance
    classes, counts = np.unique(y_train, return_counts=True)
    total = len(y_train)
    class_weights = total / (len(classes) * counts)
    sample_weights = np.array([class_weights[c] for c in y_train])

    sampler = WeightedRandomSampler(
        weights=torch.DoubleTensor(sample_weights),
        num_samples=len(sample_weights),
        replacement=True
    )

    train_ds = TensorDataset(
        torch.from_numpy(X_train).float(),
        torch.from_numpy(y_train).long()
    )
    val_ds = TensorDataset(
        torch.from_numpy(X_val).float(),
        torch.from_numpy(y_val).long()
    )

    train_loader = DataLoader(train_ds, batch_size=64, sampler=sampler, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=64)

    # Model
    num_features = X.shape[2]
    num_classes = len(CLASS_NAMES)
    seq_len = X.shape[1]

    model = PoseLSTM(
        input_size=num_features,
        hidden_size=128,
        num_layers=2,
        num_classes=num_classes,
        dropout=0.3,
    ).to(device)

    # Try to load existing weights for fine-tuning
    model_dir = os.path.join(os.path.dirname(__file__), '')
    model_path = os.path.join(model_dir, 'activity_lstm.pt')
    if os.path.exists(model_path):
        try:
            checkpoint = torch.load(model_path, map_location=device)
            model.load_state_dict(checkpoint['model_state_dict'])
            logger.info("Loaded existing model weights for fine-tuning")
        except Exception as e:
            logger.warning(f"Could not load existing weights: {e}. Training from scratch.")

    # Loss and optimizer
    weight_tensor = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimizer = optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # Training loop
    best_val_loss = float('inf')
    patience = 10
    patience_counter = 0
    epochs = 50

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0

        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_X)
            loss = criterion(logits, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            train_loss += loss.item()
            _, predicted = logits.max(1)
            train_total += batch_y.size(0)
            train_correct += predicted.eq(batch_y).sum().item()

        # Validate
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                logits = model(batch_X)
                loss = criterion(logits, batch_y)
                val_loss += loss.item()
                _, predicted = logits.max(1)
                val_total += batch_y.size(0)
                val_correct += predicted.eq(batch_y).sum().item()

        avg_val_loss = val_loss / max(len(val_loader), 1)
        train_acc = train_correct / max(train_total, 1)
        val_acc = val_correct / max(val_total, 1)

        scheduler.step(avg_val_loss)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            logger.info(
                f"Epoch {epoch+1}/{epochs}: "
                f"train_acc={train_acc:.3f} val_acc={val_acc:.3f} "
                f"val_loss={avg_val_loss:.4f}"
            )

        # Early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0

            # Save best model
            # Backup existing
            if os.path.exists(model_path):
                backup = model_path + '.bak'
                shutil.copy2(model_path, backup)

            torch.save({
                'model_state_dict': model.state_dict(),
                'class_names': CLASS_NAMES,
                'input_size': num_features,
                'hidden_size': 128,
                'num_layers': 2,
                'num_classes': num_classes,
                'seq_len': seq_len,
                'val_accuracy': val_acc,
                'train_accuracy': train_acc,
                'epoch': epoch + 1,
            }, model_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break

    logger.info(f"Best val loss: {best_val_loss:.4f}, model saved to {model_path}")
