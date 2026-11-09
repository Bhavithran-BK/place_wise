import sys
import os
from pathlib import Path
import json
import requests

BACKEND_URL = "http://127.0.0.1:8000"

# Setup resilient client: uses live server if running, or in-memory TestClient
try:
    r = requests.get(f"{BACKEND_URL}/api/health", timeout=0.5)
    if r.status_code == 200:
        client = requests
    else:
        raise Exception("Server not running on port 8000")
except Exception:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from starlette.testclient import TestClient
    from app.main import app
    _tc = TestClient(app)
    class TestClientAdapter:
        @staticmethod
        def post(url, **kwargs):
            endpoint = url.replace(BACKEND_URL, "")
            return _tc.post(endpoint, **kwargs)
        @staticmethod
        def get(url, **kwargs):
            endpoint = url.replace(BACKEND_URL, "")
            return _tc.get(endpoint, **kwargs)
        @staticmethod
        def patch(url, **kwargs):
            endpoint = url.replace(BACKEND_URL, "")
            return _tc.patch(endpoint, **kwargs)
    client = TestClientAdapter()

def print_step(name, status=None):
    if status is None:
        print(f"\n[TEST] {name}...")
    elif status:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}")

def run_day3_4_verification():
    print("=" * 60)
    print("PLACEWISE - DAY 3-4 WORKS RIGOROUS VERIFICATION (VOICE & INTENT)")
    print("=" * 60)

    # 1. Setup a benchmark room with diverse objects
    print_step("1. Preparing benchmark room with multiple objects")
    with open("backend/storage/uploads/demo_room_01.jpg", "rb") as f:
        res = client.post(f"{BACKEND_URL}/api/rooms", files={"file": ("demo.jpg", f, "image/jpeg")})
    assert res.status_code == 200
    room_id = res.json()["room_id"]
    
    # Run detection
    d_res = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/detect")
    assert d_res.status_code == 200
    objs = d_res.json()["objects"]
    print_step(f"Room {room_id} ready with {len(objs)} detected objects: {[o['class'] for o in objs]}", True)

    # 2. Test Pattern 1: REMOVE ONLY ("Indha chair-um table-um vendaam")
    print_step("2. Pattern 1: REMOVE ONLY ('Indha chair-um table-um vendaam')")
    p1 = client.post(
        f"{BACKEND_URL}/api/rooms/{room_id}/instructions",
        json={"transcript": "Indha chair-um table-um vendaam"}
    ).json()
    assert p1["mode"] == "REMOVE_ONLY"
    assert "table" in p1["parsed_remove"]
    print_step(f"Mode: {p1['mode']}, Parsed Remove: {p1['parsed_remove']}", True)

    # 3. Test Pattern 2: KEEP ONLY ("Sofa, TV, bookshelf ellame venum")
    print_step("3. Pattern 2: KEEP ONLY ('Sofa, TV, bookshelf ellame venum')")
    p2 = client.post(
        f"{BACKEND_URL}/api/rooms/{room_id}/instructions",
        json={"transcript": "Sofa, TV, bookshelf ellame venum"}
    ).json()
    assert p2["mode"] == "KEEP_ONLY"
    assert "sofa" in p2["parsed_keep"]
    print_step(f"Mode: {p2['mode']}, Parsed Keep: {p2['parsed_keep']}", True)

    # 4. Test Pattern 3: KEEP & REMOVE Combo ("Indha rendu chairs vendaam. Sofa venum.")
    print_step("4. Pattern 3: KEEP & REMOVE ('Indha rendu chairs vendaam. Sofa venum.')")
    p3 = client.post(
        f"{BACKEND_URL}/api/rooms/{room_id}/instructions",
        json={"transcript": "Indha rendu chairs vendaam. Sofa venum."}
    ).json()
    assert p3["mode"] == "KEEP_AND_REMOVE"
    assert "sofa" in p3["parsed_keep"]
    assert "chair" in p3["parsed_remove"]
    print_step(f"Mode: {p3['mode']}, Actions: {[a['object_id'] + '=' + a['action'] for a in p3['actions']]}", True)

    # 5. Test Pattern 4: ARRANGE ALL ("Neat ah arrange pannunga")
    print_step("5. Pattern 4: ARRANGE ALL ('Neat ah arrange pannunga')")
    p4 = client.post(
        f"{BACKEND_URL}/api/rooms/{room_id}/instructions",
        json={"transcript": "Neat ah arrange pannunga"}
    ).json()
    assert p4["mode"] == "REARRANGE_ALL"
    assert p4["rearrange_remaining"] is True
    print_step("Mode: REARRANGE_ALL with rearrange_remaining=True", True)

    # 6. Test Pattern 5: AMBIGUOUS REFERENCE (Singular 'Indha chair vendaam' when multiple exist)
    print_step("6. Pattern 5: AMBIGUITY CHECK (Single 'chair' when multiple exist in room)")
    # Inject 2 chairs into room objects to verify ambiguity resolution
    patch_chairs = client.patch(f"{BACKEND_URL}/api/rooms/{room_id}/objects", json=[
        {"object_id": "chair_01", "class_name": "chair", "action": None},
        {"object_id": "chair_02", "class_name": "chair", "action": None}
    ])
    p5 = client.post(
        f"{BACKEND_URL}/api/rooms/{room_id}/instructions",
        json={"transcript": "Indha chair vendaam"}
    ).json()
    assert p5["clarification_required"] is True, f"Expected ambiguity clarification, got: {p5}"
    assert len(p5["clarification_candidates"]) >= 2
    print_step(f"Clarification Triggered: '{p5['clarification_message']}'", True)

    # 7. Test Spoken Voice Confirmation (POST /api/rooms/{id}/speak)
    print_step("7. Spoken Confirmation Loop (POST /api/rooms/{id}/speak)")
    speak_res = client.post(f"{BACKEND_URL}/api/rooms/{room_id}/speak", json={}).json()
    assert "text" in speak_res
    print_step(f"Spoken feedback generated: \"{speak_res['text']}\"", True)

    print("\n" + "=" * 60)
    print("ALL DAY 3-4 VOICE & INTENT REQUIREMENTS PASSED FULLY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_day3_4_verification()
    sys.exit(0 if success else 1)

