"""
app.py — MRJ4.15 Flask Application
Mr. Jealousy Interior Intelligence Tool

Routes:
  GET  /           → serve static/index.html
  POST /analyze    → run phases 1-8 (Claude vision)
  POST /render     → run phase 9 (Gemini image generation)
"""

import os
import sys
import base64
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

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

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
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
            quality="full",  # Full HD render
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

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("API_KEY")
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
            quality="preview",  # Low-res preview
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

    # Quality mode guidance
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

ABSOLUTE PRODUCT RULES
Only render:
  Houten Jaloezieën
  Aluminium Jaloezieën
Never render:
  curtains, roller blinds, pleated blinds, Roman blinds, vertical blinds, any non-horizontal product

SCENE PRESERVATION RULES
  DO NOT repaint walls
  DO NOT recolor frames
  DO NOT change the floor
  DO NOT alter furniture
  DO NOT restyle the room
  ONLY remove old window coverings if visible
  ONLY insert the new blind
  Preserve all exposed architecture in original color/material
  Preserve outside view through open slats where visible

CRITICAL REALISM RULE
The blind must not look pasted on. It must look manufactured, mounted, and photographed in place.

────────────────────────────────────────────────
ANALYSIS JSON (treat as binding source of truth):
{analysis_block}
────────────────────────────────────────────────

STEP 1 — VIRTUAL DEMOLITION
Detect and fully remove any existing curtain, roller blind, pleated blind, Roman blind, \
Venetian blind, vertical blind, or other window covering.
Reconstruct the underlying glass, frame, reveal, and outside view.
The new blind must NEVER sit on top of an old one.

STEP 2 — USE JSON AS SOURCE OF TRUTH
Read the supplied analysis JSON as binding. Prioritize especially:
  windowCheck (obstacles, glass section count, opening mechanism, mounting recommendation, physical feasibility notes)
  selected suggestion (productType, material, colorName, colorHex)
  renderInstructions (all fields)
  colour_palette
  lightingConditions
Do not contradict the JSON unless the image makes a hard correction unavoidable.

STEP 3 — MOUNTING GEOMETRY
{mounting_desc}

Never:
  float the blind unrealistically
  clip through frame geometry
  block hardware in an impossible way
  ignore opening direction or handle clearance

STEP 4 — PRODUCT SPECIFICATION
Product:       {product_desc}
Material:      {config.get('material', '')}
Color:         {config.get('colorName', '')} (Hex: {config.get('colorHex', '')})
Configuration: {slat_desc}, {tape_desc}
State:         {state_desc}

Product realism requirements:
  slats perfectly horizontal and parallel
  equidistant spacing
  realistic slat thickness
  realistic headrail dimensions
  realistic bottom rail dimensions
  realistic cord/tape logic
  realistic scale relative to actual window size
  physically plausible full-drop geometry
  If ladder tape: render wide decorative vertical fabric tapes, aligned consistently over slats, \
perspective-correct and physically attached

STEP 5 — STATE LOGIC
{state_desc}
  slats remain parallel and perfectly aligned
  spacing is rhythmically consistent
  daylight may filter through slats if not in blackout-closed position
  create refined striped light behavior where physically appropriate

STEP 6 — LIGHTING PHYSICS
Condition: {lighting_desc}

Shadow rules:
  inside mount: shadows mainly inside the recess, on sill, and immediate adjacent surfaces
  outside mount: shadows can fall across wall and floor
  shadow direction must match actual light angle
  shadow softness must match selected lighting mode

Material rules:
  aluminium: subtle specular highlights, gentle room reflections, sleek finish
  wood: visible grain, matte/satin response, warmer absorption of light

STEP 7 — PERSPECTIVE AND DEPTH
  Match the room's vanishing point exactly
  Respect vertical and horizontal perspective
  Align blind to the actual frame plane or wall plane
  Account for recess depth and occlusion by frame edges, handles, sash lines, or recess returns
  Maintain correct depth hierarchy between blind, frame, glass, and wall

STEP 8 — FINAL INTEGRATION
The final image must show:
  one coherent installed blind
  original architecture preserved
  believable interaction with light
  believable depth and occlusion
  photorealistic integration without overlay look

FINAL OUTPUT GOAL
Produce a premium, believable, sales-ready visualization in which the blind looks truly \
installed in the photographed room.

FAIL CONDITIONS — render is invalid if:
  old coverings remain visible
  wall/frame/floor/furniture are recolored
  the blind floats
  the blind clips unrealistically
  product type is wrong
  slats are misaligned
  shadows contradict the light source
  perspective is off
  the blind looks like a flat pasted layer
  the render ignores mounting logic from the JSON
""".strip()

    # Decode image bytes for the Gemini API
    mime_type, raw_b64 = _strip_data_url(image_b64)
    img_bytes  = base64.b64decode(raw_b64)

    # Use the new google-genai SDK (google-generativeai is deprecated)
    client = genai.Client(api_key=api_key)

    image_part = genai_types.Part.from_bytes(data=img_bytes, mime_type=mime_type)

    # response_modalities=["IMAGE"] is mandatory — without it the model returns text only.
    response = client.models.generate_content(
        model=core.RENDER_MODEL,
        contents=[prompt, image_part],
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        ),
    )

    # Extract generated image from response parts
    if not response.candidates:
        raise ValueError("Geen candidates in Gemini response.")

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            mime = part.inline_data.mime_type
            data = part.inline_data.data
            return f"data:{mime};base64,{base64.b64encode(data).decode()}"

    raise ValueError("Geen afbeelding gegenereerd door Gemini.")


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
