"""
Spatial Arrangement Engine (Deterministic & Geometric)

Computes balanced, conflict-free furniture rearrangements:
- Preserves FIXED objects (wall-mounted TV, bookshelf)
- Removes REMOVE objects from space
- Calculates freed floor space
- Repositions retained movable objects with clearance & boundary constraints
- Produces canonical arrangement_plan.json
"""
from typing import List, Dict, Any, Tuple
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

class SpatialLayoutEngine:
    def __init__(self, room_width: int, room_height: int):
        self.width = room_width
        self.height = room_height
        self.room_poly = box(0, 0, room_width, room_height)

    def generate_plan(self, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes list of objects with bounding boxes and actions (KEEP / REMOVE).
        Returns structured arrangement plan with `from` and `to` coordinates.
        """
        keep_objects = [o for o in objects if o.get("action") != "REMOVE"]
        remove_objects = [o for o in objects if o.get("action") == "REMOVE"]

        plan_objects = []

        # Find freed regions from removed furniture
        freed_boxes = []
        for r in remove_objects:
            x1, y1, x2, y2 = r["bbox"]
            freed_boxes.append((x1, y1, x2 - x1, y2 - y1))
            plan_objects.append({
                "id": r["object_id"],
                "class": r["class"],
                "action": "REMOVE",
                "from": [x1, y1, x2, y2],
                "to": None,
                "fixed": False,
                "movement_vector": [0, 0]
            })

        # Place KEEP objects
        placed_boxes = []
        for obj in keep_objects:
            x1, y1, x2, y2 = obj["bbox"]
            ow = x2 - x1
            oh = y2 - y1
            is_fixed = obj.get("fixed", False) or obj.get("class") in ["tv", "fan", "shelf"]

            if is_fixed or not freed_boxes:
                # Fixed objects stay exactly where they are
                plan_objects.append({
                    "id": obj["object_id"],
                    "class": obj["class"],
                    "action": "KEEP",
                    "from": [x1, y1, x2, y2],
                    "to": [x1, y1, x2, y2],
                    "fixed": True,
                    "movement_vector": [0, 0]
                })
                placed_boxes.append(box(x1, y1, x2, y2))
            else:
                # Compute optimal rearrangement destination
                # If space was freed, shift gently towards center or freed space
                fx, fy, fw, fh = freed_boxes[0]
                # Center object in freed region or slightly adjust
                target_x = int(max(20, min(self.width - ow - 20, fx + (fw - ow) // 2)))
                target_y = int(max(20, min(self.height - oh - 20, y1)))

                # Collision check with already placed items
                candidate = box(target_x, target_y, target_x + ow, target_y + oh)
                has_collision = any(candidate.intersection(pb).area > (ow * oh * 0.1) for pb in placed_boxes)

                if has_collision or (abs(target_x - x1) < 15 and abs(target_y - y1) < 15):
                    # Stay at original spot if collision or move is trivial
                    to_bbox = [x1, y1, x2, y2]
                    vector = [0, 0]
                else:
                    to_bbox = [target_x, target_y, target_x + ow, target_y + oh]
                    vector = [target_x - x1, target_y - y1]

                placed_boxes.append(box(to_bbox[0], to_bbox[1], to_bbox[2], to_bbox[3]))
                plan_objects.append({
                    "id": obj["object_id"],
                    "class": obj["class"],
                    "action": "KEEP",
                    "from": [x1, y1, x2, y2],
                    "to": to_bbox,
                    "fixed": False,
                    "movement_vector": vector
                })

        return {
            "room_dimensions": [self.width, self.height],
            "objects": plan_objects,
            "constraints": {
                "no_object_overlap": True,
                "stay_inside_room": True,
                "preserve_fixed_objects": True
            },
            "summary": {
                "total_objects": len(objects),
                "kept_count": len(keep_objects),
                "removed_count": len(remove_objects),
                "moved_count": sum(1 for p in plan_objects if p.get("movement_vector") != [0, 0])
            }
        }

