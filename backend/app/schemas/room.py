from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class DetectedObject(BaseModel):
    object_id: str
    class_name: str = Field(..., alias="class")
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    mask_path: Optional[str] = None
    mask_url: Optional[str] = None
    action: Optional[str] = None  # "KEEP", "REMOVE", "MOVE", "FIXED"
    fixed: bool = False

    class Config:
        populate_by_name = True

class ActionItem(BaseModel):
    object_id: str
    object_class: str
    action: str  # "KEEP" | "REMOVE" | "MOVE"
    reason: Optional[str] = "Determined from instruction"

class ActionPlan(BaseModel):
    mode: str = "REARRANGE_ALL"  # "REMOVE_ONLY" | "KEEP_ONLY" | "KEEP_AND_REMOVE" | "REARRANGE_ALL"
    actions: List[ActionItem] = []
    rearrange_remaining: bool = False
    clarification_required: bool = False
    clarification_message: Optional[str] = None
    clarification_candidates: List[str] = []
    parsed_keep: List[str] = []
    parsed_remove: List[str] = []
    raw_transcript: Optional[str] = ""

class RoomMetadata(BaseModel):
    room_id: str
    filename: str
    image_url: str
    width: int
    height: int
    created_at: str
    status: str = "uploaded"  # uploaded, detected, instructed, arranged, completed
    detected_objects: List[DetectedObject] = []
    voice_transcript: Optional[str] = None
    instruction_plan: Optional[ActionPlan] = None
    arrangement_plan: Optional[Dict[str, Any]] = None

class RoomUploadResponse(BaseModel):
    room_id: str
    filename: str
    image_url: str
    width: int
    height: int
    created_at: str
    status: str

class DetectionResponse(BaseModel):
    room_id: str
    status: str
    objects_count: int
    objects: List[DetectedObject]

class ObjectUpdateRequest(BaseModel):
    object_id: str
    class_name: Optional[str] = None
    action: Optional[str] = None
    fixed: Optional[bool] = None

class InstructionRequest(BaseModel):
    transcript: str

class InstructionResponse(BaseModel):
    success: bool
    room_id: str
    action_plan: ActionPlan

class TranscribeResponse(BaseModel):
    success: bool
    transcript: str
    language: str
    provider: str
    confidence: Optional[float] = None
    words: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


