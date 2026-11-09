import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

# Attempt loading .env from BASE_DIR or ROOT_DIR
def _load_env_file():
    for p in [BASE_DIR / ".env", ROOT_DIR / ".env"]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k and k not in os.environ:
                            os.environ[k] = v

_load_env_file()

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

# Gnani Voice AI Config
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_API_URL = os.getenv("GNANI_API_URL", "https://asr.gnani.ai/api/v1/asr")
GNANI_LANG = os.getenv("GNANI_LANG", "en-IN")
GNANI_TTS_URL = os.getenv("GNANI_TTS_URL", "https://tts.gnani.ai/api/v1/tts")

# LLM Instruction Understanding Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")

# Supported room furniture & indoor objects
TARGET_CLASSES = {
    "chair", "couch", "sofa", "bed", "dining table", "table", 
    "tv", "laptop", "potted plant", "plant", "book", "clock", 
    "vase", "cup", "bowl", "bottle", "refrigerator", "microwave", 
    "oven", "sink", "bookshelf", "shelf", "desk", "lamp"
}

