"""
src/AI/analyse_claude.py — MRJ4.15 Claude Vision Pipeline

Executes phases 1-8 sequentially using Claude's vision API.
Imports all laws and constants from core.py — never defines its own.

Phase gate:
  Phase 2 (quality check) can abort the pipeline early and return an error response.
  Phases 3, 4, 5, 7 run concurrently (all image-only, mutually independent).
  Phase 8 runs after, using outputs of 3, 4 and 7 as context.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import anthropic
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core
from src.AI.utils import strip_data_url
from src.AI.sam2_segment import detect_window_bounds

logger = logging.getLogger(__name__)

_PROMPT_SEP = "─" * 60  # separator produced by core.get_phase_prompt() — used for cache split


# ── CLAUDE CLIENT ───────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


# ── VISION CALL ─────────────────────────────────────────────────

def _call_claude_vision(
    client: anthropic.Anthropic,
    system_prompt: str,
    image_b64: str,
    image_mime: str,
    user_message: str,
    model: Optional[str] = None,
) -> str:
    """
    Send a single vision request to Claude.
    - model=None  → uses ANALYSIS_MODEL (Opus) with FALLBACK_MODEL (Sonnet) on overload.
    - model=X     → uses X only, no fallback (for phases where Sonnet is sufficient).
    The static base of the system prompt is marked for prompt caching, which reduces
    token-processing overhead on repeated calls within the same session.
    Returns the raw text response (expected to be JSON).
    """
    models_to_try = [model] if model else [core.ANALYSIS_MODEL, core.FALLBACK_MODEL]

    # Split system prompt into cacheable static base and phase-specific suffix.
    # The separator line (─────) is the natural split point produced by get_phase_prompt().
    if _PROMPT_SEP in system_prompt:
        idx = system_prompt.index(_PROMPT_SEP)
        system_content: Any = [
            {
                "type": "text",
                "text": system_prompt[:idx].rstrip(),
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": system_prompt[idx:],
            },
        ]
    else:
        system_content = system_prompt  # fallback: plain string (e.g. phase 2 simple prompt)

    for m in models_to_try:
        try:
            if m != models_to_try[0]:
                logger.warning("%s overloaded — falling back to %s", models_to_try[0], m)

            response = client.messages.create(
                model=m,
                max_tokens=4096,
                system=system_content,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type":       "base64",
                                    "media_type": image_mime,
                                    "data":       image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": user_message,
                            },
                        ],
                    }
                ],
            )

            if not response.content:
                raise ValueError(f"Empty response received from model {m}.")

            return response.content[0].text.strip()

        except (anthropic.InternalServerError, anthropic.RateLimitError):
            if m == models_to_try[-1]:
                raise  # all options exhausted — propagate
            continue   # try next model

    raise RuntimeError("All models failed.")


def _parse_json(raw: str, phase: int = 0) -> Dict[str, Any]:
    """Strip markdown fences and parse JSON. Raises with phase context on failure."""
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        phase_label = f"phase {phase}" if phase else "unknown phase"
        raise ValueError(
            f"JSON parse error in {phase_label}: {exc}\n"
            f"Raw response (first 400 chars): {raw[:400]}"
        ) from exc


# ── PHASE EXECUTORS ─────────────────────────────────────────────

def _phase_2_quality(client, image_b64, image_mime) -> Dict[str, Any]:
    """
    Phase 2: Image quality and compliance check.
    Returns a dict with 'passed': bool and 'feedback': str.
    """
    system = core.get_phase_prompt(2)
    user   = (
        "Voer de kwaliteits- en compliancecheck uit op deze afbeelding. "
        "Geef je antwoord als geldig JSON object met de volgende structuur:\n"
        '{"passed": true/false, "feedback": "feedback tekst als failed, anders leeg string"}'
    )
    # Sonnet is voldoende voor deze binaire ja/nee check — sneller dan Opus.
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user,
                                 model=core.FALLBACK_MODEL)
    result = _parse_json(raw, phase=2)
    return {
        "passed":   bool(result.get("passed", False)),
        "feedback": result.get("feedback", ""),
    }


def _phase_3_style(client, image_b64, image_mime) -> Dict[str, Any]:
    """Phase 3: Extract interior thesis — style, mood, luxury level, material language."""
    system = core.get_phase_prompt(3)
    user   = (
        "Analyseer de interieurstijl van deze ruimte. "
        "Geef je antwoord als geldig JSON object:\n"
        '{"style": "één stijllabel (bijv. Japandi, Industrial, Hotel Chic)", '
        '"styleSummary": "Maximaal 2 zinnen.", '
        '"roomMood": "één woord of korte zin die de sfeer van de ruimte beschrijft"}'
    )
    raw = _call_claude_vision(client, system, image_b64, image_mime, user)
    return _parse_json(raw, phase=3)


def _phase_4_colors(client, image_b64, image_mime) -> Dict[str, Any]:
    """Phase 4: Extract color DNA (5 room tones)."""
    # Catalog is already embedded in the master prompt via get_phase_prompt().
    system = core.get_phase_prompt(4)
    user   = (
        "Extraheer precies 5 zichtbare kleuren uit de ruimte. "
        "Elk matched_catalog_color moet letterlijk in de catalogus hierboven staan. "
        "Geef je antwoord als geldig JSON object:\n"
        '{"colour_palette": ['
        '{"hex_code": "#XXXXXX", "extracted_source": "...", "matched_catalog_color": "..."}'
        ", ...]}"
    )
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user)
    return _parse_json(raw, phase=4)


def _phase_5_window(client, image_b64, image_mime) -> Dict[str, Any]:
    """Phase 5: Forensic window architecture analysis."""
    system = core.get_phase_prompt(5)
    user   = (
        "Voer een forensische raamanalyse uit. "
        "Geef je antwoord als geldig JSON object:\n"
        '{"windowType": "...", "detectedWindowCount": 1, "recessDepth": 10, '
        '"handlePresent": false, "handleSide": "...", "ventPresent": false, '
        '"openingMechanism": "...", "openingDirection": "...", "isOperable": true, '
        '"frameType": "...", "glazingType": "...", "stackHeightClearance": 0, '
        '"sillPresent": true, "cornerProximity": false, "collisionRisks": "...", '
        '"exceptions": "Max 1 concrete zin over afwijkingen die montage beïnvloeden, of lege string."}'
    )
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user)
    return _parse_json(raw, phase=5)


def _phase_6_mounting(window_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 6: Determine mounting strategy from window data.
    Pure logic — no Claude call needed. Applies the 5 rules from core.PHASE_LAWS[6].
    """
    recess_depth     = float(window_data.get("recessDepth", 0))
    handle_present   = bool(window_data.get("handlePresent", False))
    vent_present     = bool(window_data.get("ventPresent", False))
    window_type      = str(window_data.get("windowType", "")).lower()
    opening_dir      = str(window_data.get("openingDirection", "")).lower()
    stack_clearance  = float(window_data.get("stackHeightClearance", 999))
    corner_proximity = bool(window_data.get("cornerProximity", False))
    obstacle         = handle_present or vent_present

    # Rule 1: depth threshold
    if recess_depth < 5:
        return {"recommendation": "op de dag", "rule": "RULE_1_DEPTH",
                "reasoning": f"Recess diepte {recess_depth}cm < 5cm: buitenbevestiging verplicht."}

    # Rule 2: protrusion & clearance
    if obstacle:
        if recess_depth <= 15:
            return {"recommendation": "in de dag", "rule": "RULE_2_PROTRUSION_FRONT",
                    "reasoning": "Obstakel aanwezig; montage op voorste rand van het dagvlak."}
        return {"recommendation": "op de dag", "rule": "RULE_2_PROTRUSION_OUTSIDE",
                "reasoning": "Obstakel aanwezig en recess te diep; buitenbevestiging verplicht."}

    # Rule 3: kinematic collision (tilt & turn)
    is_tilt_turn = "tilt" in window_type or "draai" in window_type or "inward" in opening_dir
    if is_tilt_turn:
        if stack_clearance < 20:
            return {"recommendation": "op de dag", "rule": "RULE_3_KINEMATIC",
                    "reasoning": "Kiepbeweging vereist extra stapelruimte; buitenbevestiging verplicht."}

    # Rule 4: lateral collision
    if corner_proximity:
        return {"recommendation": "op de dag", "rule": "RULE_4_LATERAL",
                "reasoning": "WAARSCHUWING: Onvoldoende zijdelingse ruimte voor overlap; check hoekbotsing.",
                "error": True}

    # Rule 5: default
    return {"recommendation": "in de dag", "rule": "RULE_5_DEFAULT",
            "reasoning": "Alle regels groen: binnenbevestiging 10mm vanaf de wandrand (schaduwnaad)."}


def _phase_7_lighting(client, image_b64, image_mime) -> Dict[str, Any]:
    """Phase 7: Lighting conditions analysis."""
    system = core.get_phase_prompt(7)
    user   = (
        "Analyseer de lichtomstandigheden in deze ruimte. "
        "Geef je antwoord als geldig JSON object:\n"
        '{"lightDirection": "...", "lightIntensity": "...", "lightSoftness": "...", '
        '"lightTemperature": "...", "naturalContribution": 80, "artificialContribution": 20, '
        '"glassReflection": "...", "shadowBehavior": "...", '
        '"recommendedMaterial": "Houten Jaloezieën of Aluminium Jaloezieën", '
        '"lightingConditions": "samenvatting in één zin"}'
    )
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user)
    return _parse_json(raw, phase=7)


def _phase_8_catalog(client, image_b64, image_mime, context: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 8: Catalog match — select best products from the catalog."""
    # Catalog is already embedded in the master prompt via get_phase_prompt().
    style_ctx    = context.get("style", "")
    mood_ctx     = context.get("roomMood", "")
    palette_ctx  = json.dumps(context.get("colour_palette", []), ensure_ascii=False)
    material_rec = context.get("recommendedMaterial", "")

    system = core.get_phase_prompt(8)
    user   = (
        f"Interieurstijl: {style_ctx}\n"
        f"Sfeer: {mood_ctx}\n"
        f"Kleurenpalet: {palette_ctx}\n"
        f"Aanbevolen materiaal op basis van licht: {material_rec}\n\n"
        "Selecteer de 3 beste overeenkomende producten uit de catalogus. "
        "ALLEEN producten die letterlijk in de catalogus staan. "
        "Geef je antwoord als geldig JSON object:\n"
        '{"materialSuggestions": ["Hout", "Aluminium"], "suggestions": ['
        '{"productType": "...", "material": "...", "colorName": "...", '
        '"colorHex": "#XXXXXX", "suitabilityScore": 10, "reasoning": "..."}'
        ", ...]}"
    )
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user)
    return _parse_json(raw, phase=8)


# ── MAIN PIPELINE ───────────────────────────────────────────────

def run_analysis_pipeline(image_data_url: str) -> Dict[str, Any]:
    """
    Execute phases 1-8 sequentially.
    Phase 1: handled by the caller (upload to Supabase, pass base64 here).
    Phase 2: quality gate — returns error dict immediately if image fails.
    Phases 3-8: run in order, accumulating context.

    Returns an AnalysisResult-compatible dict.
    """
    client = _get_client()
    image_mime, image_b64 = strip_data_url(image_data_url)

    # ── PHASE 2: Quality gate ──────────────────────────────────
    quality = _phase_2_quality(client, image_b64, image_mime)
    if not quality["passed"]:
        return {
            "qualityFailed":   True,
            "qualityFeedback": quality["feedback"],
        }

    # ── PHASES 3, 4, 5, 7 + SAM2: run concurrently ──────────
    # All four Claude phases only need the image and are mutually independent.
    # SAM2 runs in the same pool — it's GPU/CPU bound so it overlaps fine
    # with the network-bound Claude calls.
    with ThreadPoolExecutor(max_workers=5) as executor:
        f3   = executor.submit(_phase_3_style,    client, image_b64, image_mime)
        f4   = executor.submit(_phase_4_colors,   client, image_b64, image_mime)
        f5   = executor.submit(_phase_5_window,   client, image_b64, image_mime)
        f7   = executor.submit(_phase_7_lighting, client, image_b64, image_mime)
        fsam = executor.submit(detect_window_bounds, image_data_url)
        style    = f3.result()
        colors   = f4.result()
        window   = f5.result()
        lighting = f7.result()
        sam      = fsam.result()

    # ── PHASE 6: Mounting strategy (pure logic, no API call) ──
    mounting = _phase_6_mounting(window)

    # ── PHASE 8: Catalog match ─────────────────────────────────
    context = {
        "style":               style.get("style", ""),
        "roomMood":            style.get("roomMood", ""),
        "colour_palette":      colors.get("colour_palette", []),
        "recommendedMaterial": lighting.get("recommendedMaterial", ""),
    }
    catalog_match = _phase_8_catalog(client, image_b64, image_mime, context)

    # ── Assemble final result ──────────────────────────────────
    window_check = {
        "obstacles":             window.get("handlePresent", False) or window.get("ventPresent", False),
        "windowType":            window.get("windowType", "—"),
        "detectedWindowCount":   window.get("detectedWindowCount", 1),
        "recommendation":        mounting.get("recommendation", "in de dag"),
        "reasoning":             mounting.get("reasoning", ""),
        "specialConsiderations": window.get("exceptions", ""),
    }

    # SAM2 window region — mask drives the SDXL inpaint, bounds are metadata
    window_bounds = None
    window_mask_b64 = None
    if sam.get("success"):
        window_bounds = sam["bounds"]
        window_bounds["confidence"] = sam.get("confidence", 0.0)
        window_mask_b64 = sam.get("mask_b64")
    else:
        logger.warning("SAM2 detection failed: %s", sam.get("error", "unknown"))

    result = {
        "qualityFailed":       False,
        "style":               style.get("style", ""),
        "styleSummary":        style.get("styleSummary", ""),
        "roomMood":            style.get("roomMood", ""),
        "lightingConditions":  lighting.get("lightingConditions", ""),
        "colour_palette":      colors.get("colour_palette", []),
        "windowCheck":         window_check,
        "windowBounds":        window_bounds,
        "windowMask":          window_mask_b64,
        "materialSuggestions": catalog_match.get("materialSuggestions", []),
        "suggestions":         catalog_match.get("suggestions", []),
    }

    return result
