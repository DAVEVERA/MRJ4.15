"""
inpaint_sdxl.py — Local SDXL inpainting for window-blind visualization.

Replaces the Gemini image-edit endpoint. Uses a SAM2-derived mask so the
edit is strictly confined to the window region; the rest of the photo is
preserved pixel-for-pixel.

Model: diffusers/stable-diffusion-xl-1.0-inpainting-0.1
Loads lazily on first call; cached on the GPU thereafter.
"""

import base64
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

_PIPELINE = None
_MODEL_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"


def _get_pipeline():
    """Lazy-load the SDXL inpainting pipeline. CUDA fp16 if available."""
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE

    import torch
    from diffusers import StableDiffusionXLInpaintPipeline

    dtype  = torch.float16 if torch.cuda.is_available() else torch.float32
    device = "cuda" if torch.cuda.is_available() else "cpu"

    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        _MODEL_ID,
        torch_dtype=dtype,
        variant="fp16" if dtype == torch.float16 else None,
        use_safetensors=True,
    ).to(device)

    pipe.set_progress_bar_config(disable=True)
    _PIPELINE = pipe
    return _PIPELINE


def _b64_to_pil(data_url: str) -> Image.Image:
    """Decode a data: URL or raw base64 string into a PIL RGB image."""
    if data_url.startswith("data:"):
        data_url = data_url.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(data_url))).convert("RGB")


def _pil_to_b64_jpeg(img: Image.Image, quality: int = 92) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _prepare_mask(mask_b64: str, target_size: tuple, dilate_px: int = 12,
                  feather_px: int = 6) -> Image.Image:
    """
    Convert SAM2 mask into an inpainting mask: white = inpaint, black = keep.
    Dilates slightly so the blind covers any thin window-frame edge,
    then feathers for a soft transition (avoids hard composite seams).
    """
    if mask_b64.startswith("data:"):
        mask_b64 = mask_b64.split(",", 1)[1]
    mask = Image.open(io.BytesIO(base64.b64decode(mask_b64))).convert("L")
    mask = mask.resize(target_size, Image.NEAREST)
    if dilate_px > 0:
        mask = mask.filter(ImageFilter.MaxFilter(size=dilate_px * 2 + 1))
    if feather_px > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_px))
    return mask


def _round_to_8(img: Image.Image, max_side: int = 1024) -> Image.Image:
    """SDXL likes dimensions divisible by 8; cap longest side for VRAM/speed."""
    w, h = img.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        w, h = int(w * scale), int(h * scale)
    w = (w // 8) * 8
    h = (h // 8) * 8
    return img.resize((w, h), Image.LANCZOS)


def inpaint_blind(
    image_b64: str,
    mask_b64: str,
    prompt: str,
    negative_prompt: str = "",
    seed: int = 42,
    steps: int = 30,
    guidance: float = 7.5,
    strength: float = 0.99,
    max_side: int = 1024,
) -> str:
    """
    Run SDXL inpainting confined to the SAM2 mask.

    Args:
      image_b64        — source room photo (data: URL or raw base64)
      mask_b64         — SAM2 binary mask for the window region
      prompt           — what to put in the masked region (the blind description)
      negative_prompt  — what to avoid (curtains, rollers, etc.)
      seed             — fixed for repeatable output
      steps            — denoising steps; 30 is a good quality/speed balance
      guidance         — CFG scale; 7.5 is standard
      strength         — 0.99 = (almost) fully replace masked region
      max_side         — cap longest side for VRAM/speed

    Returns:
      data:image/jpeg;base64,... of the resulting image at original aspect ratio.
    """
    import torch

    src = _b64_to_pil(image_b64)
    orig_w, orig_h = src.size

    src_resized = _round_to_8(src, max_side=max_side)
    target_size = src_resized.size
    mask = _prepare_mask(mask_b64, target_size)

    pipe = _get_pipeline()

    generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(seed)

    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt or None,
        image=src_resized,
        mask_image=mask,
        num_inference_steps=steps,
        guidance_scale=guidance,
        strength=strength,
        generator=generator,
        height=target_size[1],
        width=target_size[0],
    ).images[0]

    # Restore to original resolution for the UI
    if result.size != (orig_w, orig_h):
        result = result.resize((orig_w, orig_h), Image.LANCZOS)

    return _pil_to_b64_jpeg(result)
