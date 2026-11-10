import sys
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app.services.object_detector import RoomObjectDetector
from app.services.instruction_parser import InstructionParser
from app.services.layout_engine import SpatialLayoutEngine
from app.services.inpainting import PlanAndImageRenderer
from app.core.config import STORAGE_DIR

print("=" * 60)
print("TESTING FULL PLACEWISE END-TO-END PIPELINE")
print("=" * 60)

# Step 1: Detect objects
detector = RoomObjectDetector()
room_id = "test_run_01"
img_path = str(STORAGE_DIR / "uploads" / "demo_room_01.jpg")

print("\n1. Detecting room objects...")
objects = detector.detect_objects(img_path, room_id)
print(f"   Detected {len(objects)} objects:")
for o in objects:
    print(f"   - {o['object_id']}: {o['class']} @ {o['bbox']}")

# Step 2: Tanglish Voice Instruction
parser = InstructionParser()
voice_instruction = "Indha rendu chairs vendaam. Sofa venum."
print(f"\n2. Parsing Voice Instruction: \"{voice_instruction}\"")
plan_intent = parser.parse(voice_instruction, objects)
print(f"   Mode: {plan_intent['mode']}")
for a in plan_intent['actions']:
    print(f"   - {a['object_id']}: {a['action']}")

# Update objects with actions
for obj in objects:
    for a in plan_intent['actions']:
        if obj['object_id'] == a['object_id']:
            obj['action'] = a['action']

# Step 3: Spatial Arrangement
print("\n3. Generating Deterministic Spatial Layout...")
layout_engine = SpatialLayoutEngine(800, 600)
spatial_plan = layout_engine.generate_plan(objects)
print(f"   Spatial Plan Created: {spatial_plan['summary']}")

# Step 4: Render Both Outputs
print("\n4. Rendering Both Coordinated Outputs...")
renderer = PlanAndImageRenderer(STORAGE_DIR)
rendered = renderer.render_both_outputs(img_path, spatial_plan, room_id)

print(f"   [Output 1] Annotated Plan: {rendered['plan_image_url']}")
print(f"   [Output 2] Rearranged Photo: {rendered['rearranged_image_url']}")

plan_disk_path = STORAGE_DIR / Path(rendered['plan_image_url'].replace('/storage/', ''))
rearranged_disk_path = STORAGE_DIR / Path(rendered['rearranged_image_url'].replace('/storage/', ''))

assert plan_disk_path.exists(), f"Plan image not found at {plan_disk_path}"
assert rearranged_disk_path.exists(), f"Rearranged image not found at {rearranged_disk_path}"

print("\n" + "=" * 60)
print("SUCCESS: COMPLETE END-TO-END PIPELINE VERIFIED!")
print("=" * 60)
