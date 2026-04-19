"""
sam2_segment.py — Window Detection & Segmentation via SAM2

Detects the window region in a room photo and returns both bounds and a
binary mask. The mask is used by the render pipeline to tell Gemini
exactly which pixels belong to the window.
"""

import sys
import base64
import io
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.AI.utils import strip_data_url


_PREDICTOR = None


def get_sam2_predictor():
    """Lazy-load SAM2 predictor. Cached after first call."""
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR

    try:
        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
    except ImportError as exc:
        raise RuntimeError(f"SAM2 not installed: {exc}")

    checkpoint = ROOT / "models" / "sam2.1_hiera_large.pt"
    if not checkpoint.exists():
        raise FileNotFoundError(
            f"SAM2.1 checkpoint missing at {checkpoint}. "
            f"Download from https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt"
        )

    config = "configs/sam2.1/sam2.1_hiera_l.yaml"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_sam2(config, str(checkpoint), device=device)
    _PREDICTOR = SAM2ImagePredictor(model)
    return _PREDICTOR


def detect_window_bounds(image_b64: str) -> dict:
    """
    Detect the window region in a room photo.

    Strategy: prompt SAM2 with a small grid of foreground points across the
    upper-middle band of the image (where windows typically live), then
    pick the largest contiguous mask. This handles multi-panel windows
    (side panels + door, transom + main pane) better than a single point.

    Returns:
        {
          "success": bool,
          "bounds": {"x": int, "y": int, "w": int, "h": int},
          "confidence": float,
          "mask_b64": "data:image/png;base64,...",  # binary mask
          "overlay_b64": "data:image/png;base64,..." # original + red rect outline
        }
    or {"success": False, "error": "..."}
    """
    try:
        mime, raw_b64 = strip_data_url(image_b64)
        img_bytes = base64.b64decode(raw_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_w, img_h = img.size
        np_img = np.array(img)

        predictor = get_sam2_predictor()
        predictor.set_image(np_img)

        # Strategy: tight cluster of positive seeds on the upper-middle (where
        # windows live in interior photos) + explicit negative seeds at image
        # corners and edge midpoints (almost always wall/floor/ceiling, never
        # window). The negatives push SAM2 away from picking the entire alcove.
        pos_xs = [int(img_w * f) for f in (0.35, 0.50, 0.65)]
        pos_ys = [int(img_h * f) for f in (0.35, 0.45)]
        pos = [(x, y) for y in pos_ys for x in pos_xs]

        m = 0.04  # 4% margin from image edge for negatives
        neg = [
            (int(img_w * m),         int(img_h * m)),          # TL
            (int(img_w * (1 - m)),   int(img_h * m)),          # TR
            (int(img_w * m),         int(img_h * (1 - m))),    # BL
            (int(img_w * (1 - m)),   int(img_h * (1 - m))),    # BR
            (int(img_w * m),         int(img_h * 0.50)),       # mid-left
            (int(img_w * (1 - m)),   int(img_h * 0.50)),       # mid-right
            (int(img_w * 0.50),      int(img_h * (1 - m))),    # bottom-mid (floor)
        ]

        points = np.array(pos + neg, dtype=np.float32)
        labels = np.array([1] * len(pos) + [0] * len(neg), dtype=np.int32)

        masks, scores, _ = predictor.predict(
            point_coords=points,
            point_labels=labels,
            multimask_output=True,
        )

        if masks is None or len(masks) == 0:
            return {"success": False, "error": "SAM2 returned no masks"}

        # Pick mask with highest SAM2 confidence score, filtered to plausible
        # window-area range (5% < area < 65% of image — rules out tiny artifacts
        # AND whole-alcove blobs that the negatives didn't fully suppress).
        candidates = []
        total = float(img_w * img_h)
        for i, (m_arr, s) in enumerate(zip(masks, scores)):
            frac = m_arr.sum() / total
            if 0.05 <= frac <= 0.65:
                candidates.append((float(s), i, m_arr))
        if not candidates:
            # Fall back: just take highest score
            best_idx = int(np.argmax(scores))
        else:
            candidates.sort(key=lambda c: -c[0])
            best_idx = candidates[0][1]

        mask = masks[best_idx].astype(np.uint8)
        score = float(scores[best_idx])

        if mask.sum() == 0:
            return {"success": False, "error": "Selected mask is empty"}

        # Bounding box from mask
        ys_nz, xs_nz = np.where(mask > 0)
        x_min, x_max = int(xs_nz.min()), int(xs_nz.max())
        y_min, y_max = int(ys_nz.min()), int(ys_nz.max())

        bounds = {
            "x": x_min,
            "y": y_min,
            "w": x_max - x_min,
            "h": y_max - y_min,
        }

        # Sanity check — reject pathological masks
        area_frac = mask.sum() / float(img_w * img_h)
        if area_frac < 0.02 or area_frac > 0.85:
            return {
                "success": False,
                "error": f"Mask area fraction {area_frac:.2f} outside plausible range",
            }

        # Build overlay image: original + red rectangle outline
        overlay = img.copy()
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(
            [x_min, y_min, x_max, y_max],
            outline=(255, 0, 0),
            width=max(4, img_w // 200),
        )

        return {
            "success":     True,
            "bounds":      bounds,
            "confidence":  score,
            "mask_b64":    _png_b64(mask * 255),
            "overlay_b64": _pil_b64(overlay),
        }

    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def _png_b64(mask_arr: np.ndarray) -> str:
    """Encode a 2-D uint8 array as base64 PNG data URL."""
    img = Image.fromarray(mask_arr.astype(np.uint8), mode="L")
    return _pil_b64(img)


def _pil_b64(img: Image.Image) -> str:
    """Encode a PIL image as base64 PNG data URL."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
