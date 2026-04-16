"""
app.py — MRJ4.15 Flask Application
Mr. Jealousy Interior Intelligence Tool

Routes:
  GET  /           → serve static/index.html
  POST /analyze    → run phases 1-8 (Claude vision)
  POST /render     → run phase 9 (Gemini 2.5 Flash image generation)
"""

import os
import sys
import base64
import urllib.request
from pathlib import Path

from google import genai
from google.genai import types as genai_types
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env before anything else so API keys are available
# whether the app is started via start.bat or directly.
load_dotenv()

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import core
from src.AI.analyse_claude import run_analysis_pipeline
from src.AI.utils import save_upload_locally, upload_to_supabase
from src.AI.sam2_segment import detect_window_bounds
from src import refs as ref_images

# Pre-generate reference images at startup
ref_images.generate_all()


# ── APP SETUP ───────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)


# ── STATIC / INDEX ───────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory("static", "favicon.ico") if \
        (ROOT / "static" / "favicon.ico").exists() else ("", 204)


# ── PHASE 1-8: ANALYZE ──────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Receive a base64 image, upload it, and run the 9-phase analysis pipeline.
    Returns an AnalysisResult JSON object.
    """
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")

    if not image_b64:
        return jsonify({"error": "Geen afbeelding ontvangen."}), 400

    # Phase 1: upload (non-blocking — failures are non-critical)
    try:
        upload_to_supabase(image_b64)
    except Exception as exc:
        app.logger.warning("Supabase upload failed (non-critical): %s", exc)

    try:
        save_upload_locally(image_b64)
    except Exception as exc:
        app.logger.warning("Local save failed (non-critical): %s", exc)

    # Phases 2-8: run the pipeline
    try:
        result = run_analysis_pipeline(image_b64)
        return jsonify(result)
    except Exception as exc:
        app.logger.error("Pipeline error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


# ── PHASE 9: RENDER ─────────────────────────────────────────────

@app.route("/render", methods=["POST"])
def render():
    """
    Phase 9: Generate a photorealistic visualization using Gemini 2.5 Flash.
    Returns { image: "data:image/jpeg;base64,..." }
    """
    data = request.get_json(silent=True) or {}

    image_b64 = data.get("image")
    config    = data.get("config", {})
    mounting  = data.get("mounting", "in de dag")
    state     = data.get("state", "Tot de helft")
    extra     = data.get("extraOptions", {})
    analysis  = data.get("analysis", {})

    if not image_b64 or not config:
        return jsonify({"error": "Ontbrekende parameters."}), 400

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return jsonify({"error": "GEMINI_API_KEY is niet geconfigureerd."}), 500

    try:
        generated = _run_gemini_render(
            image_b64=image_b64,
            config=config,
            mounting=mounting,
            state=state,
            extra=extra,
            analysis=analysis,
            api_key=gemini_key,
            quality="full",
        )
        return jsonify({"image": generated})
    except Exception as exc:
        app.logger.error("Render error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


# ── PHASE 9-BIS: PREVIEW ──────────────────────────────────────

@app.route("/preview", methods=["POST"])
def preview():
    """
    Phase 9-bis: Fast preview using Gemini 2.5 Flash with lower quality.
    Called on result page load & config changes. ~10-15 seconds.
    Returns { image: "data:image/jpeg;base64,..." }
    """
    data = request.get_json(silent=True) or {}

    image_b64 = data.get("image")
    config    = data.get("config", {})
    mounting  = data.get("mounting", "in de dag")
    state     = data.get("state", "Tot de helft")
    extra     = data.get("extraOptions", {})
    analysis  = data.get("analysis", {})

    if not image_b64 or not config:
        return jsonify({"error": "Ontbrekende parameters."}), 400

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return jsonify({"error": "GEMINI_API_KEY is niet geconfigureerd."}), 500

    try:
        generated = _run_gemini_render(
            image_b64=image_b64,
            config=config,
            mounting=mounting,
            state=state,
            extra=extra,
            analysis=analysis,
            api_key=gemini_key,
            quality="preview",
        )
        return jsonify({"image": generated})
    except Exception as exc:
        app.logger.error("Preview error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


def _run_gemini_render(
    image_b64: str,
    config: dict,
    mounting: str,
    state: str,
    extra: dict,
    analysis: dict,
    api_key: str,
    quality: str = "full",
) -> str:
    """
    PROMPT 2 — GENERATION / VISUALIZATION PROMPT
    Build the render prompt from core.py maps and call Gemini 2.5 Flash.

    quality="preview" → lower resolution, faster (~10-15s)
    quality="full"    → full HD render, slower (~30-45s)
    """
    import json as _json

    # Resolve descriptors from core.py
    state_desc    = core.STATE_MAP.get(state, state)
    mounting_desc = core.resolve_mounting(mounting)
    lighting_key  = extra.get("lighting", "Middag (Helder)")
    lighting_desc = core.resolve_lighting(lighting_key)
    product_desc  = core.PRODUCT_MAP.get(config.get("productType", ""), "Horizontal Venetian Blinds")

    ladder_tape = extra.get("ladderTape", True)
    slat_width  = extra.get("slatWidth", "50mm")
    tape_desc   = "with wide decorative fabric ladder tapes (vertical fabric strips)" if ladder_tape \
                  else "with minimalist string cords (no wide fabric tapes)"
    slat_desc   = f"with {slat_width} wide horizontal slats"

    analysis_block = (
        _json.dumps(analysis, ensure_ascii=False, indent=2)
        if analysis
        else "No analysis JSON provided — derive window geometry purely from the image."
    )

    quality_note = (
        "⚡ SPEED PRIORITY (PREVIEW): Optimize for speed (~10-15s). "
        "Use efficient rendering, lower detail, accept minor approximations."
        if quality == "preview"
        else "✅ FULL QUALITY (RENDER): Maximum photorealism, full detail, no compromises. "
        "This is the final sales-ready image."
    )

    prompt = f"""
You are an Elite Photorealistic Window Treatment Rendering Engine for Mr. Jealousy.

RENDER MODE: {quality_note}

TASK
Using the uploaded room image and the supplied analysis JSON, create a photorealistic \
end visualization of the specified Venetian blind installed on the correct window.

You are NOT allowed to redesign the room. You must ONLY remove any existing window covering \
and insert the new blind as a physically believable architectural object.

════════════════════════════════════════════════════
ABSOLUTE NON-NEGOTIABLE RULES — OVERRIDE EVERYTHING
════════════════════════════════════════════════════

RULE 1 — PRODUCT TYPE
Only render: Horizontal Venetian Blind (Jaloezieën)
Never render: curtains, roller blinds, pleated blinds, Roman blinds, vertical blinds

RULE 2 — EXACT COLOR MATCH (CRITICAL)
The blind slats MUST be rendered in exactly this color:
  Name: {config.get('colorName', '')}
  Hex:  {config.get('colorHex', '')}
The rendered color must match this hex value precisely under the scene's lighting.
Apply realistic light/shadow variation ON TOP of this base color — never deviate from the hue.
FAIL: slats appear in a different color than specified.

RULE 3 — LADDER TYPE (CRITICAL — RENDER EXACTLY AS SPECIFIED)
{tape_desc.upper()}
{"  → Render visible wide fabric tapes running vertically along both sides of the blind, connecting each slat. Tapes are approximately 5cm wide, fabric texture, same color family as slats, perspective-correct." if ladder_tape else "  → Render thin minimalist string cords only. NO wide fabric tapes. Cords are barely visible thin threads."}
FAIL: ladder type does not match the specification above.

RULE 4 — KANTELSTAND / SLAT ANGLE (CRITICAL — DO NOT DEVIATE)
{state_desc}
FAIL: slat angle does not match the specified kantelstand.

RULE 5 — MOUNTING POSITION (CRITICAL)
{mounting_desc}
FAIL: blind is mounted incorrectly (wrong position relative to frame/wall).

════════════════════════════════════════════════════
SCENE PRESERVATION
════════════════════════════════════════════════════
  DO NOT repaint walls, frames, floor, or furniture
  DO NOT restyle the room
  ONLY remove existing window coverings if visible
  ONLY insert the new blind
  The blind must look manufactured, mounted, and photographed in place — not composited

────────────────────────────────────────────────
ANALYSIS JSON (binding source of truth):
{analysis_block}
────────────────────────────────────────────────

STEP 1 — VIRTUAL DEMOLITION
Remove any existing window covering completely.
Reconstruct the bare glass, frame, reveal, and outside view underneath.
The new blind must NEVER sit on top of an old one.

STEP 2 — PRODUCT SPECIFICATION (repeat for emphasis)
Product:      {product_desc}
Material:     {config.get('material', '')}
Color:        {config.get('colorName', '')} — hex {config.get('colorHex', '')} — render this exact color
Slat width:   {slat_width}
Ladder type:  {"Ladderband — wide decorative fabric tapes, clearly visible vertically on both sides of every slat" if ladder_tape else "Ladderkoord — thin minimalist cords only, no fabric tapes"}
Kantelstand:  {state_desc}

STEP 3 — REALISM REQUIREMENTS
  Slats perfectly horizontal, parallel, equidistant
  Realistic headrail at top, bottom rail at sill level
  Correct scale relative to the actual window in the photo
  Physically plausible full-drop geometry matching window height

STEP 4 — LIGHTING PHYSICS
Condition: {lighting_desc}
  Inside mount: cast shadows inside the recess, on sill, adjacent surfaces
  Outside mount: shadows fall across wall and floor with correct drop direction
  Shadow direction and softness match the specified time of day exactly
  Aluminium: subtle specular highlights, sleek metallic finish
  Wood: visible grain texture, matte/satin, warm light absorption

STEP 5 — PERSPECTIVE AND DEPTH
  Match the room's vanishing point exactly
  Align blind to the actual frame plane or wall plane
  Correct depth hierarchy: wall → frame → glass → blind

FINAL OUTPUT GOAL
Photorealistic, sales-ready visualization. The blind looks truly installed in this room.
Color, ladder type, slat angle, and mounting must be exactly as specified — no exceptions.
""".strip()

    # Decode and resize the room image (Gemini rejects oversized inputs)
    mime_type, raw_b64 = _strip_data_url(image_b64)
    img_bytes = base64.b64decode(raw_b64)
    img_bytes  = _resize_image(img_bytes, max_px=1536)

    model_id = core.RENDER_MODEL_FAST if quality == "preview" else core.RENDER_MODEL

    client = genai.Client(api_key=api_key)
    room_part = genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")

    # ── Build reference image parts ───────────────────────────────
    def _ref_part(filename: str) -> genai_types.Part:
        data, mime = ref_images.load(filename)
        return genai_types.Part.from_bytes(data=data, mime_type=mime)

    def _url_part(url: str) -> genai_types.Part | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                raw = r.read()
                ct  = r.headers.get_content_type() or "image/png"
            return genai_types.Part.from_bytes(data=raw, mime_type=ct)
        except Exception:
            return None

    # ── Assemble contents ─────────────────────────────────────────
    # Preview: lean call (prompt + room only) for speed/reliability.
    # Full render: reference images prepended so model sees exact specs.
    contents: list = []

    if quality == "full":
        ladder_ref = _ref_part("ref_ladderband.png" if ladder_tape else "ref_ladderkoord.png")
        kantel_ref = _ref_part("ref_halfopen.png" if state == "Tot de helft" else "ref_gesloten.png")
        slat_ref   = _ref_part("ref_slats_25mm.png" if slat_width == "25mm" else "ref_slats_50mm.png")
        swatch     = _url_part(config.get("sampleUrl", ""))

        ladder_label = "LADDERBAND (wide fabric tapes ~5cm)" if ladder_tape else "LADDERKOORD (thin cords ~3mm, NO fabric tapes)"
        contents += [
            f"REF 1 — LADDER TYPE ({ladder_label}): copy this construction exactly.",
            ladder_ref,
            f"REF 2 — KANTELSTAND ({state}): copy this exact slat angle.",
            kantel_ref,
            f"REF 3 — SLAT WIDTH ({slat_width}): copy these proportions.",
            slat_ref,
        ]
        if swatch:
            contents += [
                f"REF 4 — COLOR SWATCH for '{config.get('colorName', '')}' "
                f"(hex {config.get('colorHex', '')}): match this color exactly on all slats.",
                swatch,
            ]

    contents += [prompt, room_part]

    client   = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    if not response.candidates:
        raise ValueError("Geen candidates in Gemini response.")

    candidate = response.candidates[0]
    if candidate.content is None:
        fr = getattr(candidate, "finish_reason", "UNKNOWN")
        raise ValueError(f"Gemini response geblokkeerd. finish_reason={fr}")

    for part in candidate.content.parts:
        if part.inline_data:
            mime = part.inline_data.mime_type
            data = part.inline_data.data
            return f"data:{mime};base64,{base64.b64encode(data).decode()}"

    raise ValueError("Geen afbeelding in Gemini response.")


def _resize_image(img_bytes: bytes, max_px: int = 1536) -> bytes:
    """Resize image so the longest side ≤ max_px; re-encode as JPEG."""
    import io
    from PIL import Image as _Img
    img = _Img.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), _Img.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _strip_data_url(data_url: str) -> tuple:
    if data_url.startswith("data:"):
        header, b64 = data_url.split(",", 1)
        mime = header.split(";")[0].replace("data:", "")
        return mime, b64
    return "image/jpeg", data_url


# ── ENTRYPOINT ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
