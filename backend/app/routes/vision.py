from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.room import DetectionResponse, DetectedObject, ObjectUpdateRequest
from app.routes.rooms import load_room_meta, save_room_meta
from app.services.object_detector import RoomObjectDetector
from app.services.segmentation import ObjectSegmenter
from app.core.config import MASKS_DIR

router = APIRouter(prefix="/api/rooms", tags=["vision"])

detector = RoomObjectDetector()
segmenter = ObjectSegmenter(MASKS_DIR)

class AddObjectRequest(BaseModel):
    class_name: str
    bbox: List[int] # [x1, y1, x2, y2]
    fixed: bool = False

@router.post("/{room_id}/detect", response_model=DetectionResponse)
async def detect_room_objects(room_id: str):
    """
    Step 2: Detect & Segment Objects.
    Uses YOLOv8 + Segmentation to identify objects and output binary masks.
    """
    meta = load_room_meta(room_id)
    image_path = meta.get("image_path")

    if not image_path:
        raise HTTPException(status_code=400, detail="Room has no image associated")

    objects = detector.detect_objects(image_path, room_id)
    meta["detected_objects"] = objects
    meta["status"] = "detected"
    save_room_meta(room_id, meta)

    return DetectionResponse(
        room_id=room_id,
        status="detected",
        objects_count=len(objects),
        objects=[DetectedObject(**o) for o in objects]
    )

@router.patch("/{room_id}/objects")
async def update_room_objects(room_id: str, updates: List[ObjectUpdateRequest]):
    """
    Allows user corrections of detected objects (rename class, mark KEEP/REMOVE/FIXED).
    """
    meta = load_room_meta(room_id)
    current_objs = {obj["object_id"]: obj for obj in meta.get("detected_objects", [])}

    for upd in updates:
        if upd.object_id in current_objs:
            target = current_objs[upd.object_id]
            if upd.class_name:
                target["class"] = upd.class_name
            if upd.action is not None:
                target["action"] = upd.action
            if upd.fixed is not None:
                target["fixed"] = upd.fixed

    meta["detected_objects"] = list(current_objs.values())
    save_room_meta(room_id, meta)
    return {"status": "success", "objects": meta["detected_objects"]}

@router.post("/{room_id}/objects")
async def add_manual_object(room_id: str, req: AddObjectRequest):
    """
    Allows user to manually draw and add a missing object on canvas.
    """
    meta = load_room_meta(room_id)
    image_path = meta.get("image_path")
    existing_objs = meta.get("detected_objects", [])

    idx = len([o for o in existing_objs if o["class"] == req.class_name]) + 1
    obj_id = f"{req.class_name}_{idx:02d}"

    mask_file = segmenter.generate_mask(image_path, req.bbox, f"{room_id}_{obj_id}")

    new_obj = {
        "object_id": obj_id,
        "class": req.class_name,
        "confidence": 1.0,  # User confirmed
        "bbox": req.bbox,
        "mask_path": mask_file,
        "mask_url": f"/storage/masks/{mask_file}",
        "action": None,
        "fixed": req.fixed
    }

    existing_objs.append(new_obj)
    meta["detected_objects"] = existing_objs
    save_room_meta(room_id, meta)

    return {"status": "success", "object": new_obj}

