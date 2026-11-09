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

VALID_ACTIONS = {"KEEP", "REMOVE", "MOVE", "FIXED", None}

@router.patch("/{room_id}/objects")
async def update_room_objects(room_id: str, updates: List[ObjectUpdateRequest]):
    """
    Allows user corrections of detected objects (rename class, mark KEEP/REMOVE/FIXED).
    Validates object IDs and action values, and synchronizes the canonical action plan.
    """
    meta = load_room_meta(room_id)
    current_objs = {obj["object_id"]: obj for obj in meta.get("detected_objects", [])}

    # 1. Validation & upsert phase
    for upd in updates:
        if upd.action is not None and upd.action.upper() not in VALID_ACTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{upd.action}'. Allowed values: KEEP, REMOVE, MOVE, FIXED"
            )
        if upd.object_id not in current_objs and not upd.class_name:
            raise HTTPException(
                status_code=400,
                detail=f"Object ID '{upd.object_id}' does not exist in room {room_id}. Provide class_name to add as new object."
            )

    # 2. Update or insert room detected objects
    for upd in updates:
        if upd.object_id in current_objs:
            target = current_objs[upd.object_id]
            if upd.class_name:
                target["class"] = upd.class_name.strip().lower()
            if upd.action is not None:
                target["action"] = upd.action.upper()
            if upd.fixed is not None:
                target["fixed"] = upd.fixed
        else:
            # Upsert object if injected/added via PATCH
            cls_n = (upd.class_name or "furniture").strip().lower()
            current_objs[upd.object_id] = {
                "object_id": upd.object_id,
                "class": cls_n,
                "confidence": 1.0,
                "bbox": [50, 50, 150, 150],
                "action": upd.action.upper() if upd.action else None,
                "fixed": bool(upd.fixed)
            }

    meta["detected_objects"] = list(current_objs.values())

    # 3. Synchronize canonical action plan (instruction_plan)
    plan = meta.get("instruction_plan") or {
        "mode": "REARRANGE_ALL",
        "actions": [],
        "rearrange_remaining": False,
        "clarification_required": False,
        "clarification_message": None,
        "clarification_candidates": [],
        "parsed_keep": [],
        "parsed_remove": [],
        "raw_transcript": meta.get("voice_transcript", "")
    }

    # Update or insert into action plan
    existing_actions_map = {a["object_id"]: a for a in plan.get("actions", [])}
    for upd in updates:
        action_val = upd.action.upper() if upd.action else "KEEP"
        if upd.object_id in existing_actions_map:
            existing_actions_map[upd.object_id]["action"] = action_val
            existing_actions_map[upd.object_id]["reason"] = "Manually corrected by user"
            if upd.class_name:
                existing_actions_map[upd.object_id]["object_class"] = upd.class_name.strip().lower()
        else:
            existing_actions_map[upd.object_id] = {
                "object_id": upd.object_id,
                "object_class": current_objs[upd.object_id]["class"],
                "action": action_val,
                "reason": "Manually corrected by user"
            }

    # Ensure all detected objects are in plan actions
    for obj in meta["detected_objects"]:
        oid = obj["object_id"]
        if oid not in existing_actions_map:
            existing_actions_map[oid] = {
                "object_id": oid,
                "object_class": obj["class"],
                "action": obj.get("action") or "KEEP",
                "reason": "Retained by default"
            }

    plan["actions"] = list(existing_actions_map.values())
    
    # Recalculate mode
    has_rem = any(a["action"] == "REMOVE" for a in plan["actions"])
    has_keep = any(a["action"] == "KEEP" for a in plan["actions"])
    if has_rem and has_keep:
        plan["mode"] = "KEEP_AND_REMOVE"
    elif has_rem:
        plan["mode"] = "REMOVE_ONLY"
    elif has_keep:
        plan["mode"] = "KEEP_ONLY"
    else:
        plan["mode"] = "REARRANGE_ALL"

    meta["instruction_plan"] = plan
    save_room_meta(room_id, meta)

    return {
        "status": "success",
        "room_id": room_id,
        "objects": meta["detected_objects"],
        "action_plan": plan
    }

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

