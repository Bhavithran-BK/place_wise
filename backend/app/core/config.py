import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
MASKS_DIR = STORAGE_DIR / "masks"
RESULTS_DIR = STORAGE_DIR / "results"

for d in [STORAGE_DIR, UPLOADS_DIR, MASKS_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Server Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "*"
]

# Supported room furniture classes
TARGET_CLASSES = {
    "chair", "couch", "sofa", "bed", "dining table", "table", 
    "tv", "laptop", "potted plant", "plant", "book", "clock", 
    "vase", "refrigerator", "microwave", "oven", "sink"
}

