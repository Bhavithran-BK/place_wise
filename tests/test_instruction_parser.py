"""
Automated Test Suite for PLACEWISE Instruction Parser & Object Matching

Covers all 15 required scenarios specified in PLACEWISE Days 3-4 Specification:
1. Remove one object class.
2. Remove all objects of a class.
3. Keep one object class.
4. Keep and remove multiple classes.
5. Rearrange everything.
6. Ambiguous object references.
7. Contradictory instructions.
8. Numerical object references.
9. Tanglish instructions.
10. Tamil/English mixed instructions.
11. Missing object classes.
12. Duplicate object IDs.
13. LLM returning malformed JSON.
14. LLM returning nonexistent object IDs.
15. Manual object-action correction.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend is in sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.services.instruction_parser import InstructionParser

parser = InstructionParser()


def assert_valid_action_plan(plan: dict, detected_objects: list):
    """
    Mandatory invariant verification:
    - Every detected object has exactly one action.
    - No nonexistent object ID appears.
    - Actions are either KEEP or REMOVE.
    """
    detected_ids = {o.get("object_id") for o in detected_objects if o.get("object_id")}
    action_ids = [a["object_id"] for a in plan.get("actions", [])]

    # Exactly one action per detected object
    assert len(action_ids) == len(set(action_ids)), f"Duplicate action IDs in plan: {action_ids}"
    assert set(action_ids) == detected_ids, f"Action IDs {set(action_ids)} do not match detected IDs {detected_ids}"

    # Valid action values
    for a in plan["actions"]:
        assert a["action"] in ["KEEP", "REMOVE", "MOVE"], f"Invalid action: {a}"
        assert a.get("object_class"), f"Missing object_class in action: {a}"


# ──────────────────────────────────────────────────────────────────────────────
# SCENARIOS 1–15
# ──────────────────────────────────────────────────────────────────────────────

def test_1_remove_one_object_class():
    """Scenario 1: Remove one object class."""
    objects = [
        {"object_id": "table_01", "class": "table"},
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "sofa_01", "class": "sofa"}
    ]
    res = parser.parse("Table remove pannunga.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["table_01"] == "REMOVE"
    assert actions["chair_01"] == "KEEP"
    assert actions["sofa_01"] == "KEEP"
    assert res["mode"] == "REMOVE_ONLY"


def test_2_remove_all_objects_of_a_class():
    """Scenario 2: Remove all objects of a class (Test Case B)."""
    objects = [
        {"object_id": f"book_{i:02d}", "class": "book"} for i in range(1, 8)
    ] + [
        {"object_id": "sofa_01", "class": "sofa"},
        {"object_id": "sofa_02", "class": "sofa"},
        {"object_id": "vase_01", "class": "vase"},
        {"object_id": "vase_02", "class": "vase"},
        {"object_id": "cup_01", "class": "cup"},
        {"object_id": "bowl_01", "class": "bowl"},
        {"object_id": "potted_plant_01", "class": "potted plant"},
        {"object_id": "potted_plant_02", "class": "potted plant"},
        {"object_id": "potted_plant_03", "class": "potted plant"},
    ]
    assert len(objects) == 16

    res = parser.parse("Remove all books and keep both sofas.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    # All 7 books must be removed
    for i in range(1, 8):
        assert actions[f"book_{i:02d}"] == "REMOVE", f"book_{i:02d} was not removed"

    # Both sofas kept
    assert actions["sofa_01"] == "KEEP"
    assert actions["sofa_02"] == "KEEP"

    # Unmentioned items default to KEEP
    assert actions["vase_01"] == "KEEP"
    assert actions["cup_01"] == "KEEP"
    assert actions["bowl_01"] == "KEEP"
    assert actions["potted_plant_01"] == "KEEP"

    rem_count = sum(1 for a in res["actions"] if a["action"] == "REMOVE")
    keep_count = sum(1 for a in res["actions"] if a["action"] == "KEEP")
    assert rem_count == 7
    assert keep_count == 9
    assert res["clarification_required"] is False
    assert res["mode"] == "KEEP_AND_REMOVE"


def test_3_keep_one_object_class():
    """Scenario 3: Keep one object class (Pattern 2)."""
    objects = [
        {"object_id": "sofa_01", "class": "sofa"},
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "tv_01", "class": "tv"}
    ]
    res = parser.parse("Sofa mattum venum.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["sofa_01"] == "KEEP"
    # Unmentioned default to KEEP unless removal was explicitly requested
    assert actions["chair_01"] == "KEEP"
    assert actions["tv_01"] == "KEEP"
    assert res["mode"] == "KEEP_ONLY"


def test_4_keep_and_remove_multiple_classes():
    """Scenario 4: Keep and remove multiple classes (Pattern 3)."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_02", "class": "chair"},
        {"object_id": "table_01", "class": "table"},
        {"object_id": "sofa_01", "class": "sofa"},
        {"object_id": "tv_01", "class": "tv"}
    ]
    res = parser.parse("Chair remove pannunga, table vendaam, sofa venum.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["chair_01"] == "REMOVE"
    assert actions["chair_02"] == "REMOVE"
    assert actions["table_01"] == "REMOVE"
    assert actions["sofa_01"] == "KEEP"
    assert actions["tv_01"] == "KEEP"
    assert res["mode"] == "KEEP_AND_REMOVE"


def test_5_rearrange_everything():
    """Scenario 5: Rearrange everything (Pattern 4)."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "sofa_01", "class": "sofa"},
        {"object_id": "tv_01", "class": "tv"}
    ]
    res = parser.parse("Ellathayum neat ah arrange pannunga.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    for a in res["actions"]:
        assert a["action"] == "KEEP"
    assert res["rearrange_remaining"] is True
    assert res["mode"] == "REARRANGE_ALL"


def test_6_ambiguous_object_references():
    """Scenario 6: Ambiguous object references (Pattern 5)."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_02", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]
    # "Andha chair remove pannunga" with multiple chairs present
    res = parser.parse("Andha chair remove pannunga.", objects)
    assert_valid_action_plan(res, objects)
    assert res["clarification_required"] is True
    assert res["clarification_message"] is not None
    assert "chair_01" in res["clarification_candidates"]
    assert "chair_02" in res["clarification_candidates"]


def test_7_contradictory_instructions():
    """Scenario 7: Contradictory instructions (Pattern 6)."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]
    res = parser.parse("Chair remove pannunga, chair venum.", objects)
    assert_valid_action_plan(res, objects)
    assert res["clarification_required"] is True
    assert "contradiction" in res["clarification_message"].lower()


def test_8_numerical_object_references():
    """Scenario 8: Numerical object references."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_02", "class": "chair"},
        {"object_id": "chair_03", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]

    # "Remove both chairs" when 2 chairs exist
    res_both = parser.parse("Remove both chairs.", objects[:2] + [objects[3]])
    act_both = {a["object_id"]: a["action"] for a in res_both["actions"]}
    assert act_both["chair_01"] == "REMOVE"
    assert act_both["chair_02"] == "REMOVE"
    assert res_both["clarification_required"] is False

    # "Remove one chair" when 3 exist -> ambiguous
    res_one = parser.parse("Remove one chair.", objects)
    assert res_one["clarification_required"] is True

    # "Remove first chair"
    res_ord = parser.parse("Remove first chair.", objects)
    act_ord = {a["object_id"]: a["action"] for a in res_ord["actions"]}
    assert act_ord["chair_01"] == "REMOVE"
    assert act_ord["chair_02"] == "KEEP"
    assert act_ord["chair_03"] == "KEEP"


def test_9_tanglish_instructions():
    """Scenario 9: Authentic Tanglish phrasing."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_02", "class": "chair"},
        {"object_id": "sofa_01", "class": "sofa"}
    ]
    res = parser.parse("Indha rendu chairs vendaam. Sofa venum.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["chair_01"] == "REMOVE"
    assert actions["chair_02"] == "REMOVE"
    assert actions["sofa_01"] == "KEEP"


def test_10_tamil_english_mixed_instructions():
    """Scenario 10: Tamil/English mixed instructions (Test Case A)."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_02", "class": "chair"},
        {"object_id": "table_01", "class": "table"},
        {"object_id": "sofa_01", "class": "sofa"},
        {"object_id": "tv_01", "class": "tv"}
    ]
    res = parser.parse("Table and chair remove pannunga. Remaining arrange pannunga.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["chair_01"] == "REMOVE"
    assert actions["chair_02"] == "REMOVE"
    assert actions["table_01"] == "REMOVE"
    assert actions["sofa_01"] == "KEEP"
    assert actions["tv_01"] == "KEEP"
    assert res["rearrange_remaining"] is True


def test_11_missing_object_classes():
    """Scenario 11: Mentioning classes not detected in the room."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]
    # User mentions removing refrigerator and bed, which don't exist
    res = parser.parse("Remove refrigerator and bed. Table venum.", objects)
    assert_valid_action_plan(res, objects)

    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    # Existing objects must not be hallucinated or falsely removed
    assert actions["chair_01"] == "KEEP"
    assert actions["table_01"] == "KEEP"
    assert "refrigerator" not in actions
    assert "bed" not in actions


def test_12_duplicate_object_ids():
    """Scenario 12: Normalizing duplicate object IDs in input."""
    duplicate_objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "chair_01", "class": "chair"},  # duplicate
        {"object_id": "table_01", "class": "table"}
    ]
    res = parser.parse("Table remove pannunga.", duplicate_objects)
    # Output must have distinct IDs
    action_ids = [a["object_id"] for a in res["actions"]]
    assert len(action_ids) == len(set(action_ids))
    assert len(action_ids) == 3  # Normalized into distinct IDs


def test_13_llm_returning_malformed_json():
    """Scenario 13: LLM returning malformed JSON."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]

    # Mock LLM returning malformed JSON string
    with patch.object(parser, "_call_gemini_llm", return_value=None):
        res = parser.parse("Chair remove pannunga.", objects)

    assert_valid_action_plan(res, objects)
    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["chair_01"] == "REMOVE"
    assert actions["table_01"] == "KEEP"


def test_14_llm_returning_nonexistent_object_ids():
    """Scenario 14: LLM returning nonexistent or hallucinated IDs."""
    objects = [
        {"object_id": "chair_01", "class": "chair"},
        {"object_id": "table_01", "class": "table"}
    ]

    # Mock LLM returning hallucinated ID 'alien_sofa_99' and missing 'table_01'
    mock_llm_plan = {
        "mode": "REMOVE_ONLY",
        "actions": [
            {"object_id": "chair_01", "object_class": "chair", "action": "REMOVE"},
            {"object_id": "alien_sofa_99", "object_class": "sofa", "action": "REMOVE"}
        ],
        "rearrange_remaining": False,
        "clarification_required": False
    }

    with patch.object(parser, "_call_gemini_llm", return_value=mock_llm_plan):
        res = parser.parse("Chair remove pannunga.", objects)

    assert_valid_action_plan(res, objects)
    action_ids = [a["object_id"] for a in res["actions"]]
    assert "alien_sofa_99" not in action_ids
    assert "table_01" in action_ids
    actions = {a["object_id"]: a["action"] for a in res["actions"]}
    assert actions["chair_01"] == "REMOVE"
    assert actions["table_01"] == "KEEP"  # Defaulted to KEEP


def test_15_manual_object_action_correction():
    """Scenario 15: Validating manual object-action update synchronization."""
    from app.routes.vision import update_room_objects
    from app.schemas.room import ObjectUpdateRequest
    import json
    from app.core.config import STORAGE_DIR

    # Setup dummy room file
    test_room_id = "test_room_scen15"
    room_file = STORAGE_DIR / f"room_{test_room_id}.json"
    dummy_data = {
        "room_id": test_room_id,
        "detected_objects": [
            {"object_id": "chair_01", "class": "chair", "action": "KEEP", "fixed": False},
            {"object_id": "table_01", "class": "table", "action": "KEEP", "fixed": False}
        ],
        "instruction_plan": {
            "mode": "KEEP_ONLY",
            "actions": [
                {"object_id": "chair_01", "object_class": "chair", "action": "KEEP"},
                {"object_id": "table_01", "object_class": "table", "action": "KEEP"}
            ]
        }
    }
    with open(room_file, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f)

    try:
        import asyncio
        update_req = [
            ObjectUpdateRequest(object_id="chair_01", action="REMOVE")
        ]
        result = asyncio.run(update_room_objects(test_room_id, update_req))

        assert result["status"] == "success"
        obj_map = {o["object_id"]: o["action"] for o in result["objects"]}
        assert obj_map["chair_01"] == "REMOVE"
        assert obj_map["table_01"] == "KEEP"

        # Action plan updated
        plan_actions = {a["object_id"]: a["action"] for a in result["action_plan"]["actions"]}
        assert plan_actions["chair_01"] == "REMOVE"
        assert plan_actions["table_01"] == "KEEP"
        assert result["action_plan"]["mode"] == "KEEP_AND_REMOVE"
    finally:
        if room_file.exists():
            room_file.unlink()


if __name__ == "__main__":
    print("Running all 15 test scenarios...")
    test_1_remove_one_object_class()
    print("✓ Test 1: Remove one object class passed.")
    test_2_remove_all_objects_of_a_class()
    print("✓ Test 2: Remove all objects of a class (Test Case B) passed.")
    test_3_keep_one_object_class()
    print("✓ Test 3: Keep one object class passed.")
    test_4_keep_and_remove_multiple_classes()
    print("✓ Test 4: Keep and remove multiple classes passed.")
    test_5_rearrange_everything()
    print("✓ Test 5: Rearrange everything passed.")
    test_6_ambiguous_object_references()
    print("✓ Test 6: Ambiguous object references passed.")
    test_7_contradictory_instructions()
    print("✓ Test 7: Contradictory instructions passed.")
    test_8_numerical_object_references()
    print("✓ Test 8: Numerical object references passed.")
    test_9_tanglish_instructions()
    print("✓ Test 9: Tanglish instructions passed.")
    test_10_tamil_english_mixed_instructions()
    print("✓ Test 10: Tamil/English mixed instructions (Test Case A) passed.")
    test_11_missing_object_classes()
    print("✓ Test 11: Missing object classes passed.")
    test_12_duplicate_object_ids()
    print("✓ Test 12: Duplicate object IDs passed.")
    test_13_llm_returning_malformed_json()
    print("✓ Test 13: LLM returning malformed JSON passed.")
    test_14_llm_returning_nonexistent_object_ids()
    print("✓ Test 14: LLM returning nonexistent object IDs passed.")
    test_15_manual_object_action_correction()
    print("✓ Test 15: Manual object-action correction passed.")
    print("\n" + "=" * 60)
    print("ALL 15 TEST SCENARIOS PASSED WITH ZERO FAILURES!")
    print("=" * 60)
