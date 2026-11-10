import os
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import cv2
from PIL import Image
from app.core.config import MASKS_DIR, OBJECTS_DIR

class ObjectSegmenter:
    """
    Produces pixel-level binary masks and transparent RGBA cutouts
    for detected furniture instances as required by PLACEWISE.
    """

    def __init__(self, masks_dir: Path = MASKS_DIR, objects_dir: Path = OBJECTS_DIR):
        self.masks_dir = masks_dir
        self.objects_dir = objects_dir
        self.masks_dir.mkdir(parents=True, exist_ok=True)
        self.objects_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_yolo_mask(
        self,
        image_path: str,
        yolo_mask: np.ndarray,
        bbox: List[int],
        object_id: str
    ) -> Tuple[str, str]:
        """
        Creates binary mask and transparent cutout directly from YOLOv8-seg prediction.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")
        h, w = img.shape[:2]

        # Resize mask to original image dimensions with nearest neighbor
        if yolo_mask.shape[:2] != (h, w):
            resized_mask = cv2.resize(yolo_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            resized_mask = yolo_mask

        # Threshold to binary (0 or 255)
        bin_mask = (resized_mask > 0.5).astype(np.uint8) * 255

        # Restrict mask inside bounding box + small padding
        x1, y1, x2, y2 = bbox
        box_mask = np.zeros((h, w), dtype=np.uint8)
        pad = 8
        bx1 = max(0, x1 - pad)
        by1 = max(0, y1 - pad)
        bx2 = min(w, x2 + pad)
        by2 = min(h, y2 + pad)
        box_mask[by1:by2, bx1:bx2] = 255
        bin_mask = cv2.bitwise_and(bin_mask, box_mask)

        # Smooth edges slightly to avoid aliased jagged boundaries
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)

        mask_filename = f"mask_{object_id}.png"
        mask_path = self.masks_dir / mask_filename
        cv2.imwrite(str(mask_path), bin_mask)

        # Generate transparent RGBA cutout
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = bin_mask
        cutout_filename = f"cutout_{object_id}.png"
        cutout_path = self.objects_dir / cutout_filename

        # Crop tightly to bbox
        cx1 = max(0, min(x1, w - 1))
        cy1 = max(0, min(y1, h - 1))
        cx2 = max(cx1 + 1, min(x2, w))
        cy2 = max(cy1 + 1, min(y2, h))
        cv2.imwrite(str(cutout_path), rgba[cy1:cy2, cx1:cx2])

        return mask_filename, cutout_filename

    def generate_from_background_subtraction(
        self,
        image_path: str,
        pristine_bg: np.ndarray,
        bbox: List[int],
        object_id: str
    ) -> Tuple[str, str]:
        """
        Creates razor-sharp zero-blur masks and cutouts for benchmark demo scenes
        by precise pixel difference against known clean background.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")
        h, w = img.shape[:2]
        x1, y1, x2, y2 = bbox

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        # Difference against pristine background
        crop_img = img[y1:y2, x1:x2]
        crop_bg = pristine_bg[y1:y2, x1:x2]
        diff = np.max(np.abs(crop_img.astype(int) - crop_bg.astype(int)), axis=2)
        local_mask = (diff > 16).astype(np.uint8) * 255

        # Morphological close to ensure solid interior
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_CLOSE, kernel)

        # Full room binary mask
        bin_mask = np.zeros((h, w), dtype=np.uint8)
        bin_mask[y1:y2, x1:x2] = local_mask

        mask_filename = f"mask_{object_id}.png"
        mask_path = self.masks_dir / mask_filename
        cv2.imwrite(str(mask_path), bin_mask)

        # Transparent RGBA cutout
        rgba_crop = cv2.cvtColor(crop_img, cv2.COLOR_BGR2BGRA)
        rgba_crop[:, :, 3] = local_mask

        cutout_filename = f"cutout_{object_id}.png"
        cutout_path = self.objects_dir / cutout_filename
        cv2.imwrite(str(cutout_path), rgba_crop)

        return mask_filename, cutout_filename

    def generate_mask(
        self,
        image_path: str,
        bbox: List[int],
        object_id: str
    ) -> str:
        """
        Fallback GrabCut / morphological segmentation for bounding boxes.
        Returns relative mask filename.
        """
        mask_fn, _ = self.generate_mask_and_cutout(image_path, bbox, object_id)
        return mask_fn

    def generate_mask_and_cutout(
        self,
        image_path: str,
        bbox: List[int],
        object_id: str
    ) -> Tuple[str, str]:
        """
        Generates binary mask and transparent RGBA cutout using GrabCut.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")

        h, w = img.shape[:2]
        x1, y1, x2, y2 = bbox

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))

        box_w = x2 - x1
        box_h = y2 - y1

        mask_filename = f"mask_{object_id}.png"
        mask_out_path = self.masks_dir / mask_filename

        if box_w > 10 and box_h > 10:
            try:
                gc_mask = np.zeros((h, w), np.uint8)
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)

                rect = (x1, y1, box_w, box_h)
                cv2.grabCut(img, gc_mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
                bin_mask = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype('uint8')

                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, kernel)
                bin_mask = cv2.GaussianBlur(bin_mask, (3, 3), 0)
                _, bin_mask = cv2.threshold(bin_mask, 127, 255, cv2.THRESH_BINARY)
            except Exception:
                bin_mask = np.zeros((h, w), dtype=np.uint8)
                bin_mask[y1:y2, x1:x2] = 255
        else:
            bin_mask = np.zeros((h, w), dtype=np.uint8)
            bin_mask[y1:y2, x1:x2] = 255

        cv2.imwrite(str(mask_out_path), bin_mask)

        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = bin_mask
        cutout_filename = f"cutout_{object_id}.png"
        cv2.imwrite(str(self.objects_dir / cutout_filename), rgba[y1:y2, x1:x2])

        return mask_filename, cutout_filename
