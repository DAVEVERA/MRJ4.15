"""
render_blind.py — Procedural 2D venetian blind renderer (PIL).

Deterministic. Given config + target pixel size, draws a venetian blind with
exact slat count, slat width, ladder tapes, tilt angle and color on a
transparent RGBA canvas. No AI involved here — every pixel is calculated.

Output is a flat front-on render. Perspective warp happens in a later stage
using the SAM2 bounds + depth estimate.
"""

import io
import math
import base64
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter


# ── REAL-WORLD CONSTANTS (mm) ────────────────────────────────────

DEFAULT_WINDOW_HEIGHT_MM = 1400.0   # standard NL interior window
HEADRAIL_HEIGHT_MM       = 35.0
BOTTOMRAIL_HEIGHT_MM     = 25.0
LADDER_TAPE_WIDTH_MM     = 30.0
SLAT_OVERLAP_FACTOR      = 0.88     # pitch = slat_width × this (slats overlap when closed)


# ── PUBLIC API ───────────────────────────────────────────────────

def render_blind_panel(
    width_px:         int,
    height_px:        int,
    config:           dict,
    state:            str,
    extra:            dict,
    window_height_mm: float = DEFAULT_WINDOW_HEIGHT_MM,
) -> Image.Image:
    """
    Render a venetian blind panel front-on at exact pixel size, transparent bg.

    Args:
      width_px, height_px : output canvas size (will match SAM2 bounds later)
      config              : {colorName, colorHex, productType}
      state               : "Geheel uitgerold" (closed) | "Tot de helft" (45° tilt)
      extra               : {slatWidth: "25mm"|"50mm", ladderTape: bool, lighting: ...}
      window_height_mm    : real-world window height for mm→px scale

    Returns:
      PIL.Image (RGBA), transparent everywhere except the blind.
    """
    color_hex   = config.get("colorHex") or "#E8E0D5"
    slat_w_mm   = 25.0 if extra.get("slatWidth", "50mm") == "25mm" else 50.0
    has_tape    = bool(extra.get("ladderTape", True))
    is_wood     = "houten" in (config.get("productType", "")).lower()

    rgb         = _hex_to_rgb(color_hex)
    px_per_mm   = height_px / window_height_mm

    headrail_h  = max(4, int(HEADRAIL_HEIGHT_MM   * px_per_mm))
    bottomrail_h = max(4, int(BOTTOMRAIL_HEIGHT_MM * px_per_mm))

    img  = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    slat_top = headrail_h
    slat_bot = height_px - bottomrail_h
    slat_h   = slat_bot - slat_top

    # ── Slats area ──
    if state == "Geheel uitgerold":
        _draw_closed_slats(draw, width_px, slat_top, slat_bot, slat_w_mm, px_per_mm, rgb)
    else:
        _draw_tilted_slats(draw, width_px, slat_top, slat_bot, slat_w_mm, px_per_mm, rgb,
                           tilt_deg=45.0, is_wood=is_wood)

    # ── Ladder tapes / strings (drawn over slats) ──
    tape_xs = (0.20, 0.80)
    if has_tape:
        tape_w = max(3, int(LADDER_TAPE_WIDTH_MM * px_per_mm))
        tape_color = _lighten(rgb, 1.06)
        for xf in tape_xs:
            xc = int(width_px * xf)
            draw.rectangle(
                [xc - tape_w // 2, slat_top, xc + tape_w // 2, slat_bot],
                fill=(*tape_color, 235),
            )
            # Subtle inner shadow on tape edges
            edge_color = _darken(tape_color, 0.92)
            draw.line([(xc - tape_w // 2, slat_top), (xc - tape_w // 2, slat_bot)],
                      fill=(*edge_color, 200), width=1)
            draw.line([(xc + tape_w // 2, slat_top), (xc + tape_w // 2, slat_bot)],
                      fill=(*edge_color, 200), width=1)
    else:
        # Thin string cords only
        cord_color = _darken(rgb, 0.55)
        for xf in tape_xs:
            x = int(width_px * xf)
            draw.line([(x, slat_top), (x, slat_bot)], fill=(*cord_color, 200), width=1)

    # ── Headrail (over the top of slats area) ──
    headrail_color = _darken(rgb, 0.78)
    draw.rectangle([0, 0, width_px, headrail_h], fill=(*headrail_color, 255))
    # Subtle bottom shadow line under headrail
    draw.line([(0, headrail_h), (width_px, headrail_h)],
              fill=(*_darken(rgb, 0.45), 200), width=1)

    # ── Bottom rail ──
    draw.rectangle([0, slat_bot, width_px, height_px], fill=(*headrail_color, 255))
    draw.line([(0, slat_bot), (width_px, slat_bot)],
              fill=(*_darken(rgb, 0.45), 200), width=1)

    return img


# ── DRAWING PRIMITIVES ───────────────────────────────────────────

def _draw_closed_slats(draw, width_px, y_top, y_bot, slat_w_mm, px_per_mm, rgb):
    """Fully closed: solid panel with subtle slat division lines."""
    draw.rectangle([0, y_top, width_px, y_bot], fill=(*rgb, 255))

    pitch_px = slat_w_mm * SLAT_OVERLAP_FACTOR * px_per_mm
    n_div    = max(1, int((y_bot - y_top) / pitch_px))
    line_col = _darken(rgb, 0.82)

    for i in range(1, n_div):
        y = y_top + int(i * (y_bot - y_top) / n_div)
        draw.line([(0, y), (width_px, y)], fill=(*line_col, 255), width=1)


def _draw_tilted_slats(draw, width_px, y_top, y_bot, slat_w_mm, px_per_mm, rgb,
                        tilt_deg=45.0, is_wood=True):
    """
    Tilted slats with gaps. Each slat = horizontal band of height
    slat_w × cos(tilt). Gaps between slats reveal the background (transparent).
    """
    tilt_rad      = math.radians(tilt_deg)
    pitch_px      = slat_w_mm * px_per_mm                      # full slat-to-slat spacing at this tilt
    visible_h     = slat_w_mm * px_per_mm * math.cos(tilt_rad) # vertical projection per slat
    slat_area_h   = y_bot - y_top
    n_slats       = max(1, int(round(slat_area_h / pitch_px)))
    actual_pitch  = slat_area_h / n_slats

    light_rgb  = _lighten(rgb, 1.18)
    shadow_rgb = _darken(rgb, 0.55)
    edge_top_w = max(1, int(visible_h * 0.10))
    edge_bot_w = max(1, int(visible_h * 0.08))

    for i in range(n_slats):
        y_center = y_top + (i + 0.5) * actual_pitch
        ytop = int(round(y_center - visible_h / 2))
        ybot = int(round(y_center + visible_h / 2))

        # Slat body
        draw.rectangle([0, ytop, width_px, ybot], fill=(*rgb, 255))

        # Top edge highlight (light catches the top curve of the slat)
        for k in range(edge_top_w):
            t = 1.0 - (k / max(1, edge_top_w))   # fade from light → base
            col = _mix(light_rgb, rgb, t * 0.7)
            draw.line([(0, ytop + k), (width_px, ytop + k)], fill=(*col, 255), width=1)

        # Bottom edge shadow (underside in shade)
        for k in range(edge_bot_w):
            t = 1.0 - (k / max(1, edge_bot_w))
            col = _mix(shadow_rgb, rgb, t * 0.6)
            draw.line([(0, ybot - k), (width_px, ybot - k)], fill=(*col, 255), width=1)

        # Wood grain hint (very subtle horizontal streaks)
        if is_wood and visible_h >= 6:
            grain = _darken(rgb, 0.93)
            ymid = (ytop + ybot) // 2
            draw.line([(0, ymid), (width_px, ymid)], fill=(*grain, 90), width=1)


# ── COLOR UTILS ──────────────────────────────────────────────────

def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _darken(rgb, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def _lighten(rgb, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in rgb)


def _mix(a, b, t):
    """Mix rgb a→b by factor t (0..1, 0=all a)."""
    return tuple(max(0, min(255, int(a[i] * (1 - t) + b[i] * t))) for i in range(3))


# ── BASE64 EXPORT ────────────────────────────────────────────────

def panel_to_b64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
