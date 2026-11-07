"""
Tanglish / Tamil / English Instruction Parser

Converts a voice transcript + detected object list into a structured 
KEEP / REMOVE / MOVE action plan.

Uses clause-based semantic pattern matching for reliable, deterministic parsing.
"""
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

REMOVE_KEYWORDS = [
    "remove pannunga", "remove pannu", "hata do", "hatao", "eduthudunga",
    "vendaam", "vendam", "venda", "remove", "delete", "nikalo",
    "discard", "clear", "edukku", "thooku"
]

KEEP_KEYWORDS = [
    "ellame venum", "ellam venum", "venum", "vaenum", "irukkattum", 
    "irukattum", "irukanum", "keep", "retain", "rakho", "need",
    "preserve", "remain", "stay"
]

ARRANGE_KEYWORDS = [
    "arrange pannunga", "arrange pannu", "neat ah", "neat-a",
    "arrange", "rearrange", "organize", "organise", "set pannu",
    "properly", "shift", "move", "adjust", "align"
]

ALL_KEYWORDS = [
    "ellam", "ellame", "ella", "everything", "all", "sab", "sabkuch", "remaining", "matha"
]

QUANTITY_MAP = {
    "oru": 1, "one": 1, "onnu": 1,
    "rendu": 2, "two": 2, "randu": 2, "irandu": 2,
    "moonu": 3, "three": 3, "mundru": 3,
    "naalu": 4, "four": 4,
}

OBJECT_ALIASES = {
    "couch": "sofa",
    "settee": "sofa",
    "dining table": "table",
    "coffee table": "table",
    "centre table": "table",
    "center table": "table",
    "television": "tv",
    "telly": "tv",
    "screen": "tv",
    "cupboard": "bookshelf",
    "wardrobe": "bookshelf",
    "almirah": "bookshelf",
    "bookcase": "bookshelf",
    "potted plant": "plant",
    "pot": "plant",
    "flower": "plant",
    "fridge": "refrigerator",
}

CANONICAL_OBJECTS = [
    "sofa", "chair", "table", "tv", "bookshelf", "shelf",
    "bed", "desk", "lamp", "plant", "fan", "refrigerator",
    "clock", "vase", "rug", "carpet", "box"
]

class InstructionParser:
    def __init__(self):
        pass

    def parse(
        self,
        transcript: str,
        detected_objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        text = transcript.strip().lower()
        if not text:
            return self._empty_result(transcript)

        # Split into sentences or major contrasting clauses (do NOT split on commas, as commas list items)
        clauses = re.split(r'[\.;\n]|(?:\s+aanaal\s+)|\bmatha\b|\bremaining\b', text)
        clauses = [c.strip() for c in clauses if c.strip()]

        keep_names = set()
        remove_names = set()
        wants_rearrange = any(kw in text for kw in ARRANGE_KEYWORDS)

        # Process each clause individually
        for clause in clauses:
            is_remove = any(re.search(r'\b' + re.escape(kw) + r'\b', clause) for kw in REMOVE_KEYWORDS)
            is_keep = any(re.search(r'\b' + re.escape(kw) + r'\b', clause) for kw in KEEP_KEYWORDS)

            found_in_clause = self._find_objects(clause)

            if is_remove and not is_keep:
                remove_names.update(found_in_clause)
            elif is_keep and not is_remove:
                keep_names.update(found_in_clause)
            elif is_remove and is_keep:
                # Disambiguate subclauses
                sub_rem = self._find_objects_near_keywords(clause, REMOVE_KEYWORDS)
                sub_keep = self._find_objects_near_keywords(clause, KEEP_KEYWORDS)
                remove_names.update(sub_rem)
                keep_names.update(sub_keep)

        # Fallback if clause splitting didn't catch due to no punctuation
        if not keep_names and not remove_names:
            sub_rem = self._find_objects_near_keywords(text, REMOVE_KEYWORDS)
            sub_keep = self._find_objects_near_keywords(text, KEEP_KEYWORDS)
            remove_names.update(sub_rem)
            keep_names.update(sub_keep)

        # Prevent overlap: an object can't be both kept and removed
        # If conflict, check nearest keyword
        conflict = keep_names.intersection(remove_names)
        for conf in conflict:
            rem_pos = max([text.rfind(kw) for kw in REMOVE_KEYWORDS if kw in text] or [-1])
            keep_pos = max([text.rfind(kw) for kw in KEEP_KEYWORDS if kw in text] or [-1])
            if rem_pos > keep_pos:
                keep_names.remove(conf)
            else:
                remove_names.remove(conf)

        # Determine mode
        if keep_names and remove_names:
            mode = "KEEP_AND_REMOVE"
        elif remove_names:
            mode = "REMOVE_ONLY"
        elif keep_names:
            mode = "KEEP_ONLY"
        else:
            mode = "REARRANGE_ALL"

        # Quantity detection (e.g. "rendu chairs")
        quantities = {}
        for qword, qnum in QUANTITY_MAP.items():
            if re.search(r'\b' + re.escape(qword) + r'\b', text):
                idx = text.find(qword)
                after = text[idx:min(len(text), idx + 35)]
                for obj in CANONICAL_OBJECTS:
                    if obj in after:
                        quantities[obj] = qnum

        # Map actions to actual detected objects
        actions = []
        counts_assigned = {}

        for obj in detected_objects:
            obj_class = obj.get("class", "").lower()
            obj_id = obj.get("object_id", "")
            action = "KEEP"  # Default according to PLACEWISE specification

            # Check if this object belongs to remove set
            matches_remove = any(self._fuzzy_match(obj_class, r) for r in remove_names)
            matches_keep = any(self._fuzzy_match(obj_class, k) for k in keep_names)

            if matches_remove:
                limit = quantities.get(obj_class, 999)
                curr = counts_assigned.get(obj_class, 0)
                if curr < limit:
                    action = "REMOVE"
                    counts_assigned[obj_class] = curr + 1
                else:
                    action = "KEEP"
            elif matches_keep:
                action = "KEEP"
            else:
                # Object not mentioned
                action = "KEEP"

            actions.append({"object_id": obj_id, "action": action})

        return {
            "mode": mode,
            "actions": actions,
            "rearrange_remaining": wants_rearrange or (mode in ["REARRANGE_ALL", "REMOVE_ONLY"]),
            "clarification_required": False,
            "clarification_message": None,
            "parsed_keep": list(keep_names),
            "parsed_remove": list(remove_names),
            "raw_transcript": transcript
        }

    def _find_objects(self, text: str) -> List[str]:
        found = []
        # Check aliases
        for alias, canon in OBJECT_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', text):
                if canon not in found:
                    found.append(canon)

        # Check canonicals
        for canon in CANONICAL_OBJECTS:
            if re.search(r'\b' + re.escape(canon) + r'(?:s|um)?\b', text):
                if canon not in found:
                    found.append(canon)
        return found

    def _find_objects_near_keywords(self, text: str, keywords: List[str]) -> List[str]:
        found = []
        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            for m in re.finditer(pattern, text):
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                ctx = text[start:end]
                for obj in self._find_objects(ctx):
                    if obj not in found:
                        found.append(obj)
        return found

    def _fuzzy_match(self, detected: str, parsed: str) -> bool:
        if detected == parsed:
            return True
        if detected in parsed or parsed in detected:
            return True
        if detected.rstrip('s') == parsed.rstrip('s'):
            return True
        return SequenceMatcher(None, detected, parsed).ratio() >= 0.75

    def _empty_result(self, transcript: str) -> Dict[str, Any]:
        return {
            "mode": "REARRANGE_ALL",
            "actions": [],
            "rearrange_remaining": True,
            "clarification_required": True,
            "clarification_message": "No voice instruction detected. Tap microphone to speak.",
            "parsed_keep": [],
            "parsed_remove": [],
            "raw_transcript": transcript
        }
