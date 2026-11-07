import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import STORAGE_DIR, CORS_ORIGINS
from app.routes.rooms import router as rooms_router
from app.routes.vision import router as vision_router
from app.routes.voice import router as voice_router
from app.routes.arrangement import router as arrangement_router

app = FastAPI(
    title="PLACEWISE API",
    description="Backend API for PLACEWISE — Voice-Controlled Spatial Rearrangement Assistant",
    version="1.0.0"
)

# CORS middleware for React / Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads, masks, and rendered results
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Include routers
app.include_router(rooms_router)
app.include_router(vision_router)
app.include_router(voice_router)
app.include_router(arrangement_router)

@app.get("/")
async def root():
    return {
        "project": "PLACEWISE",
        "description": "Voice-controlled, image-first space rearrangement assistant",
        "status": "online",
        "endpoints": {
            "upload_room": "POST /api/rooms",
            "detect_objects": "POST /api/rooms/{id}/detect",
            "correct_objects": "PATCH /api/rooms/{id}/objects"
        }
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "placewise-backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

