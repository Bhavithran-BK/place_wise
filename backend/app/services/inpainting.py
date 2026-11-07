import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

class PlanAndImageRenderer:
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.results_dir = storage_dir / "results"
        self.masks_dir = storage_dir / "masks"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def render_both_outputs(
        self,
        original_image_path: str,
        plan_data: Dict[str, Any],
        room_id: str
    ) -> Dict[str, str]:
        """
        Generates both coordinated outputs from the canonical arrangement plan:
        1. Annotated Arrangement Plan image (outlines, labels, movement arrows)
        2. Visual Rearranged / Inpainted Photograph
        """
        orig_img = cv2.imread(original_image_path)
        if orig_img is None:
            raise FileNotFoundError(f"Could not read image at {original_image_path}")

        h, w = orig_img.shape[:2]

        # ── 1. GENERATE ANNOTATED ARRANGEMENT PLAN ──
        plan_img = orig_img.copy()

        for obj in plan_data.get("objects", []):
            x1, y1, x2, y2 = obj["from"]
            action = obj["action"]
            obj_id = obj["id"]
            to_coords = obj.get("to")
            vector = obj.get("movement_vector", [0, 0])

            if action == "REMOVE":
                # Red dashed overlay with cross
                overlay = plan_img.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (40, 40, 220), -1)
                cv2.addWeighted(overlay, 0.25, plan_img, 0.75, 0, plan_img)
                cv2.rectangle(plan_img, (x1, y1), (x2, y2), (50, 50, 240), 2)
                # Strike-through cross
                cv2.line(plan_img, (x1, y1), (x2, y2), (50, 50, 240), 2)
                cv2.line(plan_img, (x1, y2), (x2, y1), (50, 50, 240), 2)
                # Label
                cv2.putText(plan_img, f"{obj_id} [REMOVE]", (x1 + 6, y1 + 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
            else:
                # KEEP object — green outline
                cv2.rectangle(plan_img, (x1, y1), (x2, y2), (50, 200, 80), 2)
                cv2.putText(plan_img, f"{obj_id} [KEEP]", (x1 + 6, y1 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

                # If moved, draw destination outline & arrow
                if vector != [0, 0] and to_coords:
                    tx1, ty1, tx2, ty2 = to_coords
                    # Cyan dashed destination
                    cv2.rectangle(plan_img, (tx1, ty1), (tx2, ty2), (230, 180, 50), 2)
                    # Movement arrow from center of original to center of destination
                    cx1, cy1 = (x1 + x2) // 2, (y1 + y2) // 2
                    cx2, cy2 = (tx1 + tx2) // 2, (ty1 + ty2) // 2
                    cv2.arrowedLine(plan_img, (cx1, cy1), (cx2, cy2), (255, 220, 0), 3, tipLength=0.25)
                    cv2.putText(plan_img, "Proposed Position", (tx1 + 6, ty1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 220, 0), 2, cv2.LINE_AA)

        plan_filename = f"plan_{room_id}.jpg"
        plan_dest = self.results_dir / plan_filename
        cv2.imwrite(str(plan_dest), plan_img)

        # ── 2. GENERATE REARRANGED / INPAINTED PHOTOGRAPH ──
        edited_img = orig_img.copy()

        # Inpaint removed objects
        remove_mask = np.zeros((h, w), dtype=np.uint8)
        for obj in plan_data.get("objects", []):
            if obj["action"] == "REMOVE":
                x1, y1, x2, y2 = obj["from"]
                # Try loading exact mask if available
                mask_file = self.masks_dir / f"mask_{room_id}_{obj['id']}.png"
                if mask_file.exists():
                    m = cv2.imread(str(mask_file), cv2.IMREAD_GRAYSCALE)
                    if m is not None and m.shape == (h, w):
                        remove_mask = cv2.bitwise_or(remove_mask, m)
                    else:
                        remove_mask[y1:y2, x1:x2] = 255
                else:
                    remove_mask[y1:y2, x1:x2] = 255

        if np.count_nonzero(remove_mask) > 0:
            # Dilate mask slightly to prevent seam artifacts
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated_mask = cv2.dilate(remove_mask, kernel, iterations=2)
            # Inpainting with Telea algorithm
            edited_img = cv2.inpaint(edited_img, dilated_mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)

        # Reposition moved objects onto cleaned background
        for obj in plan_data.get("objects", []):
            if obj["action"] == "KEEP" and obj.get("movement_vector", [0, 0]) != [0, 0]:
                x1, y1, x2, y2 = obj["from"]
                tx1, ty1, tx2, ty2 = obj["to"]
                ow, oh = x2 - x1, y2 - y1
                tw, th = tx2 - tx1, ty2 - ty1

                cutout_file = self.masks_dir / f"cutout_{room_id}_{obj['id']}.png"
                if cutout_file.exists():
                    cutout = cv2.imread(str(cutout_file), cv2.IMREAD_UNCHANGED)
                    if cutout is not None:
                        # Resize cutout if needed to fit destination
                        if (ow, oh) != (tw, th):
                            cutout = cv2.resize(cutout, (tw, th), interpolation=cv2.INTER_AREA)

                        # Overlay cutout onto destination with alpha blending
                        if cutout.shape[2] == 4:
                            alpha = cutout[:, :, 3] / 255.0
                            rgb = cutout[:, :, :3]
                            for c in range(3):
                                edited_img[ty1:ty2, tx1:tx2, c] = (
                                    alpha * rgb[:, :, c] +
                                    (1 - alpha) * edited_img[ty1:ty2, tx1:tx2, c]
                                )

        rearranged_filename = f"rearranged_{room_id}.jpg"
        rearranged_dest = self.results_dir / rearranged_filename
        cv2.imwrite(str(rearranged_dest), edited_img)

        return {
            "plan_image_url": f"/storage/results/{plan_filename}",
            "rearranged_image_url": f"/storage/results/{rearranged_filename}"
        }

