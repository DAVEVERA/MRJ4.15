"""
core.py — The Quiet Engine
MRJ4.15 | Mr. Jealousy Interior Intelligence System

This file is the single source of truth for all phase laws, the product catalog,
descriptor maps, response schemas, and system constants. It defines — it never executes.
Every other module in this project imports from here. Nothing runs inside core.py itself.
"""

from typing import TypedDict, List, Dict, Any, Optional


# ── TYPE DEFINITIONS ───────────────────────────────────────────────────────────

class ProductColor(TypedDict):
    name: str
    hex: str
    material: str
    sampleUrl: str
    galleryUrls: Optional[List[str]]


class ColourPaletteEntry(TypedDict):
    hex_code: str
    extracted_source: str
    matched_catalog_color: str


class WindowCheck(TypedDict):
    obstacles: bool
    windowType: str
    detectedWindowCount: int
    recommendation: str
    reasoning: str
    specialConsiderations: str


class ProductSuggestion(TypedDict):
    productType: str
    material: str
    colorName: str
    colorHex: str
    suitabilityScore: int
    reasoning: str


class AnalysisResult(TypedDict):
    style: str
    styleSummary: str
    styleDescription: str
    roomMood: str
    lightingConditions: str
    colour_palette: List[ColourPaletteEntry]
    windowCheck: WindowCheck
    materialSuggestions: List[str]
    suggestions: List[ProductSuggestion]


class RenderInstruction(TypedDict):
    product_type: str
    color_name: str
    hex_code: str
    mount_type: str
    window_sections: int
    lighting_condition: str
    state: str
    slat_width: Optional[str]
    ladder_tape: bool
    scene_description: str
    negative_prompt: str
    camera_angle: str
    room_context: str


# ── SYSTEM CONSTANTS ───────────────────────────────────────────────────────────

PHASE_COUNT       = 9
ANALYSIS_MODEL    = "claude-opus-4-6"
FALLBACK_MODEL    = "claude-sonnet-4-6"
RENDER_MODEL      = "gemini-2.5-flash-image-preview"   # full render — preview variant of the image model
RENDER_MODEL_FAST = "gemini-2.5-flash-image"           # preview — production image model
UPLOAD_PATH       = "data/uploads"
SUPABASE_BUCKET   = "uploads"


# ── PRODUCT RULES ──────────────────────────────────────────────────────────────

ALLOWED_PRODUCT_TYPES: List[str] = [
    "Aluminium Jaloezieën",
    "Houten Jaloezieën",
]

ALLOWED_WOODEN_SUBTYPES: List[str] = [
    "Paulownia",
    "Bamboo",
    "Abachi",
]

FORBIDDEN_PRODUCT_TYPES: List[str] = [
    "Verticale lamellen",
    "Gordijnen",
    "Vouwgordijnen",
    "Plisségordijnen",
    "Rolgordijnen",
]

MOUNT_LABELS: Dict[str, str] = {
    "inside":  "in de dag",
    "outside": "op de dag",
    "sash":    "op de glaslat",
}


# ── MR. JEALOUSY CATALOG ───────────────────────────────────────────────────────

MR_JEALOUSY_CATALOG: Dict[str, List[ProductColor]] = {
    "Aluminium Jaloezieën": [
        {"name": "Like RAL9002",      "hex": "#E9E5CE", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Like-RAL9002%20A.png"},
        {"name": "Like RAL9010",      "hex": "#F7F9EF", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Like-RAL9010%20A.png"},
        {"name": "Moody Munt",        "hex": "#98FF98", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Moody-Munt%20A.png"},
        {"name": "Naughty Aubergine", "hex": "#472C4C", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Naughty-Aubergine%20A.png"},
        {"name": "Oud Green",         "hex": "#8F9779", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Oud-Green%20A.png"},
        {"name": "Peachy Pink",       "hex": "#FFDAB9", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Peachy-Pink%20A.png"},
        {"name": "Poolside Blue",     "hex": "#00BFFF", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Poolside-Blue%20A.png"},
        {"name": "Purple Grey",       "hex": "#6D6875", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Purple-Grey%20A.png"},
        {"name": "Rocky Rood",        "hex": "#8B0000", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Rocky-Rood%20A.png"},
        {"name": "Rusty Retro",       "hex": "#B7410E", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Rusty-Retro%20A.png"},
        {"name": "Silk Zwart",        "hex": "#050505", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Silk-Zwart%20A.png"},
        {"name": "Skinny Dip",        "hex": "#F4C2C2", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Skinny-Dip%20A.png"},
        {"name": "Smokey Grey",       "hex": "#708090", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Smokey-Grey%20A.png"},
        {"name": "Soft Naakt",        "hex": "#E3BC9A", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Soft-Naakt%20A.png"},
        {"name": "Soft Terra",        "hex": "#E2725B", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Soft-Terra%20A.png"},
        {"name": "Stevig Taupe",      "hex": "#483C32", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Stevig-Taupe%20A.png"},
        {"name": "Stormy Taupe",      "hex": "#5C5552", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Stormy-Taupe%20A.png"},
        {"name": "Twijfel Taupe",     "hex": "#876C5E", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Twijfel-Taupe%20A.png"},
        {"name": "Velvet Brown",      "hex": "#4B3621", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Velvet-Brown%20A.png"},
        {"name": "Bold Bruin",        "hex": "#654321", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Bold-Bruin%20A.png"},
        {"name": "Butter Geel",       "hex": "#F3E5AB", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Butter-Geel%20A.png"},
        {"name": "Cherry Pop",        "hex": "#D2042D", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Cherry-Pop%20A.png"},
        {"name": "Cool Grey",         "hex": "#A9A9A9", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Cool-Grey%20A.png"},
        {"name": "Cosmic Blauw",      "hex": "#000080", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Cosmic-Blauw%20A.png"},
        {"name": "Crazy Karamel",     "hex": "#C68E17", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Crazy-Karamel%20A.png"},
        {"name": "Drop Zwart",        "hex": "#1A1A1A", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Drop-Zwart%20A.png"},
        {"name": "Fluffy Naakt",      "hex": "#F5DEB3", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Fluffy-Naakt%20A.png"},
        {"name": "Brushed Nikkel",    "hex": "#B0C4DE", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Geborsteld-Nikkel%20A.png"},
        {"name": "Koffie Koper",      "hex": "#B87333", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Koffie-Koper%20A.png"},
        {"name": "Glitter Gold",      "hex": "#FFD700", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Glitter-Gold%20A.png"},
        {"name": "Goed Grijs",        "hex": "#808080", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Goed-Grijs%20A.png"},
        {"name": "Jet Black",         "hex": "#050505", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Jet-Black%20A.png"},
        {"name": "Juicy Olive",       "hex": "#808000", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Juicy-Olive%20A.png"},
        {"name": "Koel Blue",         "hex": "#AEC6CF", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Koel-Blue%20A.png"},
        {"name": "Like RAL9001",      "hex": "#FDF4E3", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Like-RAL9001%20A.png"},
        {"name": "Cowboy Koper",      "hex": "#8B4513", "material": "Aluminium", "sampleUrl": "https://storage.googleapis.com/mrjealousy/ALUMINIUM%20JALOEZIE/COWBOY%20KOPER/ALU_7381_Cowboy-Koper_BRUSHED_DA.jpeg"},
    ],
    "Houten Jaloezieën": [
        {"name": "Like RAL9016",    "hex": "#F0F8FF", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Like-RAL9016%20A.png"},
        {"name": "Mister Sandman",  "hex": "#C2B280", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Mister-Sandman.png"},
        {"name": "Misty Bamboo",    "hex": "#DCC098", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Misty-Bamboo.png"},
        {"name": "Oak Mooi",        "hex": "#C3A376", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Oak-Mooi.png"},
        {"name": "Parel White",     "hex": "#F5F5F5", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Parel-White.png"},
        {"name": "Shades of Grey",  "hex": "#808080", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Shades-of-Grey.png"},
        {"name": "Smokey Taupe",    "hex": "#9E958C", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Smokey-Taupe.png"},
        {"name": "Teder Taupe",     "hex": "#D8CCBB", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Teder-Taupe.png"},
        {"name": "Tiki Taupe",      "hex": "#A69686", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Tiki-Taupe.png"},
        {"name": "BBQ Black",       "hex": "#111111", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/BBQ-Black.png"},
        {"name": "Behoorlijk Black","hex": "#222222", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Behoorlijk-Black.png"},
        {"name": "Bonsai Bamboo",   "hex": "#6B8E23", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Bonsai_Bamboo.png"},
        {"name": "Bourbon Bamboo",  "hex": "#654321", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Bourbon-Bamboo.png"},
        {"name": "De Naturist",     "hex": "#D2B48C", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/De-Naturist.png"},
        {"name": "Donker Brown",    "hex": "#3B2F2F", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Donker-Brown.png"},
        {"name": "Eigenlijk Eiken", "hex": "#A0785A", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Eigenlijk-Eiken.png"},
        {"name": "Flat White",      "hex": "#FFFAF0", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Flat-White.png"},
        {"name": "Gebroken White",  "hex": "#FDF5E6", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Gebroken-White.png"},
        {"name": "Haver Milk",      "hex": "#EFEBD8", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/COLOR%20SAMPLES/Haver-Milk.png"},
        {"name": "Smokey Bamboo",   "hex": "#4A4A4A", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/HOUTEN%20JALOEZIE/SMOKEY%20BAMBOO/BAMBOE-JALOEZIE_5077_GRANITE_0fc56d7f-.jpeg"},
        {"name": "Deep Zwart",      "hex": "#080808", "material": "Hout", "sampleUrl": "https://storage.googleapis.com/mrjealousy/HOUTEN%20JALOEZIE/DEEP%20ZWART/HOUTEN-JALOEZIE_BLACK_04686c36-330d-4935-.jpeg"},
    ],
}


# ── DESCRIPTOR MAPS (migrated verbatim from TypeScript) ────────────────────────


MOUNTING_MAP: Dict[str, str] = {
    "in de dag": (
        "**MOUNTING TYPE: INSIDE MOUNT (In de dag)**\n"
        "1. GEOMETRY: The blind fits STRICTLY BETWEEN the window reveals (jambs).\n"
        "2. WALL PRESERVATION: The wall surface, architraves, and trim AROUND the window "
        "must remain COMPLETELY VISIBLE. Do NOT cover the casing.\n"
        "3. DEPTH: The blind is recessed into the wall.\n"
        "4. SHADOWS: Shadows from the slats fall onto the glass or the side reveals of "
        "the niche, NOT on the outer wall."
    ),
    "op de dag": (
        "**MOUNTING TYPE: OUTSIDE MOUNT (Op de dag)**\n"
        "1. GEOMETRY: The blind is mounted ON THE FACE of the wall, overlapping the "
        "window opening.\n"
        "2. OVERLAP: The blind must extend 10cm beyond the window opening on Left, Right, "
        "and Top.\n"
        "3. OBSCURING: The blind MUST physically cover the window frame/architraves.\n"
        "4. 3D LAYERING: The blind sits PROUD (forward) from the wall. You MUST render a "
        "hard drop shadow BEHIND the headrail and slats onto the wall surface.\n"
        "5. NO RECOLORING: Do not change the color of the wall or the frame underneath. "
        "The blind is a separate object placed in front."
    ),
    "op de glaslat": (
        "**MOUNTING TYPE: ON THE SASH (Op de glaslat)**\n"
        "1. PLACEMENT: Mounted directly onto the window sash (the moving part).\n"
        "2. FIT: Very tight fit against the glass. The handle remains visible and accessible."
    ),
    "Gebogen gordijnrail voor erker": "on a curved curtain rail for a bay window",
    "Speciaal dakraam product":       "in a special skylight blind system",
    "Twee aparte rolgordijnen voor hoekraam": "as two separate blinds for the corner window",
}

LIGHTING_MAP: Dict[str, str] = {
    "Ochtend (Koel)": (
        "MORNING LIGHT. Low angle sunlight from the East. Color Temp: 5500K (Cool/Fresh). "
        "Shadows: Long, crisp shadows projected deep into the room. Atmosphere: Crisp, energetic."
    ),
    "Middag (Helder)": (
        "MID-DAY SUN. High angle overhead sunlight. Color Temp: 6000K (Neutral White). "
        "Shadows: Short, sharp, high-contrast shadows on the window sill and floor. "
        "Atmosphere: Bright, clear, revealing."
    ),
    "Zonsondergang (Warm)": (
        "GOLDEN HOUR. Very low angle sunlight from the West. Color Temp: 3500K (Warm/Orange/Gold). "
        "Shadows: Extremely long, dramatic, stretching across the floor. "
        "Reflections: Warm metallic glow on slats. Atmosphere: Cozy, romantic."
    ),
    "Avond (Sfeervol)": (
        "EVENING/NIGHT. No direct sunlight. Light Source: Artificial interior lamps "
        "(Warm White 2700K). Shadows: Soft, multi-directional from room lights. "
        "Reflections: Interior room reflected in the glass. Atmosphere: Intimate, dark outside."
    ),
    "Bewolkt (Diffuus)": (
        "OVERCAST/CLOUDY. Diffuse, soft white light (6500K). No hard direct sunlight. "
        "Shadows: Very soft, ambient occlusion only, no hard projection. "
        "Atmosphere: Soft, even, calm."
    ),
}

PRODUCT_MAP: Dict[str, str] = {
    "Houten Jaloezieën": (
        "Premium Wooden Horizontal Venetian Blinds. "
        "Material physics: Matte or Satin finish, visible wood grain texture, "
        "absorbs light, warm reflections."
    ),
    "Aluminium Jaloezieën": (
        "Sleek Aluminum Horizontal Venetian Blinds. "
        "Material physics: Smooth metallic finish, slight specular highlights, "
        "reflects light, cool/sharp reflections."
    ),
}

STATE_MAP: Dict[str, str] = {
    "Tot de helft": (
        "KANTELSTAND: HALF OPEN. "
        "The blind is fully lowered (bottom rail hangs at sill level). "
        "Slat angle: exactly 45° tilt — each slat is angled so you can see daylight and the outside "
        "view through the gaps between slats. "
        "Visible result: clear alternating light/dark horizontal bands across the entire blind. "
        "The gaps between slats must be clearly visible. "
        "DO NOT render slats as fully closed or flat — they must be visibly tilted at 45°."
    ),
    "Geheel uitgerold": (
        "KANTELSTAND: VOLLEDIG GESLOTEN. "
        "The blind is fully lowered (bottom rail hangs at sill level). "
        "Slat angle: completely horizontal/flat — slats are rotated to fully overlap each other, "
        "blocking all view and light. "
        "Visible result: tight, uniform rows of parallel horizontal slats with no visible gaps. "
        "The blind surface looks solid and opaque. "
        "DO NOT render any gaps or light passing through — slats are fully closed."
    ),
}


# ── MASTER PROMPT ──────────────────────────────────────────────────────────────
#
# PROMPT 1 — ANALYSIS / DECISION PROMPT
# This is the single source of truth for all identity, laws, rules, and
# forbidden behaviors. Every phase prompt is built on top of this foundation.
# The placeholder [CATALOG] is replaced at runtime with the full catalog text.
#
MASTER_PROMPT = """\
You are a World-Class Interior Vision Architect, Window Treatment Surveyor, Product Configurator, \
and Lighting Physicist with elite computer vision precision.
You specialize exclusively in high-end horizontal Venetian blinds for Mr. Jealousy.

MISSION
Analyse the uploaded room image with forensic, pixel-level precision and return one technically \
correct, catalog-locked, installation-aware JSON object that can be used by a separate rendering \
model to place the blind photorealistically onto the window.

You are not a general interior assistant. You operate as a combined:
- interior architect
- blind installer
- window surveyor
- material and color analyst
- lighting physicist
- catalog-matching expert
- visualization planner

ABSOLUTE PRODUCT LOCK
You may ONLY use products that literally exist in the Mr. Jealousy catalog below.

ONLY ALLOWED:
  Houten Jaloezieën
  Aluminium Jaloezieën
  Allowed wooden subtypes only: Paulownia, Bamboo, Abachi

STRICTLY FORBIDDEN:
  Verticale lamellen
  Gordijnen
  Vouwgordijnen
  Plisségordijnen
  Rolgordijnen
  Any other non-horizontal product
  Invented products
  Invented materials
  Invented colors not present in the catalog
  Invented finish names
  Free interpretation outside the catalog

GOLDEN RULE
A beautiful recommendation that cannot exist physically is a failed result.

PRIMARY PRIORITIES
1. physical correctness
2. mounting correctness
3. catalog truth
4. window geometry correctness
5. perspective realism planning
6. style harmony
7. commercial relevance

CORE RULE
Do not treat the window as a flat rectangle. Treat it as a functional architectural object with:
  frame depth, glass sections, sash logic, hardware, reveal geometry, sill,
  opening motion, mounting constraints, obstacle zones, light interaction.

MR. JEALOUSY CATALOG (AUTHORITATIVE — DO NOT INVENT OUTSIDE THIS LIST):
[CATALOG]

OUTPUT OBLIGATION
Return ONLY valid JSON in Dutch. No markdown. No code fences. No explanation before or after.
TONE OF VOICE: Be extremely concise, punchy, and highly professional. Avoid all poetic language, fluff, and long essays. Write crisp, commercial copy suitable for a high-end web configurator UI. Maximum 1-2 short sentences per text field unless strictly specified otherwise.

FAIL CONDITIONS — output is wrong if:
  - it suggests a non-catalog product
  - it uses a non-catalog color
  - it invents materials
  - it ignores visible handles/vents/locks
  - it ignores recess depth logic
  - it fails to count glass sections
  - it gives generic style commentary
  - it outputs invalid JSON
  - it outputs anything other than Dutch JSON
  - it prioritizes beauty over feasibility
  - it treats the window as a flat decorative area instead of a functional architectural object
"""


# ── PHASE LAWS ─────────────────────────────────────────────────────────────────

PHASE_LAWS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "IMAGE_UPLOAD",
        "laws": [
            "Upload the image to Supabase simultaneously with triggering analyse_claude.py.",
            "All applicable laws are chronologically ordered and mandatory to follow.",
            "You may not self-interpret. Laws are given; you must obey.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    2: {
        "name": "IMAGE_QUALITY_COMPLIANCE",
        "laws": [
            "Check: Alignment — the image must show the window/room without extreme rotation.",
            "Check: Framing — the window must be clearly visible and not cut off.",
            "Check: Lighting — the image must not be completely dark or overexposed.",
            "Check: Focus / Blur — the image must not be so blurry that the window is unreadable.",
            "Check: Resolution — the image must have sufficient resolution to analyse window details.",
            "Check: Angle — the viewing angle must allow forensic window analysis.",
            "Check: Image Size — the image must be within the accepted size limits.",
            "Check: Unwanted content — no explicit, offensive, or unrelated content.",
            "Check: Format — the image must be PNG, JPG, or WEBP.",
            "If any check fails: return an error message with specific feedback on what to improve.",
            "If all checks pass: proceed to Phase 3.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    3: {
        "name": "EXTRACT_INTERIOR_THESIS",
        "laws": [
            "Determine: style (e.g., Japandi, Industrial, Hotel Chic, Scandinavisch, etc.)",
            "Determine: room mood",
            "Determine: luxury level",
            "Determine: warmth/coolness of the space",
            "Determine: material language (dominant materials visible)",
            "Determine: line language (horizontal, vertical, curved, geometric)",
            "Determine: spatial calm/density",
            "Write: style — single label string",
            "Write: styleSummary — maximum 2 sentences",
            "Write: styleDescription — minimum 200 words in Dutch, one paragraph per header, "
            "one blank line between each header paragraph",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    4: {
        "name": "EXTRACT_COLOR_DNA",
        "laws": [
            "Extract exactly 5 real visible colors from the room.",
            "Each matched_catalog_color must literally exist in the MR. JEALOUSY catalog.",
            "Each color must come from a clearly visible room surface or object.",
            "hex_code must be a valid 6-digit hex code (e.g. #AEC6CF).",
            "For each of the 5 colors return: hex_code, extracted_source, matched_catalog_color.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    5: {
        "name": "WINDOW_ARCHITECTURE",
        "laws": [
            "Determine: outer frame bounds",
            "Determine: visible glass bounds",
            "Determine: exact number of distinct visible glass sections",
            "Determine: sash divisions",
            "Determine: mullions/transoms if visible",
            "Determine: recess depth estimate (in cm)",
            "Determine: sill presence and depth",
            "Determine: frame material",
            "Determine: handle presence and side (left/right)",
            "Determine: vent/grille/lock/sensor/protrusion presence",
            "Determine: likely opening mechanism",
            "Determine: likely opening direction (inward/outward)",
            "Determine: fixed or operable",
            "Determine: nearby collision risks with wall/furniture/radiator",
            "Determine: type of glazing",
            "Determine: stack height clearance (distance from top of sash to ceiling)",
            "Determine: structural substrate",
            "Determine: corner proximity",
            "Classify window type as precisely as possible: "
            "Tilt and turn / Fixed / Casement / Sliding / Pivot / French / Multi-pane",
            "Count the EXACT number of distinct visible glass sections.",
            "State any exceptions worth pointing out which impact the mounting strategy.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    6: {
        "name": "MOUNTING_STRATEGY",
        "laws": [
            "NEVER propose a physically impossible placement.",
            "RULE 1 — DEPTH THRESHOLD (The Foundation): "
            "IF recess depth < 5 cm → OUTSIDE MOUNT (op de dag) is mandatory. "
            "Reason: inadequate surface area for bracket tension and headrail stability.",
            "RULE 2 — PROTRUSION & CLEARANCE (The Obstacle): "
            "IF handle/vent/sensor exists AND protrusion depth > recess depth → "
            "OUTSIDE MOUNT (op de dag) is mandatory. "
            "IF handle/vent/sensor exists AND recess depth is 5–15 cm → "
            "INSIDE MOUNT (in de dag), but shift position to the outermost front edge (flush with wall).",
            "RULE 3 — KINEMATIC COLLISION (The Tilt & Turn Factor): "
            "IF window type = Tilt and turn OR Inward Opening → run stack calculation: "
            "stack_height = (window_height / 10) + 10 cm (for Wood/Bamboo). "
            "IF top clearance (sash to ceiling) < stack_height → OUTSIDE MOUNT is mandatory. "
            "Note: the blind must be mounted high enough so the sash clears the stack when opened.",
            "RULE 4 — LATERAL COLLISION (The Corner Risk): "
            "IF side clearance (frame to wall) < 3 cm AND mounting = outside → "
            "FLAG ERROR: 'Insufficient lateral space for overlap; check for corner collision.'",
            "RULE 5 — DEFAULT SELECTION: "
            "IF Rules 1–4 are all false → INSIDE MOUNT (in de dag). "
            "Placement: recessed 10 mm from the wall edge for a clean architectural shadow-gap.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    7: {
        "name": "LIGHTING_CONDITIONS",
        "laws": [
            "Determine: light direction",
            "Determine: light intensity (lux estimate)",
            "Determine: light softness/hardness",
            "Determine: light temperature (warm/cool, approximate Kelvin)",
            "Determine: natural vs artificial contribution (% each)",
            "Determine: reflection behavior on glass/frame",
            "Determine: probable shadow behavior inside the room",
            "Determine: whether wood or aluminium integrates more naturally with this light",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    8: {
        "name": "CATALOG_MATCH",
        "laws": [
            "ABSOLUTE PRODUCT LOCK: You may ONLY use products that literally exist in the "
            "MR. JEALOUSY catalog.",
            "ONLY ALLOWED product types: Houten Jaloezieën, Aluminium Jaloezieën.",
            "Allowed wooden subtypes only: Paulownia, Bamboo, Abachi.",
            "STRICTLY FORBIDDEN: Verticale lamellen.",
            "STRICTLY FORBIDDEN: Gordijnen.",
            "STRICTLY FORBIDDEN: Vouwgordijnen.",
            "STRICTLY FORBIDDEN: Plisségordijnen.",
            "STRICTLY FORBIDDEN: Rolgordijnen.",
            "STRICTLY FORBIDDEN: any other non-horizontal product.",
            "STRICTLY FORBIDDEN: invented products.",
            "STRICTLY FORBIDDEN: invented materials.",
            "STRICTLY FORBIDDEN: invented colors not present in the catalog.",
            "STRICTLY FORBIDDEN: invented finish names.",
            "STRICTLY FORBIDDEN: free interpretation outside the catalog.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
    9: {
        "name": "RENDER_PLANNING",
        "laws": [
            "Prepare exact render instructions for the visualization model.",
            "Output must conform to the RenderInstruction schema.",
            "scene_description must be a minimum of 200 words in Dutch.",
            "The mounting geometry rules from Phase 6 must be reflected verbatim in the instruction.",
            "The lighting physics determined in Phase 7 must drive shadow and reflection specifications.",
            "The product and color must exactly match the Phase 8 catalog selection.",
            "Include a negative_prompt listing all rendering artifacts to avoid.",
            "Specify camera_angle matching the original uploaded image perspective.",
        ],
        "negative_seeds": [],  # TODO: populate in next session
    },
}


# ── HELPER FUNCTIONS ───────────────────────────────────────────────────────────

def get_phase_prompt(phase: int) -> str:
    """
    Build the complete system prompt for a given phase number.
    Injects the live catalog into MASTER_PROMPT, then appends the phase name,
    all phase laws, and negative seeds.
    Returns a single string ready to be sent as the system prompt to Claude.
    """
    if phase not in PHASE_LAWS:
        raise ValueError(f"Phase {phase} does not exist. Valid phases: 1–{PHASE_COUNT}.")

    # Inject catalog into the master prompt at runtime
    base_prompt = MASTER_PROMPT.replace("[CATALOG]", get_catalog_as_text())

    entry = PHASE_LAWS[phase]
    laws_text = "\n".join(f"  - {law}" for law in entry["laws"])

    negative_text = ""
    if entry["negative_seeds"]:
        seeds = "\n".join(f"  - {seed}" for seed in entry["negative_seeds"])
        negative_text = f"\nNEGATIVE SEEDS (forbidden behaviors in this phase):\n{seeds}"

    return (
        f"{base_prompt}\n"
        f"{'─' * 60}\n"
        f"ACTIVE PHASE: {phase} — {entry['name']}\n"
        f"{'─' * 60}\n"
        f"LAWS FOR THIS PHASE (mandatory, in order):\n{laws_text}"
        f"{negative_text}"
    )


def get_catalog_as_text() -> str:
    """
    Format MR_JEALOUSY_CATALOG as plain readable text for injection into prompts.
    Each product type is listed with all its colors (name + hex).
    """
    lines: List[str] = ["MR. JEALOUSY CATALOG (authoritative — only these products exist):"]
    for product_type, colors in MR_JEALOUSY_CATALOG.items():
        lines.append(f"\n{product_type}:")
        for color in colors:
            lines.append(f"  - {color['name']} | hex: {color['hex']} | material: {color['material']}")
    return "\n".join(lines)


def get_allowed_colors(product_type: str) -> List[ProductColor]:
    """Return the full color list for a given product type from the catalog."""
    if product_type not in MR_JEALOUSY_CATALOG:
        raise ValueError(
            f"Product type '{product_type}' not in catalog. "
            f"Allowed: {ALLOWED_PRODUCT_TYPES}"
        )
    return MR_JEALOUSY_CATALOG[product_type]


def resolve_mounting(key: str) -> str:
    """
    Return the full mounting description string from MOUNTING_MAP.
    Defaults to 'in de dag' if the key is not found.
    """
    return MOUNTING_MAP.get(key, MOUNTING_MAP["in de dag"])


def resolve_lighting(key: str) -> str:
    """
    Return the full lighting description string from LIGHTING_MAP.
    Defaults to 'Middag (Helder)' if the key is not found.
    """
    return LIGHTING_MAP.get(key, LIGHTING_MAP["Middag (Helder)"])
