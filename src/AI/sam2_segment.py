"""
sam2_segment.py — Window Detection & Segmentation via SAM2

Detects the window area in room photos and returns bounds for blind visualization.
"""

import base64
from pathlib import Path
from PIL import Image
import io


def get_sam2_predictor():
    """
    Lazy-load SAM2 predictor. Called once on first usage.
    """
    try:
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        # SAM2 checkpoint path — assumes models/sam2_hiera_large.pt exists
        checkpoint = Path(__file__).parent.parent.parent / "models" / "sam2_hiera_large.pt"
        if not checkpoint.exists():
            # Fallback: try to download or use default path
            checkpoint = "facebook/sam2-hiera-large"

        model = build_sam2("hiera_l", checkpoint)
        predictor = SAM2ImagePredictor(model)
        return predictor
    except ImportError:
        raise RuntimeError(
            "SAM2 not installed. Run: pip install -e 'git+https://github.com/facebookresearch/sam2.git@main#egg=sam2'"
        )


def detect_window_bounds(image_b64: str) -> dict:
    """
    Detect window region in a room photo using SAM2 auto-prompt.

    Returns:
        {
            "success": bool,
            "bounds": { "x": int, "y": int, "w": int, "h": int },  # Pixel coords
            "confidence": float,
            "error": str (if success=False)
        }
    """
    try:
        # Decode base64 image
        mime, raw_b64 = _strip_data_url(image_b64)
        img_bytes = base64.b64decode(raw_b64)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_w, img_h = img.size

        # Initialize SAM2
        predictor = get_sam2_predictor()
        predictor.set_image(img)

        # Auto-prompt: use image center as a seed point for window detection
        # In a room photo, the window is typically in the upper-middle area
        prompt_x = int(img_w * 0.5)
        prompt_y = int(img_h * 0.4)

        points = [[prompt_x, prompt_y]]
        labels = [1]  # 1 = foreground (the window)

        # Get SAM2 mask
        masks, scores, logits = predictor.predict(
            point_coords=points,
            point_labels=labels,
            multimask_output=False,
        )

        if masks is None or len(masks) == 0:
            return {
                "success": False,
                "error": "SAM2 failed to segment any region",
            }

        mask = masks[0].astype("uint8") * 255
        score = float(scores[0])

        # Extract bounding box from mask
        rows = list(range(img_h))
        cols = list(range(img_w))
        rows_nz = [r for r in rows if mask[r, :].max() > 0]
        cols_nz = [c for c in cols if mask[:, c].max() > 0]

        if not rows_nz or not cols_nz:
            return {"success": False, "error": "Mask is empty"}

        y_min, y_max = min(rows_nz), max(rows_nz)
        x_min, x_max = min(cols_nz), max(cols_nz)

        bounds = {
            "x": int(x_min),
            "y": int(y_min),
            "w": int(x_max - x_min),
            "h": int(y_max - y_min),
        }

        return {"success": True, "bounds": bounds, "confidence": score}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _strip_data_url(data_url: str) -> tuple:
    if data_url.startswith("data:"):
        header, b64 = data_url.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")
        return mime, b64
    return "image/jpeg", data_url
