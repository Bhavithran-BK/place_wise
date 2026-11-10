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
OBJECTS_DIR = STORAGE_DIR / "objects"
RESULTS_DIR = STORAGE_DIR / "results"
CLEAN_BG_DIR = STORAGE_DIR / "demo_clean_bg"

for d in [STORAGE_DIR, UPLOADS_DIR, MASKS_DIR, OBJECTS_DIR, RESULTS_DIR, CLEAN_BG_DIR]:
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

# Gnani Voice AI Config (Gnani.ai Vachana Platform)
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_API_URL = os.getenv("GNANI_API_URL", "https://api.vachana.ai/stt/v3")
GNANI_LANG = os.getenv("GNANI_LANG", "en-IN")
GNANI_TTS_URL = os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")

# LLM Instruction Understanding Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")

# 15 MVP Classes specified in PLACEWISE_YOLOv8_Segmentation_Annotation_Plan.md
MVP_CLASSES = [
    "sofa", "chair", "table", "tv", "bookshelf", "bed", "cupboard",
    "potted_plant", "lamp", "bowl", "refrigerator", "washing_machine",
    "fan", "box", "other_object"
]

# Synonyms and COCO mapping into the 15 MVP classes
CLASS_MAPPINGS = {
    "couch": "sofa",
    "dining table": "table",
    "desk": "table",
    "coffee table": "table",
    "tea table": "table",
    "wardrobe": "cupboard",
    "cabinet": "cupboard",
    "shelf": "bookshelf",
    "bookcase": "bookshelf",
    "plant": "potted_plant",
    "potted plant": "potted_plant",
    "flowerpot": "potted_plant",
    "television": "tv",
    "monitor": "tv",
    "screen": "tv",
    "stool": "chair",
    "armchair": "chair",
    "seat": "chair",
    "boxes": "box",
    "counter": "table",
    "dish": "bowl",
    "cup": "bowl",
    "bottle": "other_object",
    "clock": "other_object",
    "vase": "other_object",
    "laptop": "other_object",
    "sink": "other_object",
    "book": "other_object"
}

# Categories
CLASS_CATEGORIES = {
    "sofa": "furniture",
    "chair": "furniture",
    "table": "furniture",
    "bed": "furniture",
    "bookshelf": "furniture",
    "cupboard": "furniture",
    "tv": "appliances",
    "refrigerator": "appliances",
    "washing_machine": "appliances",
    "fan": "appliances",
    "potted_plant": "household",
    "lamp": "household",
    "bowl": "household",
    "box": "household",
    "other_object": "household"
}

# Fixed objects (never moved by automated layout engines)
FIXED_CLASSES = {
    "tv", "bookshelf", "cupboard", "refrigerator", "washing_machine",
    "fan", "sink"
}

# Target classes recognized by detector
TARGET_CLASSES = set(MVP_CLASSES).union(CLASS_MAPPINGS.keys())
