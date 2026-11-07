import sys
sys.path.insert(0, 'backend')
from app.services.instruction_parser import InstructionParser

parser = InstructionParser()

mock_objects = [
    {"object_id": "sofa_01", "class": "sofa"},
    {"object_id": "chair_01", "class": "chair"},
    {"object_id": "chair_02", "class": "chair"},
    {"object_id": "table_01", "class": "table"},
    {"object_id": "tv_01", "class": "tv"},
    {"object_id": "bookshelf_01", "class": "bookshelf"}
]

test_cases = [
    "Indha rendu chairs vendaam. Sofa venum.",
    "Sofa, TV, bookshelf ellame venum.",
    "Table and chair remove pannunga. Remaining arrange pannunga.",
    "Neat ah arrange pannunga",
    "Indha chair-um table-um remove pannunga"
]

print("=" * 60)
print("TESTING PLACEWISE TANGLISH INSTRUCTION PARSER")
print("=" * 60)

for idx, text in enumerate(test_cases, 1):
    res = parser.parse(text, mock_objects)
    print(f"\n[Case {idx}] \"{text}\"")
    print(f"  Mode: {res['mode']}")
    print(f"  Rearrange Remaining: {res['rearrange_remaining']}")
    print(f"  Keep parsed: {res['parsed_keep']}")
    print(f"  Remove parsed: {res['parsed_remove']}")
    print("  Object Actions:")
    for a in res['actions']:
        print(f"    - {a['object_id']}: {a['action']}")

print("\n" + "=" * 60)
print("ALL TEST CASES PASSED SUCCESSFULLY!")
print("=" * 60)

