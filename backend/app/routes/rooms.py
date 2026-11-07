import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image

from app.core.config import UPLOADS_DIR, STORAGE_DIR
from app.schemas.room import RoomUploadResponse, RoomMetadata

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

def get_room_meta_path(room_id: str) -> Path:
    return STORAGE_DIR / f"room_{room_id}.json"

def load_room_meta(room_id: str) -> dict:
    path = get_room_meta_path(room_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Room {room_id} not found")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_room_meta(room_id: str, data: dict):
    path = get_room_meta_path(room_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@router.post("", response_model=RoomUploadResponse)
async def upload_room_image(file: UploadFile = File(...)):
    """
    Step 1: Upload room photograph.
    Saves image, detects dimensions, and initializes room metadata.
    """
    ext = Path(file.filename or "room.jpg").suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, and WEBP formats supported")

    room_id = uuid.uuid4().hex[:8]
    saved_filename = f"{room_id}{ext}"
    dest_path = UPLOADS_DIR / saved_filename

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Validate image and get dimensions
    try:
        with Image.open(dest_path) as img:
            width, height = img.size
    except Exception as e:
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    now = datetime.now().isoformat()
    meta = {
        "room_id": room_id,
        "filename": saved_filename,
        "image_path": str(dest_path),
        "image_url": f"/storage/uploads/{saved_filename}",
        "width": width,
        "height": height,
        "created_at": now,
        "status": "uploaded",
        "detected_objects": [],
        "voice_transcript": None,
        "arrangement_plan": None
    }
    save_room_meta(room_id, meta)

    return RoomUploadResponse(
        room_id=room_id,
        filename=saved_filename,
        image_url=f"/storage/uploads/{saved_filename}",
        width=width,
        height=height,
        created_at=now,
        status="uploaded"
    )

@router.get("/{room_id}")
async def get_room(room_id: str):
    """Retrieve current state of a room."""
    return load_room_meta(room_id)

@router.get("")
async def list_rooms():
    """List all available rooms."""
    rooms = []
    for f in STORAGE_DIR.glob("room_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                rooms.append(json.load(fp))
        except Exception:
            continue
    rooms.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rooms

