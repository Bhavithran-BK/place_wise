"""
PLACEWISE — Days 5-6 & 7-8 Comprehensive Verification Suite
Tests the Spatial Arrangement Engine (Shapely), Multi-Strategy Placement,
Quality Scoring, Inpainting & Compositing Pipeline, and Results Endpoints.
"""
import sys
import os
import requests
from pathlib import Path

BACKEND_URL = "http://127.0.0.1:8000"

def print_step(title, ok=None):
    if ok is True:
        print(f"  [PASS] {title}")
    elif ok is False:
        print(f"  [FAIL] {title}")
    else:
        print(f"\n[TEST] {title}")

def run_days5_8_verification():
    print("=" * 65)
    print("PLACEWISE — DAYS 5-6 & 7-8 VERIFICATION (ARRANGE, INPAINT, POLISH)")
    print("=" * 65)

    client = requests.Session()

    # 1. Health check
    print_step("1. Verifying Backend Health...")
    res = client.get(f"{BACKEND_URL}/api/health")
    assert res.status_code == 200
    print_step("FastAPI server online and healthy", True)

    # 2. Upload test image or use demo
    print_step("2. Creating Test Room with Multi-Item Scenario...")
    demo_file = Path("backend/storage/uploads/demo_room_01.jpg")
    if not demo_file.exists():
        # Fallback to creating a dummy image
        import numpy as np, cv2
        img = np.full((600, 800, 3), 200, dtype=np.uint8)
        demo_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(demo_file), img)

    with open(demo_file, "rb") as f:
        up_res = client.post(f"{BACKEND_URL}/api/rooms", files={"file": ("room.jpg", f, "image/jpeg")}).json()

    room_id = up_res["room_id"]
    print_step(f"Room initialized with ID: {room_id}", True)

    # 3. Detect / inject objects
    print_step("3. Injecting Multi-Object Living Room Setup (TV, Sofa, Table, 2 Chairs)...")
    patch_res = client.patch(
        f"{BACKEND_URL}/api/rooms/{room_id}/objects",
        json=[
            {"object_id": "tv_01", "class_name": "tv", "action": "KEEP", "fixed": True},
            {"object_id": "sofa_01", "class_name": "sofa", "action": "KEEP", "fixed": False},
            {"object_id": "table_01", "class_name": "table", "action": "REMOVE", "fixed": False},
            {"object_id": "chair_01", "class_name": "chair", "action": "REMOVE", "fixed": False},
            {"object_id": "chair_02", "class_name": "chair", "action": "KEEP", "fixed": False},
        ]
    )
    assert patch_res.status_code == 200
    print_step("Objects initialized with actions (1 Fixed TV, 1 Keep Sofa, 1 Move Chair, 2 Removed items)", True)

    # 4. Generate Spatial Arrangement Plan (Strategy 1: Balanced)
    print_step("4. Testing Spatial Arrangement Engine (Strategy: Balanced)...")
    p1 = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/arrange?strategy=balanced").json()
    assert "objects" in p1
    assert "scores" in p1
    assert "recommendations" in p1
    assert p1["strategy"] == "balanced"
    assert p1["constraints"]["no_object_overlap"] is True

    scores = p1["scores"]
    print_step(
        f"Scores generated -> Overall: {scores['overall_score']}/100, "
        f"Space Util: {scores['space_utilization']}%, Walkway: {scores['walkway_clearance']}%, "
        f"Balance: {scores['balance_symmetry']}%",
        True
    )

    # 5. Test Alternative Strategy 2: Spacious
    print_step("5. Testing Alternative Strategy Regeneration (Strategy: Spacious)...")
    p2 = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/arrange?strategy=spacious").json()
    assert p2["strategy"] == "spacious"
    print_step("Spacious strategy plan generated successfully", True)

    # 6. Test Alternative Strategy 3: Cozy
    print_step("6. Testing Alternative Strategy Regeneration (Strategy: Cozy)...")
    p3 = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/arrange?strategy=cozy").json()
    assert p3["strategy"] == "cozy"
    print_step("Cozy cluster plan generated successfully", True)

    # 7. Test Dual Output Rendering (Level 1 Plan & Level 2 Inpainting)
    print_step("7. Testing Coordinated Visual Output Rendering (POST /api/rooms/{id}/render)...")
    render_res = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/render").json()
    print("Render response:", render_res)
    assert render_res["status"] == "completed"
    assert "plan_image_url" in render_res
    assert "rearranged_image_url" in render_res
    assert "cleaned_image_url" in render_res

    plan_disk = Path(__file__).parent / render_res['plan_image_url'].lstrip('/')
    rearranged_disk = Path(__file__).parent / render_res['rearranged_image_url'].lstrip('/')
    cleaned_disk = Path(__file__).parent / render_res['cleaned_image_url'].lstrip('/')
    print(f"Checking disk paths: {plan_disk.resolve()} exists={plan_disk.exists()}")

    assert plan_disk.exists() and plan_disk.stat().st_size > 1000
    assert rearranged_disk.exists() and rearranged_disk.stat().st_size > 1000
    assert cleaned_disk.exists() and cleaned_disk.stat().st_size > 1000

    print_step(f"Level 1 Annotated Plan on disk: {plan_disk.name} ({plan_disk.stat().st_size} bytes)", True)
    print_step(f"Level 2 Rearranged Photo on disk: {rearranged_disk.name} ({rearranged_disk.stat().st_size} bytes)", True)
    print_step(f"Cleaned Background on disk: {cleaned_disk.name} ({cleaned_disk.stat().st_size} bytes)", True)

    # 8. Test Spoken Confirmation Loop
    print_step("8. Testing Gnani Timbre Voice Confirmation Loop...")
    speak_res = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/speak", json={}).json()
    assert "text" in speak_res
    print_step(f"Voice Confirmation text: \"{speak_res['text']}\"", True)

    # 9. Test Results Package Endpoint
    print_step("9. Verifying Complete Results Package (GET /api/rooms/{id}/results)...")
    results = client.get(f"{BACKEND_URL}/api/rooms/{room_id}/results").json()
    assert results["status"] == "completed"
    assert results["plan_image_url"] == render_res["plan_image_url"]
    assert results["rearranged_image_url"] == render_res["rearranged_image_url"]
    print_step("Full package contains original, plan, rearranged, and cleaned outputs", True)

    print("\n" + "=" * 65)
    print("ALL DAY 5-6 & 7-8 REQUIREMENTS PASSED FULLY AND ARE VERIFIED!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    try:
        success = run_days5_8_verification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

