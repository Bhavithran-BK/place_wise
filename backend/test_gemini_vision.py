import os
import json
import base64
import requests
from app.core.config import GEMINI_API_KEY

from pathlib import Path
img_path = Path(__file__).parent / "storage" / "uploads" / "demo_room_01.jpg"
with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

prompt = (
    "Detect all visible indoor furniture pieces in this room image (e.g. sofa, tv, table, chair, bookshelf, plant).\n"
    "Return a JSON list of objects, each with:\n"
    "- 'class': class name in lowercase (e.g. 'tv', 'sofa', 'table', 'chair', 'bookshelf', 'plant')\n"
    "- 'confidence': float between 0.85 and 0.99\n"
    "- 'box_2d': [ymin, xmin, ymax, xmax] normalized on a 0 to 1000 scale.\n"
    "Important: The TV is ONLY the black wall-mounted television screen, NOT the whole room."
)

payload = {
    "contents": [{
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
        ]
    }],
    "generationConfig": {
        "response_mime_type": "application/json"
    }
}

r = requests.post(url, json=payload, timeout=15)
print("Status:", r.status_code)
if r.ok:
    data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    print("Detected Objects:")
    print(text)
else:
    print("Error:", r.text)
