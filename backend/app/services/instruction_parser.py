"""
Tanglish / Tamil / English Instruction Parser

Converts a voice transcript + detected object list into a structured 
KEEP / REMOVE / MOVE action plan.

Implements all 6 instruction patterns required by the PLACEWISE specification:
1. Only says what to remove -> keep everything else ("chair vendaam")
2. Only says what to keep -> remove nothing unless explicit ("sofa venum")
3. Says both -> apply both lists ("chairs vendaam, sofa venum")
4. Says "arrange everything" -> keep all, rearrange ("neat ah arrange pannunga")
5. Ambiguous reference -> ask for clarification ("Which chair? Tap to select")
6. Contradictory -> asks which takes priority
"""
import re
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

REMOVE_KEYWORDS = [
    "remove pannunga", "remove pannu", "hata do", "hatao", "eduthudunga",
    "vendaam", "vendam", "venda", "remove", "delete", "nikalo",
    "discard", "clear", "edukku", "thooku", "vendham"
]

KEEP_KEYWORDS = [
    "ellame venum", "ellam venum", "venum", "vaenum", "irukkattum", 
    "irukattum", "irukanum", "keep", "retain", "rakho", "need",
    "preserve", "remain", "stay", "vaenum"
]

ARRANGE_KEYWORDS = [
    "arrange pannunga", "arrange pannu", "neat ah", "neat-a",
    "arrange", "rearrange", "organize", "organise", "set pannu",
    "properly", "shift", "move", "adjust", "align"
]

ALL_KEYWORDS = [
    "ellam", "ellame", "ella", "everything", "all", "sab", "sabkuch", "remaining", "matha", "both"
]

QUANTITY_MAP = {
    "oru": 1, "one": 1, "onnu": 1,
    "rendu": 2, "two": 2, "randu": 2, "irandu": 2, "both": 2,
    "moonu": 3, "three": 3, "mundru": 3,
    "naalu": 4, "four": 4,
}

ORDINAL_MAP = {
    "first": 1, "modal": 1, "modhal": 1, "1st": 1, "one": 1,
    "second": 2, "rendavathu": 2, "irandavathu": 2, "2nd": 2, "two": 2,
    "third": 3, "moonavathu": 3, "3rd": 3, "three": 3,
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

        # Split into sentences or major contrasting clauses
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

        # Fallback if clause splitting didn't catch due to unpunctuated stream
        if not keep_names and not remove_names:
            sub_rem = self._find_objects_near_keywords(text, REMOVE_KEYWORDS)
            sub_keep = self._find_objects_near_keywords(text, KEEP_KEYWORDS)
            remove_names.update(sub_rem)
            keep_names.update(sub_keep)

        # Check for contradictions (exact same object claimed by both keep and remove)
        contradiction_found = False
        contradiction_msg = None
        conflict = keep_names.intersection(remove_names)
        if conflict:
            # If text explicitly has contrast ("aanaal" / "but"), latest clause wins,
            # otherwise flag as contradictory per spec requirement #6
            has_contrast = any(c in text for c in ["aanaal", "but", "however", "instead"])
            if not has_contrast and len(conflict) > 0:
                conf_item = list(conflict)[0]
                contradiction_found = True
                contradiction_msg = f"Contradiction detected: you mentioned both keeping and removing the {conf_item}. Which takes priority?"
            
            # Resolve the conflict in the sets
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

        # Quantity detection (e.g. "rendu chairs", "oru chair")
        quantities = {}
        for qword, qnum in QUANTITY_MAP.items():
            if re.search(r'\b' + re.escape(qword) + r'\b', text):
                idx = text.find(qword)
                after = text[idx:min(len(text), idx + 35)]
                for obj in CANONICAL_OBJECTS:
                    if obj in after:
                        quantities[obj] = qnum

        # Ordinal target detection (e.g. "first chair", "second chair")
        ordinal_targets = {}
        for oword, onum in ORDINAL_MAP.items():
            if re.search(r'\b' + re.escape(oword) + r'\b', text):
                idx = text.find(oword)
                after = text[idx:min(len(text), idx + 35)]
                for obj in CANONICAL_OBJECTS:
                    if obj in after:
                        ordinal_targets[obj] = onum

        # Ambiguity check (spec requirement #5: "Which chair? Tap to select.")
        clarification_required = contradiction_found
        clarification_message = contradiction_msg
        clarification_candidates = []

        if not clarification_required and remove_names:
            # Group detected objects by class
            detected_by_class: Dict[str, List[str]] = {}
            for o in detected_objects:
                cls_ = o.get("class", "").lower()
                detected_by_class.setdefault(cls_, []).append(o.get("object_id", ""))

            for r_obj in remove_names:
                matching_objs = detected_by_class.get(r_obj, [])
                if len(matching_objs) > 1:
                    # Multiple items of this class exist.
                    # Check if user specified quantity (e.g. "rendu", "all", "ellam") or ordinal ("first")
                    has_explicit_count = r_obj in quantities or any(k in text for k in ALL_KEYWORDS)
                    has_ordinal = r_obj in ordinal_targets
                    is_plural = bool(re.search(r'\b' + re.escape(r_obj) + r'(?:s|gal|kal)\b', text))

                    if not has_explicit_count and not has_ordinal and not is_plural:
                        # Ambiguous singular reference: e.g. "Indha chair vendaam" when 2 chairs exist
                        clarification_required = True
                        clarification_candidates = matching_objs
                        clarification_message = f"Multiple {r_obj}s detected ({', '.join(matching_objs)}). Tap to specify which one to remove."
                        break

        # Map actions to actual detected objects
        actions = []
        counts_assigned: Dict[str, int] = {}
        class_index_tracker: Dict[str, int] = {}

        for obj in detected_objects:
            obj_class = obj.get("class", "").lower()
            obj_id = obj.get("object_id", "")
            class_index_tracker[obj_class] = class_index_tracker.get(obj_class, 0) + 1
            curr_idx = class_index_tracker[obj_class]

            action = "KEEP"  # Default according to PLACEWISE specification

            matches_remove = any(self._fuzzy_match(obj_class, r) for r in remove_names)
            matches_keep = any(self._fuzzy_match(obj_class, k) for k in keep_names)

            if matches_remove:
                # If ordinal specified ("second chair")
                if obj_class in ordinal_targets:
                    if curr_idx == ordinal_targets[obj_class]:
                        action = "REMOVE"
                    else:
                        action = "KEEP"
                else:
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
                action = "KEEP"

            actions.append({"object_id": obj_id, "action": action})

        return {
            "mode": mode,
            "actions": actions,
            "rearrange_remaining": wants_rearrange or (mode in ["REARRANGE_ALL", "REMOVE_ONLY"]),
            "clarification_required": clarification_required,
            "clarification_message": clarification_message,
            "clarification_candidates": clarification_candidates,
            "parsed_keep": list(keep_names),
            "parsed_remove": list(remove_names),
            "raw_transcript": transcript
        }

    def _find_objects(self, text: str) -> List[str]:
        found = []
        for alias, canon in OBJECT_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', text):
                if canon not in found:
                    found.append(canon)

        for canon in CANONICAL_OBJECTS:
            if re.search(r'\b' + re.escape(canon) + r'(?:s|um|gal|kal)?\b', text):
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
            "clarification_candidates": [],
            "parsed_keep": [],
            "parsed_remove": [],
            "raw_transcript": transcript
        }
