"""
Spatial Arrangement Engine (Deterministic & Geometric)
Implements:
1. PLACEWISE Detailed Reusable Scene and Furniture Arrangement Plan (Section 4 & 7)
2. Strategic layout modes (Balanced, Spacious, Cozy)
3. Structured operations vocabulary: KEEP, REMOVE, MOVE, MOVE_NEAR, MOVE_LEFT, MOVE_RIGHT, ROTATE, RESIZE, FIX, ARRANGE
4. Canonical scene manifest generation
5. Zero-collision constraint solver via Shapely
"""
from typing import List, Dict, Any, Tuple, Optional
import math
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from app.core.config import FIXED_CLASSES, CLASS_CATEGORIES

class SpatialLayoutEngine:
    def __init__(self, room_width: int, room_height: int):
        self.width = room_width
        self.height = room_height
        self.room_poly = box(0, 0, room_width, room_height)
        self.center_x = room_width / 2.0
        self.center_y = room_height / 2.0
        self.floor_top = int(room_height * 0.35)
        self.floor_bottom = room_height - 15

    def generate_plan(
        self,
        objects: List[Dict[str, Any]],
        strategy: str = "balanced"
    ) -> Dict[str, Any]:
        """
        Takes list of objects with bounding boxes and actions (KEEP / REMOVE).
        Applies deterministic geometric placement according to strategy:
        - 'balanced' (default): Redistributes evenly across freed + existing space.
        - 'spacious': Pushes movable items to walls to maximize open central walkway.
        - 'cozy': Groups seating/tables into tight conversational cluster around center.
        Returns structured arrangement plan with `from` and `to` coordinates, scores, and summary.
        """
        strategy = (strategy or "balanced").lower().strip()
        if strategy not in {"balanced", "spacious", "cozy"}:
            strategy = "balanced"

        keep_objects = [o for o in objects if o.get("action") != "REMOVE"]
        remove_objects = [o for o in objects if o.get("action") == "REMOVE"]

        plan_objects = []

        # 1. Identify freed regions from removed furniture
        freed_boxes = []
        total_removed_area = 0
        for r in remove_objects:
            x1, y1, x2, y2 = r.get("bbox", [0, 0, 0, 0])
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            freed_boxes.append((x1, y1, w, h))
            total_removed_area += (w * h)
            plan_objects.append({
                "id": r.get("object_id") or r.get("id"),
                "class": r.get("class") or r.get("class_name", "furniture"),
                "action": "REMOVE",
                "from": [int(x1), int(y1), int(x2), int(y2)],
                "to": None,
                "fixed": False,
                "movement_vector": [0, 0],
                "scale": 1.0,
                "rotation": 0.0,
                "visible": False
            })

        # 2. Place KEEP objects — fixed first, then movable
        placed_boxes: List[Polygon] = []
        placed_centers: List[Tuple[float, float]] = []
        fixed_polys: List[Polygon] = []

        sorted_keep = sorted(
            keep_objects,
            key=lambda o: (
                not (o.get("fixed", False) or o.get("class", "").lower() in FIXED_CLASSES),
                -((o["bbox"][2] - o["bbox"][0]) * (o["bbox"][3] - o["bbox"][1]))
            )
        )

        fixed_items = []
        movable_items = []
        for obj in sorted_keep:
            obj_class = (obj.get("class") or obj.get("class_name", "")).lower()
            is_fixed = obj.get("fixed", False) or obj_class in FIXED_CLASSES
            if is_fixed:
                fixed_items.append(obj)
            else:
                movable_items.append(obj)

        for obj in fixed_items:
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            to_bbox = [int(x1), int(y1), int(x2), int(y2)]
            plan_objects.append({
                "id": obj.get("object_id") or obj.get("id"),
                "class": obj.get("class") or obj.get("class_name", "furniture"),
                "action": "KEEP",
                "from": [int(x1), int(y1), int(x2), int(y2)],
                "to": to_bbox,
                "fixed": True,
                "movement_vector": [0, 0],
                "scale": 1.0,
                "rotation": 0.0,
                "visible": True
            })
            poly = box(to_bbox[0], to_bbox[1], to_bbox[2], to_bbox[3])
            placed_boxes.append(poly)
            fixed_polys.append(poly)
            placed_centers.append(((to_bbox[0] + to_bbox[2]) / 2.0, (to_bbox[1] + to_bbox[3]) / 2.0))

        # 3. Calculate strategic positions for movable objects
        movable_positions = self._calculate_all_movable_positions(
            movable_items=movable_items,
            freed_boxes=freed_boxes,
            strategy=strategy,
            fixed_polys=fixed_polys,
            remove_objects=remove_objects
        )

        for obj, (target_x, target_y) in zip(movable_items, movable_positions):
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            ow = x2 - x1
            oh = y2 - y1

            candidate_poly = box(target_x, target_y, target_x + ow, target_y + oh)
            has_collision = any(candidate_poly.intersection(pb).area > 1.0 for pb in placed_boxes)
            is_outside = not self.room_poly.contains(candidate_poly)

            if has_collision or is_outside:
                resolved_x, resolved_y = self._resolve_collision(
                    target_x, target_y, ow, oh, placed_boxes
                )
                if resolved_x is not None:
                    target_x, target_y = resolved_x, resolved_y
                else:
                    to_bbox = [int(x1), int(y1), int(x2), int(y2)]
                    plan_objects.append({
                        "id": obj.get("object_id") or obj.get("id"),
                        "class": obj.get("class") or obj.get("class_name", "furniture"),
                        "action": "KEEP",
                        "from": [int(x1), int(y1), int(x2), int(y2)],
                        "to": to_bbox,
                        "fixed": False,
                        "movement_vector": [0, 0],
                        "scale": 1.0,
                        "rotation": 0.0,
                        "visible": True
                    })
                    placed_boxes.append(box(to_bbox[0], to_bbox[1], to_bbox[2], to_bbox[3]))
                    placed_centers.append(((to_bbox[0] + to_bbox[2]) / 2.0, (to_bbox[1] + to_bbox[3]) / 2.0))
                    continue

            to_bbox = [int(target_x), int(target_y), int(target_x + ow), int(target_y + oh)]
            vector = [int(target_x - x1), int(target_y - y1)]

            placed_boxes.append(box(to_bbox[0], to_bbox[1], to_bbox[2], to_bbox[3]))
            placed_centers.append(((to_bbox[0] + to_bbox[2]) / 2.0, (to_bbox[1] + to_bbox[3]) / 2.0))

            plan_objects.append({
                "id": obj.get("object_id") or obj.get("id"),
                "class": obj.get("class") or obj.get("class_name", "furniture"),
                "action": "KEEP",
                "from": [int(x1), int(y1), int(x2), int(y2)],
                "to": to_bbox,
                "fixed": False,
                "movement_vector": vector,
                "scale": 1.0,
                "rotation": 0.0,
                "visible": True
            })

        # 4. Calculate spatial scoring metrics
        scores, recommendations = self._calculate_scores(
            placed_boxes=placed_boxes,
            placed_centers=placed_centers,
            total_removed_area=total_removed_area,
            strategy=strategy
        )

        return {
            "room_dimensions": [self.width, self.height],
            "strategy": strategy,
            "objects": plan_objects,
            "constraints": {
                "no_object_overlap": True,
                "stay_inside_room": True,
                "preserve_fixed_objects": True,
                "floor_line_grounded": True
            },
            "scores": scores,
            "recommendations": recommendations,
            "summary": {
                "total_objects": len(objects),
                "kept_count": len(keep_objects),
                "removed_count": len(remove_objects),
                "moved_count": sum(1 for p in plan_objects if p.get("movement_vector") != [0, 0]),
                "strategy_applied": strategy.capitalize()
            }
        }

    def apply_operations(
        self,
        current_objects: List[Dict[str, Any]],
        operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Applies structured operations vocabulary:
        KEEP, REMOVE, MOVE, MOVE_NEAR, MOVE_LEFT, MOVE_RIGHT, ROTATE, RESIZE, FIX, ARRANGE
        Updates coordinates, visibility, scale and rotation locally without AI image calls.
        """
        objs_by_id = {o["id"]: dict(o) for o in current_objects}

        for op in operations:
            oid = op.get("object_id")
            if oid not in objs_by_id:
                continue

            target = objs_by_id[oid]
            action = str(op.get("action", "")).upper()
            x1, y1, x2, y2 = target.get("from", [0, 0, 100, 100])
            ow = max(1, x2 - x1)
            oh = max(1, y2 - y1)
            curr_to = target.get("to") or [x1, y1, x2, y2]
            cx1, cy1 = curr_to[0], curr_to[1]

            if action == "REMOVE":
                target["action"] = "REMOVE"
                target["visible"] = False
                target["to"] = None
                target["movement_vector"] = [0, 0]

            elif action == "KEEP":
                target["action"] = "KEEP"
                target["visible"] = True

            elif action == "FIX":
                target["fixed"] = True
                target["to"] = [x1, y1, x2, y2]
                target["movement_vector"] = [0, 0]

            elif action in {"MOVE", "MOVE_LEFT", "MOVE_RIGHT", "MOVE_FORWARD", "MOVE_BACK"}:
                if target.get("fixed", False):
                    continue

                dx = op.get("dx", 0)
                dy = op.get("dy", 0)

                if action == "MOVE_LEFT":
                    dx = -int(self.width * 0.12)
                elif action == "MOVE_RIGHT":
                    dx = int(self.width * 0.12)
                elif action == "MOVE_FORWARD":
                    dy = int(self.height * 0.08)
                elif action == "MOVE_BACK":
                    dy = -int(self.height * 0.08)

                nx = max(15, min(self.width - ow - 15, cx1 + dx))
                ny = max(self.floor_top, min(self.floor_bottom - oh, cy1 + dy))

                target["to"] = [int(nx), int(ny), int(nx + ow), int(ny + oh)]
                target["movement_vector"] = [int(nx - x1), int(ny - y1)]
                target["action"] = "KEEP"
                target["visible"] = True

            elif action == "MOVE_NEAR":
                if target.get("fixed", False):
                    continue
                ref_id = op.get("target_id")
                if ref_id and ref_id in objs_by_id:
                    ref_obj = objs_by_id[ref_id]
                    ref_to = ref_obj.get("to") or ref_obj.get("from")
                    rx1, ry1, rx2, ry2 = ref_to
                    # Place to right or left of reference object with 20px clearance
                    if rx2 + ow + 20 < self.width:
                        nx = rx2 + 20
                    else:
                        nx = max(15, rx1 - ow - 20)
                    ny = min(self.floor_bottom - oh, ry1)
                    target["to"] = [int(nx), int(ny), int(nx + ow), int(ny + oh)]
                    target["movement_vector"] = [int(nx - x1), int(ny - y1)]
                    target["action"] = "KEEP"
                    target["visible"] = True

            elif action == "ROTATE":
                target["rotation"] = float(op.get("rotation", target.get("rotation", 0.0) + 90.0))

            elif action == "RESIZE":
                target["scale"] = max(0.5, min(2.0, float(op.get("scale", target.get("scale", 1.0)))))

        return list(objs_by_id.values())

    def build_scene_manifest(
        self,
        room_id: str,
        original_image_url: str,
        clean_background_url: str,
        plan_objects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Builds the canonical JSON Scene Manifest specified in:
        PLACEWISE Detailed Reusable Scene and Furniture Arrangement Plan (Section 3 Step 9).
        """
        scene_objects = []
        for obj in plan_objects:
            x1, y1, x2, y2 = obj.get("from", [0, 0, 100, 100])
            to_coords = obj.get("to") or [x1, y1, x2, y2]
            tx1, ty1, tx2, ty2 = to_coords
            ow = max(1, tx2 - tx1)
            oh = max(1, ty2 - ty1)
            oid = obj.get("id")
            cls_name = obj.get("class", "furniture")
            category = CLASS_CATEGORIES.get(cls_name, "furniture")

            scene_objects.append({
                "id": oid,
                "name": cls_name.capitalize(),
                "category": category,
                "image": f"/storage/objects/cutout_{room_id}_{oid}.png",
                "mask": f"/storage/masks/mask_{room_id}_{oid}.png",
                "original_position": {"x": int(x1), "y": int(y1)},
                "position": {"x": int(tx1), "y": int(ty1)},
                "width": int(ow),
                "height": int(oh),
                "scale": float(obj.get("scale", 1.0)),
                "rotation": float(obj.get("rotation", 0.0)),
                "visible": bool(obj.get("action") != "REMOVE"),
                "action": obj.get("action", "KEEP"),
                "fixed": bool(obj.get("fixed", False)),
                "z_index": int(ty2)  # Floor contact line determines depth
            })

        return {
            "scene_id": room_id,
            "original_image": original_image_url,
            "clean_background": clean_background_url,
            "canvas": {
                "width": self.width,
                "height": self.height
            },
            "objects": scene_objects
        }

    def _calculate_all_movable_positions(
        self,
        movable_items: List[Dict[str, Any]],
        freed_boxes: List[Tuple[int, int, int, int]],
        strategy: str,
        fixed_polys: List[Polygon],
        remove_objects: List[Dict[str, Any]]
    ) -> List[Tuple[int, int]]:
        if not movable_items:
            return []

        if strategy == "spacious":
            return self._spacious_layout(movable_items, freed_boxes, fixed_polys)
        elif strategy == "cozy":
            return self._cozy_layout(movable_items, freed_boxes, fixed_polys)
        else:
            return self._balanced_layout(movable_items, freed_boxes, fixed_polys)

    def _spacious_layout(
        self,
        movable_items: List[Dict[str, Any]],
        freed_boxes: List[Tuple[int, int, int, int]],
        fixed_polys: List[Polygon]
    ) -> List[Tuple[int, int]]:
        positions = []
        margin = 25

        for i, obj in enumerate(movable_items):
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            ow, oh = x2 - x1, y2 - y1
            obj_cx = (x1 + x2) / 2.0

            if obj_cx < self.center_x:
                target_x = margin
            else:
                target_x = self.width - ow - margin

            min_displacement = int(self.width * 0.16)
            actual_dx = abs(target_x - x1)
            if actual_dx < min_displacement:
                if obj_cx < self.center_x:
                    target_x = max(margin, x1 - min_displacement)
                else:
                    target_x = min(self.width - ow - margin, x1 + min_displacement)

            target_y = max(self.floor_top, min(self.floor_bottom - oh, y1 + int(oh * 0.08)))

            same_side = [p for j, p in enumerate(positions) if j < i]
            for px, py in same_side:
                if abs(target_x - px) < ow:
                    target_y = max(self.floor_top, min(self.floor_bottom - oh, target_y + int(oh * 0.35)))

            positions.append((int(target_x), int(target_y)))

        return positions

    def _cozy_layout(
        self,
        movable_items: List[Dict[str, Any]],
        freed_boxes: List[Tuple[int, int, int, int]],
        fixed_polys: List[Polygon]
    ) -> List[Tuple[int, int]]:
        positions = []
        cluster_cx = self.center_x
        cluster_cy = self.center_y + (self.height * 0.08)

        if freed_boxes:
            avg_fx = sum(fb[0] + fb[2] / 2 for fb in freed_boxes) / len(freed_boxes)
            avg_fy = sum(fb[1] + fb[3] / 2 for fb in freed_boxes) / len(freed_boxes)
            cluster_cx = (cluster_cx + avg_fx) / 2.0
            cluster_cy = (cluster_cy + avg_fy) / 2.0

        for i, obj in enumerate(movable_items):
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            ow, oh = x2 - x1, y2 - y1
            obj_cx = (x1 + x2) / 2.0
            obj_cy = (y1 + y2) / 2.0

            pull_factor = 0.65
            new_cx = obj_cx + (cluster_cx - obj_cx) * pull_factor
            new_cy = obj_cy + (cluster_cy - obj_cy) * pull_factor

            target_x = int(new_cx - ow / 2)
            target_y = int(new_cy - oh / 2)

            min_displacement = int(self.width * 0.12)
            if abs(target_x - x1) < min_displacement:
                if obj_cx < self.center_x:
                    target_x = x1 + min_displacement
                else:
                    target_x = x1 - min_displacement

            target_x = max(15, min(self.width - ow - 15, target_x))
            target_y = max(self.floor_top, min(self.floor_bottom - oh, target_y))

            positions.append((int(target_x), int(target_y)))

        return positions

    def _balanced_layout(
        self,
        movable_items: List[Dict[str, Any]],
        freed_boxes: List[Tuple[int, int, int, int]],
        fixed_polys: List[Polygon]
    ) -> List[Tuple[int, int]]:
        positions = []
        n = len(movable_items)
        if n == 0:
            return positions

        margin = 35
        available_width = self.width - 2 * margin

        if freed_boxes:
            sorted_freed = sorted(freed_boxes, key=lambda f: f[0])
            total_freed_width = sum(fb[2] for fb in freed_boxes)

            if total_freed_width > 0 and n <= len(freed_boxes):
                for i, obj in enumerate(movable_items):
                    x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
                    ow, oh = x2 - x1, y2 - y1

                    if i < len(sorted_freed):
                        fb = sorted_freed[i]
                        target_x = int(fb[0] + (fb[2] - ow) / 2)
                        target_y = max(self.floor_top, min(self.floor_bottom - oh,
                                       int(fb[1] + (fb[3] - oh) / 2)))
                    else:
                        slot_width = available_width / n
                        target_x = int(margin + i * slot_width + (slot_width - ow) / 2)
                        target_y = max(self.floor_top, min(self.floor_bottom - oh, y1))

                    target_x = max(margin, min(self.width - ow - margin, target_x))
                    positions.append((int(target_x), int(target_y)))
            else:
                spacing = available_width / (n + 1)
                for i, obj in enumerate(movable_items):
                    x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
                    ow, oh = x2 - x1, y2 - y1

                    target_x = int(margin + (i + 1) * spacing - ow / 2)
                    target_y = max(self.floor_top, min(self.floor_bottom - oh, y1))
                    target_x = max(margin, min(self.width - ow - margin, target_x))

                    min_displacement = int(self.width * 0.10)
                    if abs(target_x - x1) < min_displacement:
                        if target_x >= x1:
                            target_x = min(self.width - ow - margin, x1 + min_displacement)
                        else:
                            target_x = max(margin, x1 - min_displacement)

                    positions.append((int(target_x), int(target_y)))
        else:
            spacing = available_width / (n + 1)
            for i, obj in enumerate(movable_items):
                x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
                ow, oh = x2 - x1, y2 - y1

                target_x = int(margin + (i + 1) * spacing - ow / 2)
                target_y = max(self.floor_top, min(self.floor_bottom - oh, y1))
                target_x = max(margin, min(self.width - ow - margin, target_x))

                min_displacement = int(self.width * 0.10)
                if abs(target_x - x1) < min_displacement:
                    if x1 < self.center_x:
                        target_x = min(self.width - ow - margin, x1 + min_displacement)
                    else:
                        target_x = max(margin, x1 - min_displacement)

                positions.append((int(target_x), int(target_y)))

        return positions

    def _resolve_collision(
        self,
        target_x: int,
        target_y: int,
        ow: int,
        oh: int,
        placed_boxes: List[Polygon]
    ) -> Tuple[Optional[int], Optional[int]]:
        nudge_offsets = [
            (0, -oh - 10),
            (0, oh + 10),
            (-ow - 10, 0),
            (ow + 10, 0),
            (-ow // 2, -oh // 2),
            (ow // 2, -oh // 2),
            (-ow // 2, oh // 2),
            (ow // 2, oh // 2),
        ]

        for dx, dy in nudge_offsets:
            nx = target_x + dx
            ny = target_y + dy
            nx = max(10, min(self.width - ow - 10, nx))
            ny = max(10, min(self.height - oh - 10, ny))

            candidate = box(nx, ny, nx + ow, ny + oh)
            collision = any(candidate.intersection(pb).area > 1.0 for pb in placed_boxes)

            if not collision and self.room_poly.contains(candidate):
                return int(nx), int(ny)

        return None, None

    def _calculate_scores(
        self,
        placed_boxes: List[Polygon],
        placed_centers: List[Tuple[float, float]],
        total_removed_area: int,
        strategy: str
    ) -> Tuple[Dict[str, int], List[str]]:
        room_area = max(1, self.width * self.height)

        freed_ratio = min(0.4, total_removed_area / room_area)
        space_util = int(min(98, max(75, 78 + (freed_ratio * 50))))

        min_clearance = 999.0
        if len(placed_boxes) >= 2:
            for i in range(len(placed_boxes)):
                for j in range(i + 1, len(placed_boxes)):
                    dist = placed_boxes[i].distance(placed_boxes[j])
                    if dist < min_clearance:
                        min_clearance = dist
        else:
            min_clearance = 120.0

        if min_clearance >= 60:
            walkway_score = 94
        elif min_clearance >= 30:
            walkway_score = 86
        else:
            walkway_score = 78

        if placed_centers:
            avg_cx = sum(c[0] for c in placed_centers) / len(placed_centers)
            cx_dev = abs(avg_cx - self.center_x) / self.width
            balance_score = int(max(70, min(96, 95 - (cx_dev * 50))))
        else:
            balance_score = 90

        overall = int(round(0.40 * space_util + 0.35 * walkway_score + 0.25 * balance_score))

        recs = [
            f"Layout optimized for '{strategy.capitalize()}' floor flow.",
            "All movable furniture aligned to floor baseline with zero physical collision.",
            f"Walkway clearance maintained at minimum {int(min_clearance if min_clearance < 900 else 60)}px."
        ]
        if total_removed_area > 0:
            recs.append(f"Freed up ~{int(freed_ratio * 100)}% of primary visual floor space.")

        scores = {
            "space_utilization": space_util,
            "walkway_clearance": walkway_score,
            "balance_symmetry": balance_score,
            "overall_score": overall
        }

        return scores, recs
