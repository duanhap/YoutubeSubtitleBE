from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MODEL_CONFIG = {
    "model_size": "base",
    "device": "cpu",
    "compute_type": "int8",
    "language": "ja"
}
