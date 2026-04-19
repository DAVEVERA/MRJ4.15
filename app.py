"""
app.py — MRJ4.15 Flask Application
Mr. Jealousy Interior Intelligence Tool

Routes:
  GET  /           → serve static/index.html
  POST /analyze    → run phases 1-8 (Claude vision + SAM2 segmentation)
  POST /render     → full SDXL inpaint render
  POST /preview    → fast SDXL inpaint preview
"""

import os
import sys
from pathlib import Path

import io
from flask import Flask, request, jsonify, send_from_directory, send_file, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.AI.analyse_claude import run_analysis_pipeline
from src.AI.utils import save_upload_locally, upload_to_supabase
from src.AI.sam2_segment import detect_window_bounds
from src.AI.render_gemini import generate_decor
from src.AI.render_blind import render_blind_panel
from src.AI.warp_blind import (
    find_window_corners, warp_blind_to_window,
    composite_over_photo, b64_to_pil, mask_b64_to_array,
    pil_to_b64_jpeg, draw_corner_debug,
    clean_mask, apply_lighting,
)


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

    try:
        upload_to_supabase(image_b64)
    except Exception as exc:
        app.logger.warning("Supabase upload failed (non-critical): %s", exc)

    try:
        save_upload_locally(image_b64)
    except Exception as exc:
        app.logger.warning("Local save failed (non-critical): %s", exc)

    try:
        result = run_analysis_pipeline(image_b64)
        return jsonify(result)
    except Exception as exc:
        app.logger.error("Pipeline error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


# ── PHASE 9: RENDER (procedural blind + SAM2 mask + perspective warp) ──

@app.route("/render", methods=["POST"])
def render():
    return _do_render()


@app.route("/preview", methods=["POST"])
def preview():
    return _do_render()


def _do_render():
    """
    Gemini visualization pipeline (port of MRJ415 generateDecor).
    Sends the room photo + structured prompt to gemini-2.5-flash-image
    and returns the inpainted result.
    """
    data      = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    config    = data.get("config", {})
    state     = data.get("state", "Tot de helft")
    extra     = data.get("extraOptions", {})
    analysis  = data.get("analysis") or {}

    if not image_b64 or not config:
        return jsonify({"error": "Ontbrekende parameters."}), 400

    mounting = (analysis.get("windowCheck") or {}).get("recommendation") or "in de dag"

    try:
        image_url = generate_decor(
            image_b64=image_b64,
            config=config,
            state=state,
            mounting=mounting,
            extra_options=extra,
        )
        return jsonify({"image": image_url})
    except Exception as exc:
        app.logger.error("Render error: %s", exc, exc_info=True)
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500


# ── SAM2 CONFIGURATOR (warp + composite test) ──────────────────

_TEST_WARP_HTML = """<!doctype html>
<html lang="nl"><head><meta charset="utf-8"><title>Warp + Composite — Test</title>
<style>
  body { font-family:-apple-system,sans-serif; background:#222; color:#eee;
         margin:0; padding:20px; }
  .row { display:flex; gap:20px; align-items:flex-start; }
  .col { flex:1; }
  .panel { background:#333; padding:16px; border-radius:8px; }
  label { display:block; margin:8px 0 4px; font-size:12px; color:#aaa; }
  input, select { width:100%; padding:6px; background:#1a1a1a; color:#eee;
                  border:1px solid #555; border-radius:4px; box-sizing:border-box; }
  button { margin-top:12px; padding:10px 16px; background:#4a7; color:#fff;
           border:0; border-radius:4px; cursor:pointer; font-weight:600; }
  button:disabled { background:#555; cursor:wait; }
  img { max-width:100%; display:block; border:1px solid #444; border-radius:4px; }
  .imgs { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; }
  .imgs figure { margin:0; }
  .imgs figcaption { font-size:12px; color:#888; padding:4px 0; }
  h1 { margin:0 0 12px; font-size:18px; }
  #status { font-size:13px; color:#fc6; margin-top:8px; min-height:18px; }
</style></head><body>
<div class="row">
  <div class="col panel" style="max-width:340px;">
    <h1>Warp + Composite</h1>
    <label>Foto (jpg/png)</label>
    <input id="file" type="file" accept="image/*">

    <label>Color hex</label>
    <input id="colorHex" value="#9c8b7a">

    <label>Product type</label>
    <select id="productType">
      <option>Houten Jaloezieën</option>
      <option>Aluminium Jaloezieën</option>
    </select>

    <label>Slat width</label>
    <select id="slatWidth"><option>50mm</option><option>25mm</option></select>

    <label>State</label>
    <select id="state">
      <option>Tot de helft</option>
      <option>Geheel uitgerold</option>
    </select>

    <label>Ladder</label>
    <select id="ladderTape"><option value="true">Ladderband</option><option value="false">Ladderkoord</option></select>

    <label>Window height (mm) — voor slat-density</label>
    <input id="windowHeightMm" type="number" value="1400">

    <button id="go">Run SAM2 + Render + Warp</button>
    <div id="status"></div>
  </div>

  <div class="col">
    <div class="imgs">
      <figure><figcaption>Origineel</figcaption><img id="orig"></figure>
      <figure><figcaption>SAM2 mask + 4 corners</figcaption><img id="dbg"></figure>
      <figure><figcaption>Warped blind (alleen jaloezie)</figcaption><img id="warped"></figure>
      <figure><figcaption>Final composite</figcaption><img id="final"></figure>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);

function fileToB64(f) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(f);
  });
}

$('go').onclick = async () => {
  const f = $('file').files[0];
  if (!f) { $('status').textContent = 'Kies eerst een foto.'; return; }
  $('go').disabled = true;
  $('status').textContent = 'Bezig… (SAM2 ~5s eerste keer)';

  const image = await fileToB64(f);
  $('orig').src = image;

  const body = {
    image,
    config: { colorHex: $('colorHex').value, productType: $('productType').value },
    state:  $('state').value,
    extra:  { slatWidth: $('slatWidth').value, ladderTape: $('ladderTape').value === 'true' },
    windowHeightMm: parseFloat($('windowHeightMm').value) || 1400,
  };

  try {
    const r = await fetch('/test_warp', {
      method: 'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (data.error) { $('status').textContent = 'FOUT: ' + data.error; return; }
    $('dbg').src    = data.debug;
    $('warped').src = data.warped;
    $('final').src  = data.final;
    $('status').textContent = 'Klaar. Corners: ' + JSON.stringify(data.corners);
  } catch (e) {
    $('status').textContent = 'FOUT: ' + e.message;
  } finally {
    $('go').disabled = false;
  }
};
</script>
</body></html>"""


@app.route("/test_warp_page")
def test_warp_page():
    return render_template_string(_TEST_WARP_HTML)


@app.route("/test_warp", methods=["POST"])
def test_warp():
    """End-to-end: photo → SAM2 → corners → procedural blind → warp → composite."""
    data = request.get_json(silent=True) or {}
    image_b64 = data.get("image")
    if not image_b64:
        return jsonify({"error": "Geen afbeelding ontvangen."}), 400

    config   = data.get("config", {})
    state    = data.get("state", "Tot de helft")
    extra    = data.get("extra", {})
    win_mm   = float(data.get("windowHeightMm", 1400))

    try:
        # 1. SAM2
        sam = detect_window_bounds(image_b64)
        if not sam.get("success"):
            return jsonify({"error": f"SAM2 mislukt: {sam.get('error')}"}), 500

        mask_arr = mask_b64_to_array(sam["mask_b64"])

        # 1b. Clean the mask: opening (erode→dilate) drops protrusions like
        #     windowsill bumps and mullion stubs that would inflate the bbox,
        #     then a final dilate extends onto the kozijn edge.
        mask_arr = clean_mask(mask_arr, open_px=18, dilate_px=14)

        corners  = find_window_corners(mask_arr)

        photo   = b64_to_pil(image_b64).convert("RGB")
        photo_w, photo_h = photo.size

        # 2. Pick a render size = bbox of the corners (preserves pixel density)
        xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
        target_w = max(64, max(xs) - min(xs))
        target_h = max(64, max(ys) - min(ys))

        # 3. Render front-on blind
        blind = render_blind_panel(
            width_px=target_w, height_px=target_h,
            config=config, state=state, extra=extra,
            window_height_mm=win_mm,
        )

        # 4. Warp to the window quad
        warped = warp_blind_to_window(blind, corners, (photo_w, photo_h))

        # 5. Light integration: modulate blind by photo brightness behind it
        warped_lit = apply_lighting(warped, photo, blur_px=25, strength=0.55)

        # 6. Composite
        final = composite_over_photo(photo, warped_lit)

        # 7. Debug overlay
        dbg = draw_corner_debug(photo, corners)

        return jsonify({
            "corners":  corners,
            "debug":    pil_to_b64_jpeg(dbg, quality=85),
            "warped":   pil_to_b64_jpeg(warped_lit, quality=88),
            "final":    pil_to_b64_jpeg(final, quality=92),
        })
    except Exception as exc:
        app.logger.error("test_warp error: %s", exc, exc_info=True)
        return jsonify({"error": f"{type(exc).__name__}: {exc}"}), 500


# ── ENTRYPOINT ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
