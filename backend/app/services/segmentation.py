import os
from pathlib import Path
from typing import List, Tuple
import numpy as np
import cv2
from PIL import Image

class ObjectSegmenter:
    """
    Produces segmentation masks for detected bounding boxes.
    Uses GrabCut foreground extraction with morphological refinement
    to isolate objects cleanly from walls/floors.
    """

    def __init__(self, masks_dir: Path):
        self.masks_dir = masks_dir
        self.masks_dir.mkdir(parents=True, exist_ok=True)

    def generate_mask(self, image_path: str, bbox: List[int], object_id: str) -> str:
        """
        Generates an 8-bit binary mask (255=foreground, 0=background)
        and an RGBA cut-out of the object.
        bbox format: [x1, y1, x2, y2]
        Returns relative mask filename.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")

        h, w = img.shape[:2]
        x1, y1, x2, y2 = bbox

        # Clamp bounds
        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        box_w = x2 - x1
        box_h = y2 - y1

        mask_filename = f"mask_{object_id}.png"
        mask_out_path = self.masks_dir / mask_filename

        # If bounding box is valid for GrabCut
        if box_w > 10 and box_h > 10:
            try:
                # GrabCut initialization
                gc_mask = np.zeros((h, w), np.uint8)
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)

                rect = (x1, y1, box_w, box_h)
                # 3 iterations for fast, clean contour extraction
                cv2.grabCut(img, gc_mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)

                # Foreground is where mask is 1 (FGD) or 3 (PR_FGD)
                bin_mask = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype('uint8')

                # Morphological smoothing to avoid jagged edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
                bin_mask = cv2.GaussianBlur(bin_mask, (3, 3), 0)
                _, bin_mask = cv2.threshold(bin_mask, 127, 255, cv2.THRESH_BINARY)
            except Exception as e:
                # Fallback to rectangular mask with softened edges
                bin_mask = np.zeros((h, w), dtype=np.uint8)
                bin_mask[y1:y2, x1:x2] = 255
        else:
            bin_mask = np.zeros((h, w), dtype=np.uint8)
            bin_mask[y1:y2, x1:x2] = 255

        # Save binary mask
        cv2.imwrite(str(mask_out_path), bin_mask)

        # Also generate RGBA cutout for visual compositing
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = bin_mask
        cutout_filename = f"cutout_{object_id}.png"
        cv2.imwrite(str(self.masks_dir / cutout_filename), rgba[y1:y2, x1:x2])

        return mask_filename

