import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.routes.rooms import load_room_meta, save_room_meta
from app.services.gnani_stt import GnaniSTT
from app.services.instruction_parser import InstructionParser
from app.services.gnani_tts import GnaniTTS

router = APIRouter(prefix="/api/rooms", tags=["voice"])

stt_service = GnaniSTT()
parser_service = InstructionParser()
tts_service = GnaniTTS()

class TextInstructionRequest(BaseModel):
    text: str
    language: str = "en-IN"

class ParseInstructionRequest(BaseModel):
    transcript: str

class SpeakRequest(BaseModel):
    text: Optional[str] = None
    language: str = "ta-IN"

@router.post("/{room_id}/transcribe")
async def transcribe_room_audio(room_id: str, file: UploadFile = File(...)):
    """
    Accepts recorded voice audio (WAV/WebM), saves it temporarily,
    and calls Gnani Prisma v2.5 STT to generate a transcript.
    """
    meta = load_room_meta(room_id)
    
    # Save uploaded audio to temp file
    suffix = Path(file.filename or "recording.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = stt_service.transcribe_audio(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Save transcript into room metadata
    if result.get("transcript"):
        meta["voice_transcript"] = result["transcript"]
        save_room_meta(room_id, meta)

    return result

@router.post("/{room_id}/transcribe-text")
async def transcribe_text_fallback(room_id: str, req: TextInstructionRequest):
    """
    Manual text instruction endpoint for testing or noisy environments.
    """
    meta = load_room_meta(room_id)
    result = stt_service.transcribe_text(req.text, req.language)
    meta["voice_transcript"] = req.text
    save_room_meta(room_id, meta)
    return result

@router.post("/{room_id}/instructions")
async def parse_room_instructions(room_id: str, req: ParseInstructionRequest):
    """
    Takes the transcript, parses KEEP/REMOVE/MOVE actions using
    InstructionParser against the room's detected objects, updates the
    room metadata with the new actions, and returns the structured plan.
    """
    meta = load_room_meta(room_id)
    detected_objects = meta.get("detected_objects", [])

    if not detected_objects:
        raise HTTPException(status_code=400, detail="Run object detection before giving voice instructions.")

    # Run parser
    parsed = parser_service.parse(req.transcript, detected_objects)

    # Update actions on room objects
    action_map = {a["object_id"]: a["action"] for a in parsed.get("actions", [])}
    for obj in detected_objects:
        if obj["object_id"] in action_map:
            obj["action"] = action_map[obj["object_id"]]

    meta["detected_objects"] = detected_objects
    meta["status"] = "instructed"
    meta["instruction_plan"] = parsed
    save_room_meta(room_id, meta)

    return parsed

@router.post("/{room_id}/speak")
async def generate_room_spoken_feedback(room_id: str, req: SpeakRequest):
    """
    Gnani Timbre v2.5 Spoken Confirmation.
    Generates natural spoken regional audio confirming the arrangement action.
    """
    meta = load_room_meta(room_id)
    plan = meta.get("instruction_plan") or {}
    
    # Auto-generate natural Tanglish response if text is not explicitly supplied
    if not req.text:
        removed = [a["object_id"] for a in plan.get("actions", []) if a["action"] == "REMOVE"]
        kept = [a["object_id"] for a in plan.get("actions", []) if a["action"] == "KEEP"]
        if removed and kept:
            spoken_text = f"{len(removed)} objects remove panna poren. Matha furniture neat ah arrange panniten."
        elif removed:
            spoken_text = f"{len(removed)} objects remove panniyachu."
        else:
            spoken_text = "All furniture neat ah arrange panniyachu."
    else:
        spoken_text = req.text

    tts_res = tts_service.generate_speech(spoken_text, req.language)
    return {
        "text": spoken_text,
        "audio_url": tts_res.get("audio_url"),
        "source": tts_res.get("source")
    }
