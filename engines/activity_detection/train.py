"""
Train the Pose-LSTM activity classifier.

Usage:
    python -m engines.activity_detection.train \
        --data /mnt/data/training/pose_sequences.npz \
        --output /mnt/data/models/ \
        --epochs 50 \
        --batch-size 64

Produces:
    - activity_lstm.pt          — best model checkpoint
    - training_log.json         — per-epoch metrics
    - confusion_matrix.png      — test set confusion matrix
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engines.activity_detection.lstm_model import PoseLSTM, ACTIVITY_CLASSES, NUM_CLASSES

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def load_data(data_path: str, val_split: float = 0.15, test_split: float = 0.10):
    """
    Load .npz data and create train/val/test splits.
    """
    logger.info(f"Loading data from {data_path}")
    data = np.load(data_path)
    X = data['sequences'].astype(np.float32)  # (N, 30, 51)
    y = data['labels'].astype(np.int64)       # (N,)

    logger.info(f"  Total samples: {len(X)}")
    for i, name in enumerate(ACTIVITY_CLASSES):
        count = (y == i).sum()
        logger.info(f"    {name}: {count} ({count/len(y)*100:.1f}%)")

    # First split: train+val vs test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=test_split, random_state=42, stratify=y
    )

    # Second split: train vs val
    val_ratio = val_split / (1 - test_split)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=val_ratio, random_state=42, stratify=y_trainval
    )

    logger.info(f"  Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    return X_train, X_val, X_test, y_train, y_val, y_test


def create_weighted_sampler(labels: np.ndarray) -> WeightedRandomSampler:
    """
    Create a weighted sampler to handle class imbalance.
    Under-represented classes get sampled more frequently.
    """
    class_counts = np.bincount(labels, minlength=NUM_CLASSES)
    class_weights = 1.0 / np.maximum(class_counts, 1).astype(np.float64)
    sample_weights = class_weights[labels]
    return WeightedRandomSampler(
        weights=torch.from_numpy(sample_weights),
        num_samples=len(labels),
        replacement=True,
    )


def train_epoch(model, loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for batch_x, batch_y in loader:
        batch_x = batch_x.to(device)
        batch_y = batch_y.to(device)

        optimizer.zero_grad()
        logits = model(batch_x)
        loss = criterion(logits, batch_y)
        loss.backward()

        # Gradient clipping to prevent exploding gradients in LSTM
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        total_loss += loss.item() * batch_x.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == batch_y).sum().item()
        total += batch_x.size(0)

    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    """Evaluate on validation/test set."""
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    for batch_x, batch_y in loader:
        batch_x = batch_x.to(device)
        batch_y = batch_y.to(device)

        logits = model(batch_x)
        loss = criterion(logits, batch_y)

        total_loss += loss.item() * batch_x.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == batch_y).sum().item()
        total += batch_x.size(0)

        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(batch_y.cpu().numpy())

    return total_loss / total, correct / total, np.array(all_preds), np.array(all_labels)


def save_confusion_matrix(y_true, y_pred, output_dir, class_names):
    """Save confusion matrix as image."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        cm = confusion_matrix(y_true, y_pred)
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
        ax.figure.colorbar(im, ax=ax)

        ax.set(
            xticks=np.arange(len(class_names)),
            yticks=np.arange(len(class_names)),
            xticklabels=class_names,
            yticklabels=class_names,
            ylabel='True label',
            xlabel='Predicted label',
            title='Confusion Matrix',
        )

        # Add text annotations
        for i in range(len(class_names)):
            for j in range(len(class_names)):
                ax.text(j, i, str(cm[i, j]),
                        ha='center', va='center',
                        color='white' if cm[i, j] > cm.max() / 2 else 'black')

        plt.tight_layout()
        path = os.path.join(output_dir, 'confusion_matrix.png')
        plt.savefig(path, dpi=150)
        plt.close()
        logger.info(f"Confusion matrix saved to {path}")
    except Exception as e:
        logger.warning(f"Could not save confusion matrix: {e}")


def train(
    data_path: str,
    output_dir: str,
    epochs: int = 50,
    batch_size: int = 64,
    lr: float = 1e-3,
    hidden_dim: int = 128,
    num_layers: int = 2,
    dropout: float = 0.3,
    patience: int = 10,
):
    """
    Full training pipeline.
    """
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")

    # Load data
    X_train, X_val, X_test, y_train, y_val, y_test = load_data(data_path)

    # Create datasets and loaders
    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_ds = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    test_ds = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))

    # Weighted sampler for imbalanced classes
    sampler = create_weighted_sampler(y_train)

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=2)

    # Model
    model = PoseLSTM(
        hidden_dim=hidden_dim,
        num_layers=num_layers,
        dropout=dropout,
    ).to(device)

    param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model parameters: {param_count:,}")

    # Class-weighted loss
    class_counts = np.bincount(y_train, minlength=NUM_CLASSES).astype(np.float32)
    class_weights = 1.0 / np.maximum(class_counts, 1)
    class_weights = class_weights / class_weights.sum() * NUM_CLASSES
    criterion = nn.CrossEntropyLoss(
        weight=torch.from_numpy(class_weights).to(device)
    )

    # Optimizer + scheduler
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=5, min_lr=1e-6
    )

    # Training loop
    best_val_f1 = 0
    patience_counter = 0
    training_log = []

    logger.info(f"\n{'='*60}")
    logger.info(f"Starting training: {epochs} epochs, batch_size={batch_size}")
    logger.info(f"{'='*60}\n")

    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, val_preds, val_labels = evaluate(model, val_loader, criterion, device)
        val_f1 = f1_score(val_labels, val_preds, average='weighted', zero_division=0)

        # Update scheduler based on validation F1
        scheduler.step(val_f1)

        log_entry = {
            'epoch': epoch,
            'train_loss': round(train_loss, 4),
            'train_acc': round(train_acc, 4),
            'val_loss': round(val_loss, 4),
            'val_acc': round(val_acc, 4),
            'val_f1': round(val_f1, 4),
            'lr': optimizer.param_groups[0]['lr'],
        }
        training_log.append(log_entry)

        # Logging
        marker = ''
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            marker = ' ★ BEST'
            # Save best model
            model_path = os.path.join(output_dir, 'activity_lstm.pt')
            torch.save({
                'model_state_dict': model.state_dict(),
                'class_names': ACTIVITY_CLASSES,
                'hidden_dim': hidden_dim,
                'num_layers': num_layers,
                'dropout': dropout,
                'epoch': epoch,
                'val_f1': val_f1,
                'val_acc': val_acc,
            }, model_path)
        else:
            patience_counter += 1

        logger.info(
            f"Epoch {epoch:3d}/{epochs} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.3f} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.3f} F1: {val_f1:.3f}{marker}"
        )

        # Early stopping
        if patience_counter >= patience:
            logger.info(f"\nEarly stopping at epoch {epoch} (no improvement for {patience} epochs)")
            break

    # Save training log
    log_path = os.path.join(output_dir, 'training_log.json')
    with open(log_path, 'w') as f:
        json.dump(training_log, f, indent=2)

    # Final evaluation on test set
    logger.info(f"\n{'='*60}")
    logger.info("Final evaluation on test set")
    logger.info(f"{'='*60}\n")

    # Load best model
    best_ckpt = torch.load(os.path.join(output_dir, 'activity_lstm.pt'), map_location=device)
    model.load_state_dict(best_ckpt['model_state_dict'])

    test_loss, test_acc, test_preds, test_labels = evaluate(model, test_loader, criterion, device)
    test_f1 = f1_score(test_labels, test_preds, average='weighted', zero_division=0)

    logger.info(f"Test Accuracy: {test_acc:.3f}")
    logger.info(f"Test F1 Score: {test_f1:.3f}")
    logger.info(f"\nClassification Report:\n")

    # Only include classes that appear in the data
    present_labels = sorted(set(test_labels) | set(test_preds))
    present_names = [ACTIVITY_CLASSES[i] for i in present_labels]
    logger.info(classification_report(
        test_labels, test_preds,
        labels=present_labels,
        target_names=present_names,
        zero_division=0,
    ))

    # Save confusion matrix
    save_confusion_matrix(test_labels, test_preds, output_dir, present_names)

    # Save final results
    results = {
        'test_accuracy': round(test_acc, 4),
        'test_f1': round(test_f1, 4),
        'best_epoch': best_ckpt['epoch'],
        'best_val_f1': round(best_ckpt['val_f1'], 4),
        'total_params': param_count,
        'training_date': datetime.utcnow().isoformat(),
        'data_path': data_path,
    }
    results_path = os.path.join(output_dir, 'results.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nResults saved to {results_path}")
    logger.info(f"Model saved to {os.path.join(output_dir, 'activity_lstm.pt')}")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train Pose-LSTM activity classifier')
    parser.add_argument('--data', type=str, default='/mnt/data/training/pose_sequences.npz',
                        help='Path to extracted pose sequences .npz')
    parser.add_argument('--output', type=str, default='/mnt/data/models/',
                        help='Output directory for model and logs')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--lr', type=float, default=1e-3)
    parser.add_argument('--hidden-dim', type=int, default=128)
    parser.add_argument('--num-layers', type=int, default=2)
    parser.add_argument('--dropout', type=float, default=0.3)
    parser.add_argument('--patience', type=int, default=10)
    args = parser.parse_args()

    train(
        data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        dropout=args.dropout,
        patience=args.patience,
    )
