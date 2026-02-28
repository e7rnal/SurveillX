"""
Pose-LSTM Activity Classifier Model.

A bidirectional LSTM that takes sequences of skeleton keypoints and
classifies activities: normal, fighting, running, falling.

Input:  (batch, seq_len, 51)  — 30 frames × 17 keypoints × 3 (x,y,conf)
Output: (batch, num_classes)  — class logits
"""
import torch
import torch.nn as nn


# Class labels — order matters, must match training data
ACTIVITY_CLASSES = ['normal', 'fighting', 'running', 'falling']
NUM_CLASSES = len(ACTIVITY_CLASSES)

# Keypoint feature dims: 17 keypoints × 3 (x, y, confidence)
NUM_KEYPOINTS = 17
FEATURES_PER_KP = 3
INPUT_DIM = NUM_KEYPOINTS * FEATURES_PER_KP  # 51


class PoseLSTM(nn.Module):
    """
    Bidirectional LSTM for skeleton-based activity recognition.

    Architecture:
        Input (51) → LayerNorm → BiLSTM(128, 2 layers) → Attention → FC(128) → FC(num_classes)

    ~500K parameters, fits easily on any GPU.
    """

    def __init__(
        self,
        input_dim: int = INPUT_DIM,
        hidden_dim: int = 128,
        num_layers: int = 2,
        num_classes: int = NUM_CLASSES,
        dropout: float = 0.3,
        seq_len: int = 30,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.seq_len = seq_len

        # Normalize input features
        self.input_norm = nn.LayerNorm(input_dim)

        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Attention mechanism — learn which frames matter most
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, input_dim) — keypoint sequences
        Returns:
            logits: (batch, num_classes)
        """
        # Normalize inputs
        x = self.input_norm(x)

        # LSTM encoding
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden_dim*2)

        # Attention pooling — weighted sum of all time steps
        attn_weights = self.attention(lstm_out)       # (batch, seq_len, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = torch.sum(lstm_out * attn_weights, dim=1)  # (batch, hidden_dim*2)

        # Classify
        logits = self.classifier(context)  # (batch, num_classes)
        return logits

    def predict(self, x: torch.Tensor) -> tuple:
        """
        Run inference and return predicted class + confidence.

        Args:
            x: (1, seq_len, input_dim) or (seq_len, input_dim)
        Returns:
            (class_name, confidence)
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)

        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1)
            conf, idx = probs.max(dim=1)
            class_name = ACTIVITY_CLASSES[idx.item()]
            return class_name, conf.item()


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == '__main__':
    model = PoseLSTM()
    print(f"PoseLSTM: {count_parameters(model):,} parameters")
    # Test forward pass
    dummy = torch.randn(4, 30, 51)
    out = model(dummy)
    print(f"Input:  {dummy.shape}")
    print(f"Output: {out.shape}")
    # Test predict
    single = torch.randn(30, 51)
    cls, conf = model.predict(single)
    print(f"Predicted: {cls} ({conf:.2%})")
