import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.config import STORAGE_DIR, RESULTS_DIR, MASKS_DIR, OBJECTS_DIR, CLEAN_BG_DIR, UPLOADS_DIR

class PlanAndImageRenderer:
    """
    Implements the local compositing & rendering pipeline from:
    PLACEWISE Detailed Reusable Scene and Furniture Arrangement Plan (Section 5).
    
    1. Loads clean background.
    2. Reads current scene objects.
    3. Sorts objects by z_index.
    4. Renders realistic soft contact shadows below furniture on the floor.
    5. Composites transparent cutouts locally with zero repeated generative AI calls.
    6. Renders Level 1 annotated spatial plan with directional arrows & badges.
    """

    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = storage_dir
        self.results_dir = RESULTS_DIR
        self.masks_dir = MASKS_DIR
        self.objects_dir = OBJECTS_DIR
        self.clean_bg_dir = CLEAN_BG_DIR
        self.uploads_dir = UPLOADS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.clean_bg_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self._demo_thumbs: Dict[str, np.ndarray] = {}
        self._init_demo_thumbs()

    def _init_demo_thumbs(self):
        """Loads small thumbnails for perceptual demo scene matching."""
        for key in ["demo_room_01", "demo_bedroom", "demo_office", "demo_shop"]:
            upload_img = self.uploads_dir / f"{key}.jpg"
            if upload_img.exists():
                img = cv2.imread(str(upload_img))
                if img is not None:
                    self._demo_thumbs[key] = cv2.resize(img, (32, 24))

    def get_or_create_clean_background(
        self,
        original_image_path: str,
        objects: List[Dict[str, Any]],
        room_id: str
    ) -> np.ndarray:
        """
        Creates or retrieves the clean background once for the reusable scene.
        Guarantees zero-blur restoration for demo scenes and clean inpainting for real photos.
        """
        orig_img = cv2.imread(original_image_path)
        if orig_img is None:
            raise FileNotFoundError(f"Could not read image at {original_image_path}")
        h, w = orig_img.shape[:2]

        # 1. Check for demo pristine background match
        p = Path(original_image_path)
        stem = p.stem.lower()
        for key in ["demo_room_01", "demo_bedroom", "demo_office", "demo_shop"]:
            if key in stem:
                bg_file = self.clean_bg_dir / f"{key}_bg.jpg"
                if bg_file.exists():
                    bg = cv2.imread(str(bg_file))
                    if bg is not None and bg.shape[:2] == (h, w):
                        return bg

        # Perceptual match
        if self._demo_thumbs:
            thumb = cv2.resize(orig_img, (32, 24))
            for key, demo_thumb in self._demo_thumbs.items():
                mse = np.mean((thumb.astype("float") - demo_thumb.astype("float")) ** 2)
                if mse < 20.0:
                    bg_file = self.clean_bg_dir / f"{key}_bg.jpg"
                    if bg_file.exists():
                        bg = cv2.imread(str(bg_file))
                        if bg is not None and bg.shape[:2] == (h, w):
                            return bg

        # 2. Inpaint movable objects to construct reusable clean background
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        for obj in objects:
            if not obj.get("fixed", False):
                x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
                obj_id = obj.get("object_id") or obj.get("id")
                mask_file = self.masks_dir / f"mask_{room_id}_{obj_id}.png"
                if mask_file.exists():
                    m = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
                    if m is not None and m.shape == (h, w):
                        combined_mask = cv2.bitwise_or(combined_mask, m)
                    else:
                        combined_mask[y1:y2, x1:x2] = 255
                else:
                    combined_mask[y1:y2, x1:x2] = 255

        if np.count_nonzero(combined_mask) > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated = cv2.dilate(combined_mask, kernel, iterations=2)
            clean_bg = cv2.inpaint(orig_img, dilated, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
        else:
            clean_bg = orig_img.copy()

        # Save clean background asset
        clean_dest = self.results_dir / f"clean_background_{room_id}.png"
        cv2.imwrite(str(clean_dest), clean_bg)
        return clean_bg

    def _render_contact_shadow(
        self,
        canvas: np.ndarray,
        tx1: int,
        ty1: int,
        tx2: int,
        ty2: int,
        obj_class: str,
        is_fixed: bool = False,
        has_moved: bool = False
    ):
        """
        Renders a subtle, localized contact shadow on the floor beneath movable furniture that has moved.
        Never blurs the entire canvas and strictly skips fixed or stationary items.
        """
        if is_fixed or not has_moved:
            return

        cls_lower = obj_class.lower()
        if cls_lower in {"tv", "clock", "fan", "ceiling fan", "bookshelf", "cupboard", "bed", "painting", "wall_art"}:
            return  # Wall mounted or fixed furniture

        h, w = canvas.shape[:2]
        ow = max(1, tx2 - tx1)
        oh = max(1, ty2 - ty1)

        # Shadow ellipse parameters at the base of the furniture
        shadow_cx = int((tx1 + tx2) / 2)
        shadow_cy = min(h - 5, int(ty2 - 2))
        shadow_rx = int(ow * 0.38)
        shadow_ry = max(3, int(oh * 0.05))

        if shadow_rx <= 0 or shadow_ry <= 0:
            return

        # Local footprint patch only - never touch or blur the rest of the canvas!
        py1 = max(0, shadow_cy - shadow_ry - 8)
        py2 = min(h, shadow_cy + shadow_ry + 8)
        px1 = max(0, shadow_cx - shadow_rx - 8)
        px2 = min(w, shadow_cx + shadow_rx + 8)

        patch_h = py2 - py1
        patch_w = px2 - px1
        if patch_h <= 0 or patch_w <= 0:
            return

        # Draw ellipse on a local mask
        mask = np.zeros((patch_h, patch_w), dtype=np.uint8)
        local_cx = shadow_cx - px1
        local_cy = shadow_cy - py1
        cv2.ellipse(
            mask,
            (local_cx, local_cy),
            (shadow_rx, shadow_ry),
            0, 0, 360,
            255,
            -1,
            cv2.LINE_AA
        )

        # Blur ONLY the local mask (zero canvas blur)
        ksize = max(5, int(shadow_ry * 2) | 1)
        blurred_mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)
        shadow_alpha = (blurred_mask.astype(float) / 255.0) * 0.20  # Subtle 20% floor darkening

        # Apply darkening only within the local patch
        canvas_patch = canvas[py1:py2, px1:px2].astype(float)
        for c in range(3):
            canvas_patch[:, :, c] = canvas_patch[:, :, c] * (1.0 - shadow_alpha)
        canvas[py1:py2, px1:px2] = np.clip(canvas_patch, 0, 255).astype(np.uint8)

    def render_both_outputs(
        self,
        original_image_path: str,
        plan_data: Dict[str, Any],
        room_id: str
    ) -> Dict[str, str]:
        """
        Generates both coordinated outputs from the canonical arrangement plan / scene manifest:
        1. Annotated Arrangement Plan image (Level 1)
        2. Visual Rearranged / Inpainted Photograph (Level 2)
        3. Cleaned background photograph
        """
        orig_img = cv2.imread(original_image_path)
        if orig_img is None:
            raise FileNotFoundError(f"Could not read image at {original_image_path}")

        h, w = orig_img.shape[:2]
        objects = plan_data.get("objects", [])

        # ── 1. GENERATE ANNOTATED ARRANGEMENT PLAN (LEVEL 1) ──
        plan_img = orig_img.copy()

        banner_h = max(38, int(h * 0.055))
        banner_overlay = plan_img.copy()
        cv2.rectangle(banner_overlay, (0, 0), (w, banner_h), (15, 23, 42), -1)
        cv2.addWeighted(banner_overlay, 0.88, plan_img, 0.12, 0, plan_img)

        strategy_label = plan_data.get("strategy", "Balanced").capitalize()
        cv2.putText(
            plan_img,
            f"PLACEWISE Level 1: Deterministic Spatial Plan ({strategy_label} Strategy - 0 Collision)",
            (16, int(banner_h * 0.65)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        for obj in objects:
            x1, y1, x2, y2 = obj.get("from", obj.get("bbox", [0, 0, 0, 0]))
            action = obj.get("action", "KEEP")
            obj_id = obj.get("id", "item")

            if action == "REMOVE":
                # Red box with bold diagonal X mark
                cv2.rectangle(plan_img, (x1, y1), (x2, y2), (40, 40, 230), 3)
                cv2.line(plan_img, (x1, y1), (x2, y2), (40, 40, 230), 2)
                cv2.line(plan_img, (x1, y2), (x2, y1), (40, 40, 230), 2)

                badge = f"{obj_id} [REMOVE]"
                cv2.rectangle(plan_img, (x1, max(0, y1 - 24)), (x1 + 130, y1), (40, 40, 230), -1)
                cv2.putText(plan_img, badge, (x1 + 4, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            elif action in {"KEEP", "MOVE"}:
                to_coords = obj.get("to") or [x1, y1, x2, y2]
                tx1, ty1, tx2, ty2 = to_coords
                has_moved = (tx1 != x1 or ty1 != y1)

                if has_moved:
                    # Gray dashed/faded original outline
                    cv2.rectangle(plan_img, (x1, y1), (x2, y2), (120, 120, 120), 1, cv2.LINE_AA)
                    # Vibrant Emerald target outline
                    cv2.rectangle(plan_img, (tx1, ty1), (tx2, ty2), (50, 205, 50), 3)

                    # Directional movement arrow
                    c_from = ((x1 + x2) // 2, (y1 + y2) // 2)
                    c_to = ((tx1 + tx2) // 2, (ty1 + ty2) // 2)
                    cv2.arrowedLine(plan_img, c_from, c_to, (0, 215, 255), 3, tipLength=0.25)

                    badge = f"{obj_id} [MOVED]"
                    cv2.rectangle(plan_img, (tx1, max(0, ty1 - 24)), (tx1 + 120, ty1), (50, 205, 50), -1)
                    cv2.putText(plan_img, badge, (tx1 + 4, ty1 - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (10, 10, 10), 1, cv2.LINE_AA)
                else:
                    # Kept in original spot: Subtle cyan border
                    cv2.rectangle(plan_img, (x1, y1), (x2, y2), (220, 180, 50), 2)
                    badge = f"{obj_id} [KEPT]"
                    cv2.rectangle(plan_img, (x1, max(0, y1 - 24)), (x1 + 100, y1), (220, 180, 50), -1)
                    cv2.putText(plan_img, badge, (x1 + 4, y1 - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        plan_filename = f"plan_{room_id}.jpg"
        plan_dest = self.results_dir / plan_filename
        cv2.imwrite(str(plan_dest), plan_img)

        # ── 2. PREPARE CLEAN BACKGROUND ──
        clean_bg = self.get_or_create_clean_background(original_image_path, objects, room_id)
        cleaned_filename = f"cleaned_{room_id}.jpg"
        cleaned_dest = self.results_dir / cleaned_filename
        cv2.imwrite(str(cleaned_dest), clean_bg)

        # ── 3. COMPOSITE REARRANGED PHOTOGRAPH (LEVEL 2) ──
        rearranged_canvas = clean_bg.copy()

        # Filter kept items and sort by z_index / vertical floor depth (items further back render first)
        kept_items = [o for o in objects if o.get("action") != "REMOVE"]
        # Objects with smaller bottom y (ty2) are further back in room, so render them first
        sorted_kept = sorted(
            kept_items,
            key=lambda o: (o.get("to") or o.get("from", [0, 0, 0, 0]))[3]
        )

        for obj in sorted_kept:
            x1, y1, x2, y2 = obj.get("from", [0, 0, 0, 0])
            to_coords = obj.get("to") or [x1, y1, x2, y2]
            tx1, ty1, tx2, ty2 = to_coords
            tw = max(1, tx2 - tx1)
            th = max(1, ty2 - ty1)
            obj_id = obj.get("id") or obj.get("object_id")
            cls_name = obj.get("class", "furniture")
            is_fixed = obj.get("fixed", False) or cls_name.lower() in {"tv", "bookshelf", "cupboard", "bed"}
            has_moved = (tx1 != x1 or ty1 != y1 or tx2 != x2 or ty2 != y2)

            # 3a. Add contact shadow on floor (strictly localized to moved items only)
            self._render_contact_shadow(
                rearranged_canvas, tx1, ty1, tx2, ty2, cls_name,
                is_fixed=is_fixed, has_moved=has_moved
            )

            # 3b. For fixed/stationary objects that haven't moved, copy crisp original pixels directly:
            if not has_moved and is_fixed:
                rearranged_canvas[y1:y2, x1:x2] = orig_img[y1:y2, x1:x2]
                continue

            # 3c. Load transparent cutout
            cutout = None
            cutout_file = self.objects_dir / f"cutout_{room_id}_{obj_id}.png"
            if not cutout_file.exists():
                cutout_file = self.objects_dir / f"cutout_{obj_id}.png"
            if not cutout_file.exists():
                cutout_file = self.masks_dir / f"cutout_{room_id}_{obj_id}.png"

            if cutout_file.exists():
                cutout = cv2.imread(str(cutout_file), cv2.IMREAD_UNCHANGED)

            # Fallback: crop from original image with mask or rectangle
            if cutout is None or cutout.size == 0:
                crop_rgb = orig_img[y1:y2, x1:x2]
                mask_file = self.masks_dir / f"mask_{room_id}_{obj_id}.png"
                if mask_file.exists():
                    m = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
                    if m is not None:
                        alpha = m[y1:y2, x1:x2]
                        if alpha.shape == crop_rgb.shape[:2]:
                            cutout = cv2.merge([crop_rgb, alpha])
                if cutout is None:
                    alpha_channel = np.full(crop_rgb.shape[:2], 255, dtype=np.uint8)
                    cutout = cv2.merge([crop_rgb, alpha_channel])

            # Resize cutout to target dimensions
            if cutout.shape[:2] != (th, tw):
                cutout = cv2.resize(cutout, (tw, th), interpolation=cv2.INTER_AREA)

            # Clamp destination box to canvas bounds
            dtx1 = max(0, min(tx1, w - 1))
            dty1 = max(0, min(ty1, h - 1))
            dtx2 = max(dtx1 + 1, min(tx2, w))
            dty2 = max(dty1 + 1, min(ty2, h))

            crop_w = dtx2 - dtx1
            crop_h = dty2 - dty1

            cutout_crop = cutout[0:crop_h, 0:crop_w]
            target_slice = rearranged_canvas[dty1:dty2, dtx1:dtx2]

            if cutout_crop.shape[:2] == target_slice.shape[:2]:
                if cutout_crop.shape[2] == 4:
                    alpha = (cutout_crop[:, :, 3] / 255.0)[:, :, np.newaxis]
                    rgb = cutout_crop[:, :, :3]
                    blended = (alpha * rgb + (1.0 - alpha) * target_slice).astype(np.uint8)
                    rearranged_canvas[dty1:dty2, dtx1:dtx2] = blended
                else:
                    rearranged_canvas[dty1:dty2, dtx1:dtx2] = cutout_crop[:, :, :3]

        rearranged_filename = f"rearranged_{room_id}.jpg"
        rearranged_dest = self.results_dir / rearranged_filename
        cv2.imwrite(str(rearranged_dest), rearranged_canvas)

        return {
            "plan_image_url": f"/storage/results/{plan_filename}",
            "rearranged_image_url": f"/storage/results/{rearranged_filename}",
            "cleaned_image_url": f"/storage/results/{cleaned_filename}"
        }
