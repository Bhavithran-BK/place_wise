from typing import List, Optional, Dict, Any
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

class RoomMetadata(BaseModel):
    room_id: str
    filename: str
    image_url: str
    width: int
    height: int
    created_at: str
    status: str = "uploaded"  # uploaded, detected, arranged, completed
    detected_objects: List[DetectedObject] = []

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

