# MRJ4.15 Setup Guide

Quick start for Mr. Jealousy Interior Intelligence Tool.

## Prerequisites

- Python 3.9+
- 8+ GB RAM (SAM2 is memory-intensive)
- 3+ GB free disk space (for SAM2 model)
- NVIDIA GPU recommended (SAM2 runs faster with CUDA)

## Environment Setup

### 1. Create virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 2. Install base dependencies

```bash
pip install -r requirements.txt
```

### 3. Download & configure SAM2

**Easiest way — use the setup script:**

```bash
python setup_sam2.py
```

This will:
- Install PyTorch + Torchvision (if missing)
- Install SAM2 from GitHub
- Download the SAM2 Hiera Large model (~2.5 GB)
- Verify everything is working

**Manual installation** (if setup script fails):

```bash
# Install SAM2
pip install -e 'git+https://github.com/facebookresearch/sam2.git@main#egg=sam2'

# Download model
mkdir -p models
cd models
wget https://dl.fbaipublicfiles.com/segment_anything_2/sam2_hiera_large.pt
cd ..
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJ...
FLASK_DEBUG=false
PORT=5000
```

## Running the App

```bash
python app.py
```

Then open: **http://localhost:5000**

## Architecture

**3-Phase Pipeline:**

1. **Phases 1-8 (Analysis)** — Claude vision + logic
   - Quality gate, color extraction, window detection, mounting strategy

2. **Phase 9-bis (Preview)** — Gemini 2.5 Flash
   - Low-res preview (~10-15 seconds)
   - Triggered on color/option change
   - Helps user validate before full render

3. **Phase 9 (Render)** — Gemini 2.5 Flash
   - Full HD photorealistic render (~30-45 seconds)
   - SAM2 segmentation for automatic window detection
   - Triggered by "Resultaat visualiseren" button

## Troubleshooting

### SAM2 model download fails

Download manually:
```bash
mkdir -p models
cd models
wget https://dl.fbaipublicfiles.com/segment_anything_2/sam2_hiera_large.pt
```

### Out of memory errors

SAM2 requires ~4-6 GB VRAM. If you get OOM errors:
- Close other GPU apps
- Reduce image resolution in UI
- Use CPU (slower): set `device='cpu'` in `sam2_segment.py`

### Gemini API errors

- Check `GEMINI_API_KEY` in `.env`
- Verify API key has "Generative" permissions in Google Cloud Console

### Preview takes too long

- Normal: ~10-15 seconds per preview
- If >30s: check network & API quota
- Reduce call frequency (debounce config changes)

## File Structure

```
MRJ4.15 - kopie/
├── app.py                    # Flask server
├── core.py                   # Constants & schemas
├── setup_sam2.py             # SAM2 setup script
├── requirements.txt          # Python dependencies
├── static/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── src/AI/
│   ├── analyse_claude.py     # Phases 2-8 pipeline
│   ├── utils.py
│   └── sam2_segment.py       # Window detection
├── data/
│   ├── catalogus.json        # Product catalog
│   └── uploads/              # User images
└── models/                   # SAM2 checkpoint (downloaded)
    └── sam2_hiera_large.pt
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve frontend |
| `/analyze` | POST | Phases 1-8 analysis |
| `/preview` | POST | Phase 9-bis Gemini preview (~10-15s) |
| `/render` | POST | Phase 9 Gemini render (~30-45s) |

## Performance Tips

1. **Preview caching**: Frontend debounces rapid option changes
2. **Image scaling**: Canvas preview uses max 1200px width
3. **SAM2 inference**: First call loads model (~3-5s), subsequent calls faster
4. **Gemini caching**: Use prompt caching in API config for repeated prompts

## Development

To modify the pipeline:

- **Analysis prompts**: `core.py` → `get_phase_prompt()`
- **Render prompts**: `app.py` → `_run_gemini_render()`
- **Window detection**: `src/AI/sam2_segment.py` → `detect_window_bounds()`
- **Frontend logic**: `static/script.js`

---

**Questions?** Check logs in Flask console for detailed error messages.
