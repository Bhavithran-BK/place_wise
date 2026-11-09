"""
Tanglish / Tamil / English Instruction Parser for PLACEWISE

Converts voice transcripts + detected object lists into structured KEEP / REMOVE / MOVE action plans.

Capabilities:
1. LLM Integration: Uses Google Gemini (or configured LLM) with structured JSON output.
2. Deterministic Semantic Parser: Fallback engine handling full indoor furniture taxonomy,
   Tamil/Tanglish/English linguistic nuances, quantities, ordinals, and conjunctions.
3. Strict Schema Validation & Reconciliation:
   - Guarantees every detected object gets exactly one action (KEEP or REMOVE).
   - Never drops detected objects.
   - Eliminates hallucinated/nonexistent object IDs.
   - Unmentioned objects default to KEEP.
   - Accurately detects true ambiguity (Pattern 5) and contradiction (Pattern 6).
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from difflib import SequenceMatcher
import requests

from app.core.config import GEMINI_API_KEY, LLM_MODEL, TARGET_CLASSES

# Supported indoor object classes and synonyms
OBJECT_SYNONYMS: Dict[str, List[str]] = {
    "chair": [
        "chair", "chairs", "armchair", "armchairs", "seat", "seats",
        "naarkali", "narkaali", "naarkaali", "kurchi", "kursi"
    ],
    "table": [
        "table", "tables", "dining table", "dining tables", "desk", "desks",
        "coffee table", "tea table", "center table", "centre table",
        "meesai", "mesai", "mejai"
    ],
    "sofa": [
        "sofa", "sofas", "couch", "couches", "settee", "settees",
        "lounge", "sectional"
    ],
    "tv": [
        "tv", "tvs", "television", "televisions", "telly", "screen", "screens",
        "monitor", "monitors", "display"
    ],
    "book": [
        "book", "books", "novel", "novels", "textbook", "textbooks",
        "pothagam", "pothagangal", "puthagam", "puthagangal", "kitab", "pusthakam"
    ],
    "potted plant": [
        "potted plant", "potted plants", "plant", "plants", "pot", "pots",
        "flowerpot", "flower pot", "chedi", "chedigal", "maram", "gamla", "planter"
    ],
    "vase": [
        "vase", "vases", "flower vase", "poojaadi", "poovaadi"
    ],
    "cup": [
        "cup", "cups", "mug", "mugs", "tumbler", "tumblers", "glass", "glasses"
    ],
    "bowl": [
        "bowl", "bowls", "kinnam", "katori", "dish"
    ],
    "bed": [
        "bed", "beds", "cot", "cots", "mattress", "padukkai", "kattil"
    ],
    "clock": [
        "clock", "clocks", "wall clock", "watch", "gadiyaram", "kadigaram"
    ],
    "refrigerator": [
        "refrigerator", "fridge", "fridges", "kulirsaadhanapetti"
    ],
    "bookshelf": [
        "bookshelf", "bookshelves", "bookcase", "shelf", "shelves",
        "cupboard", "almirah", "bureau", "wardrobe"
    ],
    "lamp": [
        "lamp", "lamps", "light", "lights", "vilakku"
    ],
    "laptop": [
        "laptop", "laptops", "computer", "notebook"
    ]
}

# Inverted mapping: keyword -> canonical class
KEYWORD_TO_CLASS: Dict[str, str] = {}
for canon, synonyms in OBJECT_SYNONYMS.items():
    for syn in synonyms:
        KEYWORD_TO_CLASS[syn.lower()] = canon

# Action keywords
REMOVE_KEYWORDS = [
    "remove pannunga", "remove pannu", "eduthudunga", "thooku", "thookidunga",
    "vendaam", "vendam", "venda", "vendham", "remove", "delete", "discard",
    "clear", "get rid of", "take away", "hata do", "hatao", "nikalo"
]

KEEP_KEYWORDS = [
    "venum", "vaenum", "irukkattum", "irukattum", "irukanum", "mattum venum",
    "keep", "retain", "preserve", "leave", "stay", "remain", "save",
    "rakho", "rahne do"
]

ARRANGE_KEYWORDS = [
    "arrange pannunga", "arrange pannu", "neat ah", "neat-a", "neatly",
    "arrange", "rearrange", "organize", "organise", "set pannu",
    "properly", "shift", "reposition", "adjust", "align"
]

QUANTITY_MAP = {
    "oru": 1, "onnu": 1, "one": 1, "single": 1,
    "rendu": 2, "randu": 2, "irandu": 2, "two": 2, "both": 2,
    "moonu": 3, "mundru": 3, "three": 3,
    "naalu": 4, "four": 4,
    "anji": 5, "aindhu": 5, "five": 5
}

ORDINAL_MAP = {
    "first": 1, "1st": 1, "modal": 1, "modhal": 1,
    "second": 2, "2nd": 2, "rendavathu": 2, "irandavathu": 2,
    "third": 3, "3rd": 3, "moonavathu": 3
}

ALL_INDICATORS = ["all", "all the", "every", "both", "ellam", "ellame", "ella", "sab", "sabkuch"]


class InstructionParser:
    """
    Parses natural language instructions (Tanglish, Tamil, English) into
    structured spatial action plans with strict validation.
    """

    def __init__(self):
        self.api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.model = LLM_MODEL or os.getenv("LLM_MODEL", "gemini-2.5-flash")

    def parse(
        self,
        transcript: str,
        detected_objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Main entry point for instruction parsing.
        Attempts LLM parsing first if API key is present, and falls back to
        the robust semantic parser. Reconciles and validates every plan.
        """
        clean_text = (transcript or "").strip()
        if not clean_text:
            return self._empty_result(clean_text, detected_objects)

        # 1. Normalize detected objects to ensure class and object_id exist
        normalized_objects = self._normalize_detected_objects(detected_objects)

        # 2. Try LLM parsing if configured
        plan = None
        if self.api_key:
            try:
                plan = self._call_gemini_llm(clean_text, normalized_objects)
            except Exception as e:
                print(f"[InstructionParser] LLM call failed ({e}). Using deterministic semantic parser.")
                plan = None

        # 3. Fallback to deterministic semantic parser if LLM was unavailable or failed
        if not plan:
            plan = self._deterministic_parse(clean_text, normalized_objects)

        # 4. Mandatory independent validation & reconciliation against detected objects
        validated_plan = self.validate_and_reconcile_action_plan(
            plan=plan,
            detected_objects=normalized_objects,
            transcript=clean_text
        )

        return validated_plan

    # ──────────────────────────────────────────────────────────────────────────
    # LLM INTEGRATION (Gemini REST API)
    # ──────────────────────────────────────────────────────────────────────────

    def _call_gemini_llm(self, transcript: str, detected_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Calls Google Gemini API using structured JSON output mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        system_instruction = (
            "You are the NLU Instruction Parser for PLACEWISE, an AI room rearrangement system. "
            "Your job is to parse Tanglish (Tamil+English code-mixed), Tamil, or English user instructions "
            "and assign KEEP or REMOVE actions to a given list of detected furniture and room objects.\n\n"
            "CRITICAL RULES:\n"
            "1. Every detected object must receive an action ('KEEP' or 'REMOVE').\n"
            "2. Unmentioned objects default to 'KEEP'.\n"
            "3. If user only says what to remove ('Chair remove pannunga'), mark those REMOVE and keep everything else.\n"
            "4. If user says 'all books' or 'all chairs', match all items of that class.\n"
            "5. If user says 'both sofas', match all two sofas.\n"
            "6. If user is ambiguous (e.g. 'remove that chair' or 'one chair' when multiple chairs exist with no specifier), "
            "set clarification_required = true, and formulate a clear clarification_message.\n"
            "7. If user is contradictory (e.g. 'chair remove pannunga, chair venum'), "
            "set clarification_required = true and ask which action they prefer.\n"
            "8. If user asks to arrange/rearrange everything ('Neat ah arrange pannunga', 'Ellathayum arrange pannunga'), "
            "keep all objects and set rearrange_remaining = true.\n"
            "9. Never invent object IDs. Use only the exact object_id provided in the detected objects list.\n\n"
            "OUTPUT JSON SCHEMA:\n"
            "{\n"
            '  "mode": "REMOVE_ONLY" | "KEEP_ONLY" | "KEEP_AND_REMOVE" | "REARRANGE_ALL",\n'
            '  "actions": [\n'
            '    {"object_id": "string", "object_class": "string", "action": "KEEP"|"REMOVE", "reason": "string"}\n'
            "  ],\n"
            '  "rearrange_remaining": boolean,\n'
            '  "clarification_required": boolean,\n'
            '  "clarification_message": string | null\n'
            "}"
        )

        objs_repr = [
            {"object_id": o["object_id"], "class": o["class"], "fixed": o.get("fixed", False)}
            for o in detected_objects
        ]

        user_content = (
            f"Detected Objects in Room:\n{json.dumps(objs_repr, indent=2)}\n\n"
            f"User Voice Transcript:\n\"{transcript}\""
        )

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_instruction}\n\n{user_content}"}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            raise Exception(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        raw_json_str = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        parsed = json.loads(raw_json_str)
        return parsed

    # ──────────────────────────────────────────────────────────────────────────
    # DETERMINISTIC SEMANTIC PARSER (High-Precision Fallback & Offline Engine)
    # ──────────────────────────────────────────────────────────────────────────

    def _deterministic_parse(
        self,
        transcript: str,
        detected_objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Robust semantic parser handling Tamil, Tanglish, and English without an external LLM.
        Accurately handles all 6 spec patterns, conjunctions, plurals, and counts.
        """
        text = transcript.strip().lower()
        
        # Check for full rearrangement request ("neat ah arrange pannunga", "ellathayum arrange")
        wants_full_arrange = any(kw in text for kw in ARRANGE_KEYWORDS) and (
            any(w in text for w in ["ellam", "ellame", "ellathayum", "everything", "all", "whole"])
            or not any(rk in text for rk in REMOVE_KEYWORDS)
        )

        # Extract targeted actions per class first
        remove_targets, keep_targets = self._extract_targets_per_action(text, detected_objects)

        # Check for contradiction (user mentions both KEEP and REMOVE on the exact same class)
        contradiction_class = None
        contradiction_msg = None
        conflict = set(remove_targets.keys()).intersection(set(keep_targets.keys()))
        if conflict:
            has_contrast = any(c in text for c in ["aanaal", "but", "however", "instead"])
            if not has_contrast:
                conf_item = list(conflict)[0]
                contradiction_class = conf_item
                contradiction_msg = f"Contradiction detected: you requested both keeping and removing the {conf_item}. Which action do you prefer?"

        # Check for ambiguity (e.g., singular "one chair" / "andha chair" when multiple exist)
        clarification_req = False
        clarification_msg = None
        clarification_cands: List[str] = []

        if contradiction_class:
            clarification_req = True
            clarification_msg = contradiction_msg
        else:
            ambig_res = self._check_ambiguity(text, remove_targets, detected_objects)
            if ambig_res:
                clarification_req = True
                clarification_msg = ambig_res["message"]
                clarification_cands = ambig_res["candidates"]

        # Build actions for all detected objects
        actions = []
        class_remove_counter: Dict[str, int] = {}

        for obj in detected_objects:
            obj_id = obj["object_id"]
            obj_class = obj["class"]
            action = "KEEP"
            reason = "Defaulted to KEEP (unmentioned object)"

            if obj_class in remove_targets and not clarification_req:
                target_spec = remove_targets[obj_class]
                max_rem = target_spec.get("count", 999)
                curr_rem = class_remove_counter.get(obj_class, 0)

                # Check ordinal target ("first chair", "second chair")
                if "ordinal" in target_spec:
                    target_ord = target_spec["ordinal"]
                    idx_match = re.search(r'_(\d+)$', obj_id)
                    obj_idx = int(idx_match.group(1)) if idx_match else (curr_rem + 1)
                    if obj_idx == target_ord:
                        action = "REMOVE"
                        reason = f"Explicitly requested removal (item #{target_ord})"
                    else:
                        action = "KEEP"
                        reason = f"Preserved (only item #{target_ord} requested for removal)"
                elif curr_rem < max_rem:
                    action = "REMOVE"
                    class_remove_counter[obj_class] = curr_rem + 1
                    reason = "Explicitly requested by user for removal"
                else:
                    action = "KEEP"
                    reason = "Preserved (removal quota for class reached)"

            elif obj_class in keep_targets:
                action = "KEEP"
                reason = "Explicitly requested by user to be kept"

            actions.append({
                "object_id": obj_id,
                "object_class": obj_class,
                "action": action,
                "reason": reason
            })

        # Determine overall mode
        parsed_rem = list(remove_targets.keys())
        parsed_kp = list(keep_targets.keys())

        if (any(a["action"] == "REMOVE" for a in actions) and any(a["object_class"] in keep_targets for a in actions)) or (parsed_rem and parsed_kp):
            mode = "KEEP_AND_REMOVE"
        elif any(a["action"] == "REMOVE" for a in actions) or parsed_rem:
            mode = "REMOVE_ONLY"
        elif any(a["object_class"] in keep_targets for a in actions) or parsed_kp:
            mode = "KEEP_ONLY"
        else:
            mode = "REARRANGE_ALL"

        rearrange_rem = any(kw in text for kw in ARRANGE_KEYWORDS) or mode == "REARRANGE_ALL"

        return {
            "mode": mode,
            "actions": actions,
            "rearrange_remaining": rearrange_rem,
            "clarification_required": clarification_req,
            "clarification_message": clarification_msg,
            "clarification_candidates": clarification_cands,
            "parsed_keep": list(keep_targets.keys()),
            "parsed_remove": list(remove_targets.keys()),
            "raw_transcript": transcript
        }

    # ──────────────────────────────────────────────────────────────────────────
    # LINGUISTIC TARGET EXTRACTION HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _smart_split_clauses(self, text: str) -> List[str]:
        """
        Splits text into meaningful syntactic action clauses while preserving
        comma-separated noun lists ('Sofa, TV, bookshelf ellame venum').
        """
        all_action_kw = REMOVE_KEYWORDS + KEEP_KEYWORDS + ARRANGE_KEYWORDS

        def has_verb(t: str) -> bool:
            return any(re.search(r'\b' + re.escape(kw) + r'\b', t) for kw in all_action_kw)

        delims = (
            r'[\.;\n]|(?:\s+aanaal\s+)|\bbut\b|\bhowever\b|\bremaining\b|\bmatha\b|,'
            r'|(?:\s+and\s+(?=(?:keep|remove|arrange|vendaam|venum|vaenum|eduthudunga|delete)))'
        )
        raw_segments = [s.strip() for s in re.split(delims, text, flags=re.IGNORECASE) if s.strip()]

        merged_clauses: List[str] = []
        curr = ""
        for seg in raw_segments:
            if curr:
                curr += ", " + seg
            else:
                curr = seg
            if has_verb(curr):
                merged_clauses.append(curr)
                curr = ""

        if curr:
            if merged_clauses:
                merged_clauses[-1] += ", " + curr
            else:
                merged_clauses.append(curr)

        return merged_clauses or [text]

    def _extract_targets_per_action(
        self,
        text: str,
        detected_objects: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """
        Parses text into clauses and identifies which classes are targeted for REMOVE vs KEEP.
        Returns (remove_targets, keep_targets) where each value is metadata like count/ordinal.
        """
        clauses = self._smart_split_clauses(text)

        remove_targets: Dict[str, Dict[str, Any]] = {}
        keep_targets: Dict[str, Dict[str, Any]] = {}

        for clause in clauses:
            is_rem = any(re.search(r'\b' + re.escape(kw) + r'\b', clause) for kw in REMOVE_KEYWORDS)
            is_keep = any(re.search(r'\b' + re.escape(kw) + r'\b', clause) for kw in KEEP_KEYWORDS)

            found_classes = self._find_classes_in_text(clause)

            if is_rem and not is_keep:
                for cls_name in found_classes:
                    spec = self._extract_class_spec(clause, cls_name)
                    remove_targets[cls_name] = spec
            elif is_keep and not is_rem:
                for cls_name in found_classes:
                    spec = self._extract_class_spec(clause, cls_name)
                    keep_targets[cls_name] = spec
            elif is_rem and is_keep:
                # If clause has both, split by proximity to keywords
                for cls_name in found_classes:
                    pos = clause.find(cls_name)
                    rem_distances = [
                        abs(pos - m.start()) for kw in REMOVE_KEYWORDS
                        for m in re.finditer(r'\b' + re.escape(kw) + r'\b', clause)
                    ]
                    keep_distances = [
                        abs(pos - m.start()) for kw in KEEP_KEYWORDS
                        for m in re.finditer(r'\b' + re.escape(kw) + r'\b', clause)
                    ]
                    min_rem = min(rem_distances) if rem_distances else 9999
                    min_keep = min(keep_distances) if keep_distances else 9999

                    spec = self._extract_class_spec(clause, cls_name)
                    if min_rem <= min_keep:
                        remove_targets[cls_name] = spec
                    else:
                        keep_targets[cls_name] = spec

        # Fallback if no clauses had keywords (e.g. stream without punctuation)
        if not remove_targets and not keep_targets:
            found_classes = self._find_classes_in_text(text)
            is_rem = any(kw in text for kw in REMOVE_KEYWORDS)
            is_keep = any(kw in text for kw in KEEP_KEYWORDS)
            for c in found_classes:
                spec = self._extract_class_spec(text, c)
                if is_rem and not is_keep:
                    remove_targets[c] = spec
                elif is_keep and not is_rem:
                    keep_targets[c] = spec

        return remove_targets, keep_targets

    def _extract_class_spec(self, text: str, cls_name: str) -> Dict[str, Any]:
        """Extracts numerical limits, ordinals, and demonstratives for an object class."""
        spec: Dict[str, Any] = {"count": 999}  # Default to all matching items

        # 1. Check if all-indicator is present ("all", "both", "ellam", "ellame")
        if any(ai in text for ai in ALL_INDICATORS):
            spec["count"] = 999
            spec["is_all"] = True

        # 2. Check for explicit numerals (e.g. "two chairs", "rendu chairs", "moonu")
        has_numeral = False
        for qword, qnum in QUANTITY_MAP.items():
            pattern = r'\b' + re.escape(qword) + r'\s+(?:\w+\s+)?' + re.escape(cls_name)
            if re.search(pattern, text) or (qword in text and abs(text.find(qword) - text.find(cls_name)) < 25):
                spec["count"] = qnum
                spec["explicit_count"] = True
                has_numeral = True
                if qnum > 1:
                    return spec
                break

        # 3. Check for ordinals ("first chair", "second chair", "rendavathu chair")
        for oword, onum in ORDINAL_MAP.items():
            pattern = r'\b' + re.escape(oword) + r'\s+' + re.escape(cls_name)
            if re.search(pattern, text):
                spec["ordinal"] = onum
                spec["count"] = 1
                return spec

        # 4. Check for coordinate "-um" suffix in Tamil (e.g. "chair-um table-um")
        if re.search(re.escape(cls_name) + r'-um\b', text) or re.search(re.escape(cls_name) + r'um\b', text):
            spec["count"] = 999
            spec["is_all"] = True
            return spec

        # 5. Check for demonstrative singular ("andha chair", "that chair", "indha chair", "one chair")
        # Only when no multi-item numeral was used
        if not has_numeral or spec.get("count") == 1:
            demonstratives = ["andha", "indha", "that", "this", "oru", "one"]
            for d in demonstratives:
                pattern = r'\b' + re.escape(d) + r'\s+' + re.escape(cls_name) + r'\b'
                if re.search(pattern, text):
                    spec["count"] = 1
                    spec["demonstrative"] = True
                    spec["explicit_count"] = True
                    return spec

        return spec

    def _find_classes_in_text(self, text: str) -> List[str]:
        """Finds all canonical object classes present in the text."""
        matched: List[str] = []
        
        # Sort synonyms by length descending to match multi-word phrases first ("potted plant" before "plant")
        sorted_synonyms = sorted(KEYWORD_TO_CLASS.keys(), key=len, reverse=True)

        for syn in sorted_synonyms:
            canon = KEYWORD_TO_CLASS[syn]
            pattern = r'\b' + re.escape(syn) + r'(?:s|es|um|gal|kal|nga)?\b'
            if re.search(pattern, text):
                if canon not in matched:
                    matched.append(canon)

        return matched

    def _find_classes_near_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """Finds classes located physically near the given action keywords."""
        found = []
        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            for m in re.finditer(pattern, text):
                start = max(0, m.start() - 35)
                end = min(len(text), m.end() + 35)
                ctx = text[start:end]
                for c in self._find_classes_in_text(ctx):
                    if c not in found:
                        found.append(c)
        return found

    def _check_contradiction(
        self,
        text: str,
        detected_objects: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Pattern 6: Detects if the user asked to both REMOVE and KEEP the exact same class
        within the same instruction without a resolving contrast (e.g. 'Chair remove pannunga, chair venum').
        """
        rem_found = set(self._find_classes_near_keywords(text, REMOVE_KEYWORDS))
        keep_found = set(self._find_classes_near_keywords(text, KEEP_KEYWORDS))

        direct_conflict = rem_found.intersection(keep_found)
        if direct_conflict:
            # Check if there is a contrast word like "but", "however", "aanaal"
            has_contrast = any(c in text for c in ["aanaal", "but", "however", "instead"])
            if not has_contrast:
                conf_item = list(direct_conflict)[0]
                return (
                    conf_item,
                    f"Contradiction detected: you requested both keeping and removing the {conf_item}. Which action do you prefer?"
                )

        return None, None

    def _check_ambiguity(
        self,
        text: str,
        remove_targets: Dict[str, Dict[str, Any]],
        detected_objects: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Pattern 5: Detects if the user ambiguously specifies a single item
        (e.g., 'Andha chair remove pannunga' / 'Remove one chair') when multiple exist.
        """
        # Group detected objects by class
        by_class: Dict[str, List[str]] = {}
        for o in detected_objects:
            by_class.setdefault(o["class"], []).append(o["object_id"])

        for r_cls, spec in remove_targets.items():
            matching_ids = by_class.get(r_cls, [])
            if len(matching_ids) > 1:
                # Multiple items of this class exist in room
                count = spec.get("count", 999)
                is_demonstrative = spec.get("demonstrative", False)
                has_ordinal = "ordinal" in spec
                is_all = spec.get("is_all", False)

                # Check if demonstrative or single item without ordinal
                if (is_demonstrative or count == 1) and not is_all and not has_ordinal and count < len(matching_ids):
                    return {
                        "class": r_cls,
                        "candidates": matching_ids,
                        "message": (
                            f"Multiple {r_cls}s detected ({', '.join(matching_ids)}). "
                            f"Please select which specific {r_cls} you would like to remove."
                        )
                    }

        return None

    # ──────────────────────────────────────────────────────────────────────────
    # VALIDATION & RECONCILIATION ENGINE
    # ──────────────────────────────────────────────────────────────────────────

    def validate_and_reconcile_action_plan(
        self,
        plan: Dict[str, Any],
        detected_objects: List[Dict[str, Any]],
        transcript: str
    ) -> Dict[str, Any]:
        """
        Independently validates and reconciles any generated plan against detected_objects.
        Guarantees:
        1. Every detected object receives exactly one action.
        2. No nonexistent object IDs exist in the plan.
        3. Actions are normalized to 'KEEP' or 'REMOVE'.
        4. Unmentioned objects default to KEEP.
        5. Ambiguity and contradiction fields are preserved cleanly.
        """
        detected_id_map = {o["object_id"]: o for o in detected_objects}
        raw_actions = plan.get("actions", [])

        reconciled_actions = []
        handled_ids: Set[str] = set()

        # 1. Process actions provided by parser / LLM
        for act in raw_actions:
            obj_id = act.get("object_id")
            if not obj_id or obj_id not in detected_id_map:
                # Discard hallucinated or nonexistent object IDs
                continue

            if obj_id in handled_ids:
                # Discard duplicate assignments
                continue

            target_obj = detected_id_map[obj_id]
            action_val = str(act.get("action", "KEEP")).upper()
            if action_val not in ["KEEP", "REMOVE", "MOVE"]:
                action_val = "KEEP"

            reason = act.get("reason") or ("Explicitly requested by user" if action_val == "REMOVE" else "Retained in room")

            reconciled_actions.append({
                "object_id": obj_id,
                "object_class": target_obj["class"],
                "action": action_val,
                "reason": reason
            })
            handled_ids.add(obj_id)

        # 2. Fill in any detected objects that were missing from the action list
        for obj in detected_objects:
            obj_id = obj["object_id"]
            if obj_id not in handled_ids:
                reconciled_actions.append({
                    "object_id": obj_id,
                    "object_class": obj["class"],
                    "action": "KEEP",
                    "reason": "Unmentioned object defaults to KEEP"
                })
                handled_ids.add(obj_id)

        # 3. Mode validation
        mode = plan.get("mode")
        parsed_rem = plan.get("parsed_remove", [])
        parsed_kp = plan.get("parsed_keep", [])
        removes = [a for a in reconciled_actions if a["action"] == "REMOVE"]
        keeps = [a for a in reconciled_actions if a["action"] == "KEEP"]
        explicit_keeps = [k for k in keeps if k.get("reason") and "Explicitly" in k["reason"]]

        if (removes and explicit_keeps) or (parsed_rem and parsed_kp):
            mode = "KEEP_AND_REMOVE"
        elif removes or parsed_rem:
            mode = "REMOVE_ONLY"
        elif explicit_keeps or parsed_kp:
            mode = "KEEP_ONLY"
        elif not mode or mode not in ["REMOVE_ONLY", "KEEP_ONLY", "KEEP_AND_REMOVE", "REARRANGE_ALL"]:
            mode = "REARRANGE_ALL"

        return {
            "mode": mode,
            "actions": reconciled_actions,
            "rearrange_remaining": bool(plan.get("rearrange_remaining", False)),
            "clarification_required": bool(plan.get("clarification_required", False)),
            "clarification_message": plan.get("clarification_message"),
            "clarification_candidates": plan.get("clarification_candidates", []),
            "parsed_keep": plan.get("parsed_keep", []),
            "parsed_remove": plan.get("parsed_remove", []),
            "raw_transcript": transcript
        }

    def _normalize_detected_objects(self, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensures every object dictionary has a unique 'object_id' and valid 'class' key."""
        normalized = []
        class_counts: Dict[str, int] = {}
        seen_ids: Set[str] = set()

        for idx, obj in enumerate(objects):
            cls_name = (obj.get("class") or obj.get("class_name") or "furniture").strip().lower()
            if cls_name == "couch":
                cls_name = "sofa"
            elif cls_name == "dining table":
                cls_name = "table"

            class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
            obj_id = obj.get("object_id")

            # If missing or duplicate, generate a unique sequential ID
            if not obj_id or obj_id in seen_ids:
                obj_id = f"{cls_name}_{class_counts[cls_name]:02d}"
                while obj_id in seen_ids:
                    class_counts[cls_name] += 1
                    obj_id = f"{cls_name}_{class_counts[cls_name]:02d}"

            seen_ids.add(obj_id)
            norm_obj = dict(obj)
            norm_obj["class"] = cls_name
            norm_obj["object_id"] = obj_id
            normalized.append(norm_obj)

        return normalized

    def _empty_result(self, transcript: str, detected_objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Safe default result when empty transcript is provided."""
        actions = [
            {
                "object_id": o.get("object_id", f"obj_{i:02d}"),
                "object_class": o.get("class", "furniture"),
                "action": "KEEP",
                "reason": "No instruction given; kept by default"
            }
            for i, o in enumerate(detected_objects, 1)
        ]
        return {
            "mode": "REARRANGE_ALL",
            "actions": actions,
            "rearrange_remaining": True,
            "clarification_required": True,
            "clarification_message": "No voice instruction detected. Tap microphone to speak.",
            "clarification_candidates": [],
            "parsed_keep": [],
            "parsed_remove": [],
            "raw_transcript": transcript
        }
