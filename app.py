"""
app.py — MRJ4.15 Flask Application
Mr. Jealousy Interior Intelligence Tool

Routes:
  GET  /           → serve static/index.html
  POST /analyze    → run phases 1-8 (Claude vision)
  POST /render     → run phase 9 (Flux.1 Kontext image generation via fal.ai)
"""

import os
import sys
import base64
import urllib.request
from pathlib import Path

import fal_client
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


# ── APP SETUP ───────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)


# ── STATIC / INDEX ───────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


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

    if not os.getenv("FAL_KEY"):
        return jsonify({"error": "FAL_KEY is niet geconfigureerd."}), 500

    try:
        generated = _run_flux_render(
            image_b64=image_b64,
            config=config,
            mounting=mounting,
            state=state,
            extra=extra,
            analysis=analysis,
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

    if not os.getenv("FAL_KEY"):
        return jsonify({"error": "FAL_KEY is niet geconfigureerd."}), 500

    try:
        generated = _run_flux_render(
            image_b64=image_b64,
            config=config,
            mounting=mounting,
            state=state,
            extra=extra,
            analysis=analysis,
            quality="preview",
        )
        return jsonify({"image": generated})
    except Exception as exc:
        app.logger.error("Preview error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


def _run_flux_render(
    image_b64: str,
    config: dict,
    mounting: str,
    state: str,
    extra: dict,
    analysis: dict,
    quality: str = "full",
) -> str:
    """
    PROMPT 2 — GENERATION / VISUALIZATION PROMPT
    Build the render prompt from core.py maps and call Flux.1 Kontext via fal.ai.

    quality="preview" → fal-ai/flux-pro/kontext  (~10-20s, guidance 2.5)
    quality="full"    → fal-ai/flux-pro/kontext/max (~20-40s, guidance 3.5)
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

    # Quality mode: model + guidance scale
    if quality == "preview":
        model_id       = core.RENDER_MODEL_FAST
        guidance_scale = 2.5
        quality_note   = (
            "PREVIEW MODE: optimize for speed. Lower detail is acceptable."
        )
    else:
        model_id       = core.RENDER_MODEL
        guidance_scale = 3.5
        quality_note   = (
            "FULL RENDER MODE: maximum photorealism, full detail, no compromises. "
            "This is the final sales-ready image."
        )

    prompt = f"""Edit this room photograph: remove any existing window covering and install the specified Venetian blind photorealistically on the window. {quality_note}

ABSOLUTE PRODUCT RULES
Only install:
  Houten Jaloezieën
  Aluminium Jaloezieën
Never render:
  curtains, roller blinds, pleated blinds, Roman blinds, vertical blinds, any non-horizontal product

SCENE PRESERVATION — STRICT
  DO NOT repaint walls
  DO NOT recolor frames
  DO NOT change the floor
  DO NOT alter furniture
  DO NOT restyle the room
  ONLY remove old window coverings if visible — reconstruct the bare glass, frame, and outside view underneath
  ONLY insert the new blind
  The blind must look manufactured, mounted, and photographed in place — not composited or pasted

────────────────────────────────────────────────
ANALYSIS JSON (binding source of truth):
{analysis_block}
────────────────────────────────────────────────

STEP 1 — VIRTUAL DEMOLITION
Remove any existing curtain, roller blind, pleated blind, Roman blind, Venetian blind, \
vertical blind, or other window covering. Reconstruct the bare glass, frame, reveal, and \
outside view. The new blind must never sit on top of an existing one.

STEP 2 — MOUNTING GEOMETRY
{mounting_desc}

Never float the blind unrealistically, clip through frame geometry, block hardware \
impossibly, or ignore opening direction and handle clearance.

STEP 3 — PRODUCT SPECIFICATION
Product:       {product_desc}
Material:      {config.get('material', '')}
Color:         {config.get('colorName', '')} (exact hex: {config.get('colorHex', '')})
Configuration: {slat_desc}, {tape_desc}
State:         {state_desc}

Realism requirements:
  Slats perfectly horizontal and parallel, equidistant, realistic thickness
  Realistic headrail and bottom rail dimensions
  Realistic cord/tape geometry — if ladder tape: wide fabric strips aligned \
  consistently over slats, perspective-correct and physically attached
  Correct scale relative to the actual window size in the photo

STEP 4 — STATE LOGIC
{state_desc}
  Slats remain parallel and rhythmically consistent
  Daylight filters through slat gaps where physically appropriate
  Striped shadow behavior on floor/sill where physically correct

STEP 5 — LIGHTING PHYSICS
Condition: {lighting_desc}

Shadow rules:
  Inside mount: shadows fall inside the recess, on sill, and adjacent surfaces
  Outside mount: shadows fall across the wall and floor with correct drop direction
  Shadow direction and softness must match the specified lighting condition exactly

Material physics:
  Aluminium: subtle specular highlights, gentle room reflections, sleek metallic finish
  Wood: visible grain texture, matte/satin response, warm light absorption

STEP 6 — PERSPECTIVE AND DEPTH
  Match the room's vanishing point and perspective exactly
  Align the blind to the actual frame plane or wall plane in the photo
  Account for recess depth, frame edges, handles, sash lines, and occlusion
  Maintain correct depth hierarchy: wall → frame → glass → blind

STEP 7 — FINAL INTEGRATION
The output must show one coherent installed blind with preserved original architecture, \
believable interaction with light, correct depth and occlusion, and photorealistic \
integration — indistinguishable from a professional product photograph taken in the room.

FAIL CONDITIONS — output is wrong if:
  old coverings remain visible
  wall, frame, floor, or furniture are recolored or altered
  the blind floats or clips unrealistically
  product type, color, or material is wrong
  slats are misaligned or non-parallel
  shadows contradict the specified light source
  perspective is incorrect
  the blind looks like a flat layer pasted onto the photo
  the mounting type contradicts the analysis JSON""".strip()

    # Prepare image as data URI (fal.ai accepts base64 data URIs directly)
    mime_type, raw_b64 = _strip_data_url(image_b64)
    image_data_uri = f"data:{mime_type};base64,{raw_b64}"

    # Call fal.ai — fal_client reads FAL_KEY from environment automatically
    result = fal_client.subscribe(
        model_id,
        arguments={
            "image_url":      image_data_uri,
            "prompt":         prompt,
            "guidance_scale": guidance_scale,
            "num_images":     1,
            "output_format":  "jpeg",
        },
    )

    # Response contains a URL to the generated image — download and return as data URI
    output_url = result["images"][0]["url"]
    with urllib.request.urlopen(output_url) as resp:
        img_bytes = resp.read()

    return f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"


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
