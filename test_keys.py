"""
test_keys.py -- Quick API key validation for MRJ4.15
Run with: python test_keys.py
"""

import os, sys
from pathlib import Path

# Load .env manually
env_path = Path(__file__).parent / ".env"
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY", "")

results = {}

# -- TEST ANTHROPIC ----------------------------------------------------------
print("\nTesting ANTHROPIC_API_KEY...")
if not ANTHROPIC_KEY or ANTHROPIC_KEY == "your_anthropic_api_key_here":
    results["anthropic"] = "NIET INGEVULD -- placeholder waarde in .env"
else:
    try:
        import anthropic  # type: ignore
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        resp = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=16,
            messages=[{"role": "user", "content": "Say only: OK"}],
        )
        results["anthropic"] = "OK -- GELDIG (" + resp.content[0].text.strip() + ")"
    except anthropic.AuthenticationError:
        results["anthropic"] = "FOUT -- ONGELDIGE KEY (authenticatie mislukt)"
    except Exception as e:
        results["anthropic"] = "FOUT -- " + type(e).__name__ + ": " + str(e)

# -- TEST GEMINI -------------------------------------------------------------
print("Testing GEMINI_API_KEY...")
if not GEMINI_KEY or GEMINI_KEY == "your_gemini_api_key_here":
    results["gemini"] = "NIET INGEVULD -- placeholder waarde in .env"
else:
    try:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            results["gemini"] = "FOUT -- google.generativeai module niet geïnstalleerd"
            genai = None
        
        if genai:
            genai.configure(api_key=GEMINI_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content("Say only: OK")
            results["gemini"] = "OK -- GELDIG (" + resp.text.strip()[:40] + ")"
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "invalid api key" in msg.lower():
            results["gemini"] = "FOUT -- ONGELDIGE KEY (API_KEY_INVALID)"
        elif "PERMISSION_DENIED" in msg:
            results["gemini"] = "FOUT -- GEEN TOEGANG (PERMISSION_DENIED)"
        else:
            results["gemini"] = "FOUT -- " + type(e).__name__ + ": " + str(e)

# -- REPORT ------------------------------------------------------------------
print("\n" + "-" * 55)
print("  MRJ4.15 -- API Key Test Resultaten")
print("-" * 55)
print("  Anthropic : " + results.get("anthropic", "?"))
print("  Gemini    : " + results.get("gemini", "?"))
print("-" * 55 + "\n")
