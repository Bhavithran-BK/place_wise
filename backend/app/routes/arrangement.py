from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel

from app.routes.rooms import load_room_meta, save_room_meta
from app.services.layout_engine import SpatialLayoutEngine
from app.services.inpainting import PlanAndImageRenderer
from app.schemas.room import SceneOperationsRequest
from app.core.config import STORAGE_DIR

router = APIRouter(prefix="/api/rooms", tags=["arrangement"])
renderer = PlanAndImageRenderer(STORAGE_DIR)

class ArrangeRequest(BaseModel):
    strategy: Optional[str] = "balanced"

class SaveLayoutRequest(BaseModel):
    name: Optional[str] = "Layout 1"

@router.post("/{room_id}/arrange")
async def generate_room_arrangement(
    room_id: str,
    strategy: Optional[str] = Query("balanced", description="Placement strategy: balanced, spacious, cozy"),
    body: Optional[ArrangeRequest] = None
):
    """
    Step 5: Generate Proposed Spatial Layout.
    Uses deterministic geometric layout engine with Shapely collision detection.
    Supports strategies: balanced (default), spacious (maximize walkway), cozy (cluster grouping).
    Produces canonical arrangement_plan and scene_manifest.
    """
    meta = load_room_meta(room_id)
    objects = meta.get("detected_objects", [])

    if not objects:
        raise HTTPException(status_code=400, detail="No detected objects in room.")

    effective_strategy = (body.strategy if body and body.strategy else strategy) or "balanced"

    engine = SpatialLayoutEngine(meta["width"], meta["height"])
    plan = engine.generate_plan(objects, strategy=effective_strategy)

    # Build canonical scene manifest per plan
    clean_bg_url = f"/storage/results/cleaned_{room_id}.jpg"
    manifest = engine.build_scene_manifest(
        room_id=room_id,
        original_image_url=meta.get("image_url", ""),
        clean_background_url=clean_bg_url,
        plan_objects=plan.get("objects", [])
    )

    meta["arrangement_plan"] = plan
    meta["scene_manifest"] = manifest
    meta["status"] = "arranged"
    save_room_meta(room_id, meta)

    return plan

@router.post("/{room_id}/operations")
async def apply_room_operations(room_id: str, req: SceneOperationsRequest):
    """
    Applies structured scene operations locally without AI image calls:
    Vocabulary: KEEP, REMOVE, MOVE, MOVE_NEAR, MOVE_LEFT, MOVE_RIGHT, ROTATE, RESIZE, FIX, ARRANGE
    Updates scene manifest and canonical arrangement plan directly.
    """
    meta = load_room_meta(room_id)
    plan = meta.get("arrangement_plan")
    if not plan or not plan.get("objects"):
        objects = meta.get("detected_objects", [])
        engine = SpatialLayoutEngine(meta["width"], meta["height"])
        plan = engine.generate_plan(objects, strategy="balanced")

    engine = SpatialLayoutEngine(meta["width"], meta["height"])
    updated_objects = engine.apply_operations(
        current_objects=plan.get("objects", []),
        operations=[op.dict() for op in req.operations]
    )

    plan["objects"] = updated_objects
    clean_bg_url = meta.get("cleaned_image_url") or f"/storage/results/cleaned_{room_id}.jpg"
    manifest = engine.build_scene_manifest(
        room_id=room_id,
        original_image_url=meta.get("image_url", ""),
        clean_background_url=clean_bg_url,
        plan_objects=updated_objects
    )

    meta["arrangement_plan"] = plan
    meta["scene_manifest"] = manifest
    save_room_meta(room_id, meta)

    return {
        "status": "success",
        "room_id": room_id,
        "operations_applied": len(req.operations),
        "arrangement_plan": plan,
        "scene_manifest": manifest
    }

@router.post("/{room_id}/render")
async def render_room_outputs(room_id: str):
    """
    Step 6: Render Both Coordinated Outputs:
    1. Annotated arrangement plan image (Level 1)
    2. Visual rearranged & inpainted room photograph (Level 2)
    3. Cleaned background photograph
    """
    meta = load_room_meta(room_id)
    plan = meta.get("arrangement_plan")
    img_path = meta.get("image_path")

    if not plan or not img_path:
        raise HTTPException(status_code=400, detail="Generate spatial plan before rendering visual outputs.")

    rendered = renderer.render_both_outputs(img_path, plan, room_id)

    meta["plan_image_url"] = rendered["plan_image_url"]
    meta["rearranged_image_url"] = rendered["rearranged_image_url"]
    meta["cleaned_image_url"] = rendered.get("cleaned_image_url")
    meta["status"] = "completed"

    # Synchronize scene manifest
    engine = SpatialLayoutEngine(meta["width"], meta["height"])
    manifest = engine.build_scene_manifest(
        room_id=room_id,
        original_image_url=meta.get("image_url", ""),
        clean_background_url=rendered.get("cleaned_image_url", ""),
        plan_objects=plan.get("objects", [])
    )
    meta["scene_manifest"] = manifest
    save_room_meta(room_id, meta)

    return {
        "status": "completed",
        "plan_image_url": rendered["plan_image_url"],
        "rearranged_image_url": rendered["rearranged_image_url"],
        "cleaned_image_url": rendered.get("cleaned_image_url"),
        "plan": plan,
        "scene_manifest": manifest
    }

@router.post("/{room_id}/layouts")
async def save_layout_snapshot(room_id: str, req: SaveLayoutRequest):
    """Saves a named layout snapshot for undo/redo and experimentation."""
    meta = load_room_meta(room_id)
    plan = meta.get("arrangement_plan")
    if not plan:
        raise HTTPException(status_code=400, detail="No active arrangement plan to save.")

    layouts = meta.get("layouts", [])
    snapshot = {
        "id": f"layout_{uuid.uuid4().hex[:6]}",
        "name": req.name or f"Layout {len(layouts) + 1}",
        "created_at": datetime.now().isoformat(),
        "objects": plan.get("objects", []),
        "strategy": plan.get("strategy", "balanced")
    }
    layouts.append(snapshot)
    meta["layouts"] = layouts
    save_room_meta(room_id, meta)

    return {"status": "success", "saved_layout": snapshot, "total_layouts": len(layouts)}

@router.get("/{room_id}/layouts")
async def list_layout_snapshots(room_id: str):
    """Lists saved layout snapshots."""
    meta = load_room_meta(room_id)
    return {"room_id": room_id, "layouts": meta.get("layouts", [])}

@router.post("/{room_id}/layouts/{layout_id}/restore")
async def restore_layout_snapshot(room_id: str, layout_id: str):
    """Restores a previously saved layout snapshot."""
    meta = load_room_meta(room_id)
    layouts = meta.get("layouts", [])
    matched = next((l for l in layouts if l["id"] == layout_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail=f"Layout '{layout_id}' not found.")

    if meta.get("arrangement_plan"):
        meta["arrangement_plan"]["objects"] = matched["objects"]
        meta["arrangement_plan"]["strategy"] = matched.get("strategy", "balanced")

    engine = SpatialLayoutEngine(meta["width"], meta["height"])
    manifest = engine.build_scene_manifest(
        room_id=room_id,
        original_image_url=meta.get("image_url", ""),
        clean_background_url=meta.get("cleaned_image_url", ""),
        plan_objects=matched["objects"]
    )
    meta["scene_manifest"] = manifest
    save_room_meta(room_id, meta)

    return {"status": "restored", "layout": matched}

@router.get("/{room_id}/results")
async def get_room_results(room_id: str):
    """Fetch complete before/after package, spatial scores, scene manifest, and arrangement plan."""
    meta = load_room_meta(room_id)
    return {
        "room_id": meta["room_id"],
        "original_image_url": meta["image_url"],
        "plan_image_url": meta.get("plan_image_url"),
        "rearranged_image_url": meta.get("rearranged_image_url"),
        "cleaned_image_url": meta.get("cleaned_image_url"),
        "voice_transcript": meta.get("voice_transcript"),
        "arrangement_plan": meta.get("arrangement_plan"),
        "scene_manifest": meta.get("scene_manifest"),
        "status": meta.get("status")
    }
