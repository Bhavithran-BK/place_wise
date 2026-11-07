from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional

from app.routes.rooms import load_room_meta, save_room_meta
from app.services.layout_engine import SpatialLayoutEngine
from app.services.inpainting import PlanAndImageRenderer
from app.core.config import STORAGE_DIR

router = APIRouter(prefix="/api/rooms", tags=["arrangement"])
renderer = PlanAndImageRenderer(STORAGE_DIR)

@router.post("/{room_id}/arrange")
async def generate_room_arrangement(room_id: str):
    """
    Step 5: Generate Proposed Spatial Layout.
    Uses deterministic geometric layout engine with Shapely collision detection.
    """
    meta = load_room_meta(room_id)
    objects = meta.get("detected_objects", [])

    if not objects:
        raise HTTPException(status_code=400, detail="No detected objects in room.")

    engine = SpatialLayoutEngine(meta["width"], meta["height"])
    plan = engine.generate_plan(objects)

    meta["arrangement_plan"] = plan
    meta["status"] = "arranged"
    save_room_meta(room_id, meta)

    return plan

@router.post("/{room_id}/render")
async def render_room_outputs(room_id: str):
    """
    Step 6: Render Both Coordinated Outputs:
    1. Annotated arrangement plan image
    2. Visual rearranged & inpainted room photograph
    """
    meta = load_room_meta(room_id)
    plan = meta.get("arrangement_plan")
    img_path = meta.get("image_path")

    if not plan or not img_path:
        raise HTTPException(status_code=400, detail="Generate spatial plan before rendering visual outputs.")

    rendered = renderer.render_both_outputs(img_path, plan, room_id)

    meta["plan_image_url"] = rendered["plan_image_url"]
    meta["rearranged_image_url"] = rendered["rearranged_image_url"]
    meta["status"] = "completed"
    save_room_meta(room_id, meta)

    return {
        "status": "completed",
        "plan_image_url": rendered["plan_image_url"],
        "rearranged_image_url": rendered["rearranged_image_url"],
        "plan": plan
    }

@router.get("/{room_id}/results")
async def get_room_results(room_id: str):
    """Fetch complete before/after package and arrangement plan."""
    meta = load_room_meta(room_id)
    return {
        "room_id": meta["room_id"],
        "original_image_url": meta["image_url"],
        "plan_image_url": meta.get("plan_image_url"),
        "rearranged_image_url": meta.get("rearranged_image_url"),
        "voice_transcript": meta.get("voice_transcript"),
        "arrangement_plan": meta.get("arrangement_plan"),
        "status": meta.get("status")
    }

