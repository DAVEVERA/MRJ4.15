"""
src/AI/analyse_claude.py — MRJ4.15 Claude Vision Pipeline

Executes phases 1-8 sequentially using Claude's vision API.
Imports all laws and constants from core.py — never defines its own.

Phase gate:
  Phase 2 (quality check) can abort the pipeline early and return an error response.
  All other phases run in sequence and accumulate context.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import anthropic

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import core
from src.AI.utils import write_json_cache, strip_data_url

logger = logging.getLogger(__name__)


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
) -> str:
    """
    Send a single vision request to Claude.
    Automatically falls back to FALLBACK_MODEL if the primary model is overloaded.
    Returns the raw text response (expected to be JSON).
    """
    models_to_try = [core.ANALYSIS_MODEL, core.FALLBACK_MODEL]

    for model in models_to_try:
        try:
            if model != core.ANALYSIS_MODEL:
                logger.warning("claude-opus-4-6 overloaded — falling back to %s", model)

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
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
                raise ValueError(f"Empty response received from model {model}.")

            return response.content[0].text.strip()

        except (anthropic.InternalServerError, anthropic.RateLimitError):
            if model == core.FALLBACK_MODEL:
                raise  # both models overloaded — propagate
            continue   # try fallback

    # Unreachable, but satisfies type checkers
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
    raw    = _call_claude_vision(client, system, image_b64, image_mime, user)
    result = _parse_json(raw, phase=2)
    return {
        "passed":   bool(result.get("passed", False)),
        "feedback": result.get("feedback", ""),
    }



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
        result = {
            "qualityFailed":   True,
            "qualityFeedback": quality["feedback"],
        }
        write_json_cache(result)
        return result

    # ── PHASE 4: Color DNA ─────────────────────────────────────
    colors = _phase_4_colors(client, image_b64, image_mime)

    # ── PHASE 5: Window architecture ──────────────────────────
    window = _phase_5_window(client, image_b64, image_mime)

    # ── PHASE 6: Mounting strategy (pure logic) ────────────────
    mounting = _phase_6_mounting(window)

    # ── PHASE 7: Lighting conditions ───────────────────────────
    lighting = _phase_7_lighting(client, image_b64, image_mime)

    # ── PHASE 8: Catalog match ─────────────────────────────────
    context = {
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

    result = {
        "qualityFailed":       False,
        "lightingConditions":  lighting.get("lightingConditions", ""),
        "colour_palette":      colors.get("colour_palette", []),
        "windowCheck":         window_check,
        "materialSuggestions": catalog_match.get("materialSuggestions", []),
        "suggestions":         catalog_match.get("suggestions", []),
    }

    write_json_cache(result)
    return result
