"""
test_keys.py — Quick API key validation for MRJ
Run with: python test_keys.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")

results = {}

# ── ANTHROPIC ────────────────────────────────────────────────────
print("\nTesting ANTHROPIC_API_KEY...")
if not ANTHROPIC_KEY or ANTHROPIC_KEY.startswith("sk-ant-api03-your"):
    results["anthropic"] = "NIET INGEVULD — placeholder waarde in .env"
else:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp   = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=16,
            messages=[{"role": "user", "content": "Say only: OK"}],
        )
        results["anthropic"] = "OK — GELDIG (" + resp.content[0].text.strip() + ")"
    except anthropic.AuthenticationError:
        results["anthropic"] = "FOUT — ONGELDIGE KEY (authenticatie mislukt)"
    except Exception as e:
        results["anthropic"] = f"FOUT — {type(e).__name__}: {e}"

# ── GEMINI ───────────────────────────────────────────────────────
print("Testing GEMINI_API_KEY...")
if not GEMINI_KEY or GEMINI_KEY.startswith("AIzaSy..."):
    results["gemini"] = "NIET INGEVULD — placeholder waarde in .env"
else:
    try:
        from google import genai
        client   = genai.Client(api_key=GEMINI_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say only: OK",
        )
        text = response.text.strip()[:40] if hasattr(response, "text") else "response received"
        results["gemini"] = f"OK — GELDIG ({text})"
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "invalid api key" in msg.lower():
            results["gemini"] = "FOUT — ONGELDIGE KEY (API_KEY_INVALID)"
        elif "PERMISSION_DENIED" in msg:
            results["gemini"] = "FOUT — GEEN TOEGANG (PERMISSION_DENIED)"
        else:
            results["gemini"] = f"FOUT — {type(e).__name__}: {e}"

# ── REPORT ───────────────────────────────────────────────────────
print("\n" + "-" * 55)
print("  MRJ — API Key Test Resultaten")
print("-" * 55)
print("  Anthropic : " + results.get("anthropic", "?"))
print("  Gemini    : " + results.get("gemini", "?"))
print("-" * 55 + "\n")
