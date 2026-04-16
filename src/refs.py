"""
src/refs.py — Programmatic reference images for Gemini render calls.

Each image shows exactly one configuration property so the model
can SEE what we mean rather than interpret text descriptions.

Generated on first call; cached to static/img/ref/.
"""
import os
from PIL import Image, ImageDraw, ImageFont

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "img", "ref")

_SLAT_COLOR   = (205, 183, 153)
_TAPE_COLOR   = (160, 130, 100)
_CORD_COLOR   = (90,  75,  60)
_GAP_COLOR    = (200, 225, 250)   # light blue = daylight through open slats
_BG           = (255, 255, 255)

try:
    _FONT_BOLD  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    _FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except Exception:
    _FONT_BOLD  = ImageFont.load_default()
    _FONT_SMALL = ImageFont.load_default()


def _text_center(draw, y, text, font, color=(20, 20, 20), img_w=600):
    draw.text((img_w // 2, y), text, fill=color, font=font, anchor="mt")


def _gen_ladderband():
    W, H = 600, 420
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    slat_h, gap_h, num = 38, 6, 7
    y0 = 50

    tape_lx, tape_rx = 100, 145
    tape_rx2, tape_lx2 = W - 145, W - 100

    slat_ys = []
    y = y0
    for _ in range(num):
        slat_ys.append(y)
        y += slat_h + gap_h

    total_h = slat_ys[-1] + slat_h

    # Draw tapes behind slats
    for tx1, tx2 in ((tape_lx, tape_rx), (tape_rx2, tape_lx2)):
        draw.rectangle([tx1, y0 - 4, tx2, total_h + 4], fill=_TAPE_COLOR)

    # Draw slats on top
    for sy in slat_ys:
        draw.rectangle([30, sy, W - 30, sy + slat_h], fill=_SLAT_COLOR, outline=(150, 125, 100), width=1)
        # Tape crosses through slat (slightly darker strip)
        for tx1, tx2 in ((tape_lx, tape_rx), (tape_rx2, tape_lx2)):
            draw.rectangle([tx1, sy, tx2, sy + slat_h], fill=_TAPE_COLOR)

    # Headrail
    draw.rectangle([30, y0 - 14, W - 30, y0 - 2], fill=(120, 100, 80))
    # Bottom rail
    draw.rectangle([30, total_h + 2, W - 30, total_h + 14], fill=(120, 100, 80))

    _text_center(draw, 8, "LADDERBAND — WIDE FABRIC TAPES", _FONT_BOLD, (10, 10, 10))
    draw.text((tape_lx + 22, total_h + 20), "← fabric tape\n  (approx 5 cm wide)", fill=_TAPE_COLOR, font=_FONT_SMALL)

    img.save(os.path.join(REF_DIR, "ref_ladderband.png"))


def _gen_ladderkoord():
    W, H = 600, 420
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    slat_h, gap_h, num = 38, 6, 7
    y0 = 50

    cord_lx = 122
    cord_rx = W - 122

    slat_ys = []
    y = y0
    for _ in range(num):
        slat_ys.append(y)
        y += slat_h + gap_h

    total_h = slat_ys[-1] + slat_h

    # Draw slats
    for sy in slat_ys:
        draw.rectangle([30, sy, W - 30, sy + slat_h], fill=_SLAT_COLOR, outline=(150, 125, 100), width=1)

    # Headrail + bottom rail
    draw.rectangle([30, y0 - 14, W - 30, y0 - 2], fill=(120, 100, 80))
    draw.rectangle([30, total_h + 2, W - 30, total_h + 14], fill=(120, 100, 80))

    # Thin cords ON TOP of slats
    draw.line([(cord_lx, y0 - 4), (cord_lx, total_h + 4)], fill=_CORD_COLOR, width=3)
    draw.line([(cord_rx, y0 - 4), (cord_rx, total_h + 4)], fill=_CORD_COLOR, width=3)

    _text_center(draw, 8, "LADDERKOORD — THIN CORDS ONLY", _FONT_BOLD, (10, 10, 10))
    draw.text((cord_lx + 8, total_h + 22), "← thin cord (~3 mm)\nNO fabric tapes", fill=_CORD_COLOR, font=_FONT_SMALL)

    img.save(os.path.join(REF_DIR, "ref_ladderkoord.png"))


def _gen_halfopen():
    W, H = 600, 400
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    face_h = 22   # visible slat face at 45°
    gap_h  = 22   # daylight gap (equal = true 45°)
    y = 50
    while y + face_h + gap_h < H - 40:
        draw.rectangle([30, y, W - 30, y + gap_h], fill=_GAP_COLOR)
        y += gap_h
        draw.rectangle([30, y, W - 30, y + face_h], fill=_SLAT_COLOR, outline=(150, 125, 100), width=1)
        y += face_h

    _text_center(draw, 8, "HALF OPEN — Slats at 45°", _FONT_BOLD, (0, 100, 0))
    _text_center(draw, H - 30, "Light blue = daylight gap   Beige = slat face   Gaps EQUAL to slat width",
                 _FONT_SMALL, (0, 80, 0))

    img.save(os.path.join(REF_DIR, "ref_halfopen.png"))


def _gen_gesloten():
    W, H = 600, 400
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    slat_h  = 42
    overlap = 6   # slats overlap → no gaps
    y = 50
    while y + slat_h < H - 40:
        draw.rectangle([30, y, W - 30, y + slat_h], fill=_SLAT_COLOR, outline=(165, 140, 115), width=1)
        y += slat_h - overlap

    _text_center(draw, 8, "VOLLEDIG GESLOTEN — Slats flat, fully closed", _FONT_BOLD, (160, 0, 0))
    _text_center(draw, H - 30, "NO gaps — slats overlap — solid opaque surface — zero light passes through",
                 _FONT_SMALL, (140, 0, 0))

    img.save(os.path.join(REF_DIR, "ref_gesloten.png"))


def _gen_slats_25mm():
    W, H = 480, 360
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    # 25mm slats: narrow → many rows → ratio 1:1 face/gap when open
    slat_h, gap_h = 14, 4
    y = 50
    while y + slat_h < H - 30:
        draw.rectangle([20, y, W - 20, y + slat_h], fill=_SLAT_COLOR, outline=(150, 125, 100))
        y += slat_h + gap_h

    _text_center(draw, 8, "25 mm SLATS — NARROW / MANY ROWS", _FONT_BOLD, (0, 0, 160), W)
    img.save(os.path.join(REF_DIR, "ref_slats_25mm.png"))


def _gen_slats_50mm():
    W, H = 480, 360
    img  = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    # 50mm slats: twice as wide as 25mm → half as many rows
    slat_h, gap_h = 28, 4
    y = 50
    while y + slat_h < H - 30:
        draw.rectangle([20, y, W - 20, y + slat_h], fill=_SLAT_COLOR, outline=(150, 125, 100))
        y += slat_h + gap_h

    _text_center(draw, 8, "50 mm SLATS — WIDE / FEWER ROWS", _FONT_BOLD, (0, 0, 160), W)
    img.save(os.path.join(REF_DIR, "ref_slats_50mm.png"))


def generate_all():
    os.makedirs(REF_DIR, exist_ok=True)
    _gen_ladderband()
    _gen_ladderkoord()
    _gen_halfopen()
    _gen_gesloten()
    _gen_slats_25mm()
    _gen_slats_50mm()


def load(filename: str):
    """Return (bytes, mime_type) for a reference image, generating if needed."""
    path = os.path.join(REF_DIR, filename)
    if not os.path.exists(path):
        generate_all()
    with open(path, "rb") as f:
        return f.read(), "image/png"
