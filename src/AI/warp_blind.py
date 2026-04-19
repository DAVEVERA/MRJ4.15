"""
warp_blind.py — Perspective warp the procedural blind onto the SAM2 window quad.

Pipeline:
  1. SAM2 mask → 4 corners (TL, TR, BR, BL)
  2. Render front-on blind at the destination's bbox size (preserves pixel density)
  3. PIL PERSPECTIVE transform: source rect → destination quad
  4. Alpha-composite the warped blind over the original photo
"""

import io
import base64
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageFilter


# ── MASK PREP ────────────────────────────────────────────────────

def dilate_mask(mask_arr: np.ndarray, px: int = 12) -> np.ndarray:
    """Expand the mask outward by `px` pixels (PIL MaxFilter)."""
    if px <= 0:
        return mask_arr
    img = Image.fromarray((mask_arr > 0).astype(np.uint8) * 255, mode="L")
    img = img.filter(ImageFilter.MaxFilter(size=px * 2 + 1))
    return np.array(img)


def erode_mask(mask_arr: np.ndarray, px: int = 12) -> np.ndarray:
    """Shrink the mask inward by `px` pixels (PIL MinFilter)."""
    if px <= 0:
        return mask_arr
    img = Image.fromarray((mask_arr > 0).astype(np.uint8) * 255, mode="L")
    img = img.filter(ImageFilter.MinFilter(size=px * 2 + 1))
    return np.array(img)


def clean_mask(mask_arr: np.ndarray, open_px: int = 18, dilate_px: int = 14) -> np.ndarray:
    """
    Morphological opening (erode then dilate) to drop thin protrusions
    (windowsills, mullion stubs, plant leaves), then a final dilate to
    extend onto the kozijn edge.

    Result: the mask's bounding box snaps to the main window body, not its
    outliers — so bbox-based corner detection gives a tight rectangle.
    """
    eroded  = erode_mask(mask_arr, px=open_px)
    if eroded.max() == 0:
        # Erosion wiped the mask out — fall back to original + just outward dilate
        return dilate_mask(mask_arr, px=dilate_px)
    reopened = dilate_mask(eroded, px=open_px)
    return dilate_mask(reopened, px=dilate_px)


# ── CORNER DETECTION ─────────────────────────────────────────────

def find_window_corners(mask_arr: np.ndarray) -> List[Tuple[int, int]]:
    """
    Return the 4 axis-aligned bounding-box corners of the mask:
    [TL, TR, BR, BL] in (x, y).

    This forces the warped blind to be rectangular (no perspective skew).
    Right for the common case of straight-on product photography. For real
    perspective handling we'd need depth estimation or a separate 4-point
    detector — out of scope for the procedural pipeline.
    """
    ys, xs = np.where(mask_arr > 0)
    if xs.size == 0:
        raise ValueError("Mask is empty — cannot find corners")

    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())

    return [
        (x_min, y_min),  # TL
        (x_max, y_min),  # TR
        (x_max, y_max),  # BR
        (x_min, y_max),  # BL
    ]


# ── PERSPECTIVE TRANSFORM ────────────────────────────────────────

def _perspective_coeffs(source: list, target: list) -> list:
    """
    Solve for 8 PIL perspective coefficients (a..h).

    PIL maps OUTPUT (x,y) → INPUT via:
      input_x = (a*x + b*y + c) / (g*x + h*y + 1)
      input_y = (d*x + e*y + f) / (g*x + h*y + 1)

    Args:
      source : 4 points in the INPUT image  (the front-on blind)
      target : 4 points in the OUTPUT image (window quad on the photo)
    """
    matrix = []
    for s, t in zip(source, target):
        matrix.append([t[0], t[1], 1, 0, 0, 0, -s[0] * t[0], -s[0] * t[1]])
        matrix.append([0, 0, 0, t[0], t[1], 1, -s[1] * t[0], -s[1] * t[1]])
    A = np.array(matrix, dtype=np.float64)
    B = np.array(source, dtype=np.float64).flatten()
    return np.linalg.solve(A, B).tolist()


def warp_blind_to_window(
    blind_rgba: Image.Image,
    corners:    List[Tuple[int, int]],
    output_size: Tuple[int, int],
) -> Image.Image:
    """
    Warp the front-on blind to fit the window quad.

    Args:
      blind_rgba  : RGBA PIL image, transparent background
      corners     : [TL, TR, BR, BL] in output-image coords
      output_size : (W, H) of the final canvas (matches the photo size)

    Returns:
      RGBA PIL image at output_size with the blind warped into the quad.
    """
    bw, bh = blind_rgba.size
    src = [(0, 0), (bw, 0), (bw, bh), (0, bh)]
    coeffs = _perspective_coeffs(src, corners)

    return blind_rgba.transform(
        output_size,
        Image.PERSPECTIVE,
        coeffs,
        Image.BICUBIC,
    )


# ── LIGHT INTEGRATION ────────────────────────────────────────────

def apply_lighting(
    warped_blind: Image.Image,
    photo:        Image.Image,
    blur_px:      int   = 25,
    strength:     float = 0.55,
    min_mul:      float = 0.55,
    max_mul:      float = 1.45,
) -> Image.Image:
    """
    Modulate the warped blind's luminosity by what's behind it in the photo.

    Effect: bright window panes "shine through" → those slats look brighter;
    dark mullion frames create darker bands across the blind. Gives the blind
    real lighting without a generative model.

    Args:
      warped_blind : RGBA blind warped to fit the window
      photo        : original room photo (any mode), same canvas size
      blur_px      : Gaussian blur radius for sampling the photo (smooths
                     noise so individual leaf/branch pixels don't speckle)
      strength     : 0..1 — how much the photo brightness modulates the blind
                     (0 = no effect, 1 = pure photo brightness)
      min_mul/max_mul : clamp the multiplier so we don't blow out highlights
                        or crush shadows entirely
    """
    base = photo.convert("RGB").resize(warped_blind.size, Image.LANCZOS)
    base_blur = base.filter(ImageFilter.GaussianBlur(radius=blur_px))

    photo_rgb = np.array(base_blur, dtype=np.float32) / 255.0      # H,W,3
    blind_arr = np.array(warped_blind, dtype=np.float32) / 255.0   # H,W,4

    # Per-pixel luminance of the blurred photo, normalized around the
    # MASKED region's mean (so a "neutral" multiplier = 1.0)
    lum = 0.299 * photo_rgb[..., 0] + 0.587 * photo_rgb[..., 1] + 0.114 * photo_rgb[..., 2]
    alpha = blind_arr[..., 3]
    mask = alpha > 0.05

    if not mask.any():
        return warped_blind

    mean_lum = float(lum[mask].mean())
    if mean_lum < 1e-3:
        return warped_blind

    # Multiplier: how much brighter / darker each spot should be
    mul = lum / mean_lum
    mul = 1.0 + (mul - 1.0) * strength
    mul = np.clip(mul, min_mul, max_mul)
    mul = mul[..., None]   # broadcast over RGB

    blind_arr[..., :3] = np.clip(blind_arr[..., :3] * mul, 0.0, 1.0)

    out = (blind_arr * 255.0).astype(np.uint8)
    return Image.fromarray(out, mode="RGBA")


# ── COMPOSITE ────────────────────────────────────────────────────

def composite_over_photo(photo: Image.Image, warped_blind: Image.Image) -> Image.Image:
    """
    Alpha-composite the warped (RGBA) blind over a photo (any mode).
    Returns RGB.
    """
    base = photo.convert("RGBA")
    if warped_blind.size != base.size:
        warped_blind = warped_blind.resize(base.size, Image.LANCZOS)
    return Image.alpha_composite(base, warped_blind).convert("RGB")


# ── BASE64 / MASK HELPERS ────────────────────────────────────────

def b64_to_pil(data_url: str) -> Image.Image:
    if data_url.startswith("data:"):
        data_url = data_url.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(data_url)))


def mask_b64_to_array(mask_b64: str) -> np.ndarray:
    """Decode a base64 PNG mask to a 2-D uint8 numpy array."""
    img = b64_to_pil(mask_b64).convert("L")
    return np.array(img)


def pil_to_b64_jpeg(img: Image.Image, quality: int = 92) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# ── DEBUG OVERLAY ────────────────────────────────────────────────

def draw_corner_debug(photo: Image.Image, corners: list) -> Image.Image:
    """Draw the 4 detected corners on the photo for debugging."""
    from PIL import ImageDraw
    img  = photo.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]  # TL,TR,BR,BL
    labels = ["TL", "TR", "BR", "BL"]
    r = max(8, img.width // 120)
    # Lines
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        draw.line([a, b], fill=(255, 255, 255), width=max(2, img.width // 400))
    # Dots
    for (x, y), col, lbl in zip(corners, colors, labels):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=(0, 0, 0), width=2)
        draw.text((x + r + 4, y - r), lbl, fill=col)
    return img
