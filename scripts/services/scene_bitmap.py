"""Generate photorealistic content-aware scene bitmaps.

Primary: Cloudflare Workers AI (FLUX.1 schnell).
Fallback: Gemini image models, then bundled cached scenes.
"""

from __future__ import annotations

import base64
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "renderer" / "assets" / "scenes"

# Cloudflare Workers AI — FLUX.2 klein (quality) then FLUX.1 schnell (fallback).
_CF_FLUX_MODELS = [
    "@cf/black-forest-labs/flux-2-klein-4b",  # multipart, higher quality
    "@cf/black-forest-labs/flux-1-schnell",   # JSON + base64, fast fallback
]

# Gemini image models (often unavailable on free tier).
_IMAGE_MODELS = [
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
]

_CF_STYLE = (
    "Ultra photorealistic 8k product photography, three-quarter angle, titanium/silver metal frame, "
    "sharp studio lighting, realistic specular highlights. Solid flat CYAN chroma-key background "
    "#00FFFF edge-to-edge, ZERO gradients, ZERO desk, ZERO props, ZERO shadows on background. "
    "No logos, no watermark, no brand marks. Avoid readable text on screen (icons/shapes only)."
)

_SCENE_PROMPTS: dict[str, str] = {
    "foldable": (
        f"{_CF_STYLE} Two modern foldable smartphones open on the cyan field, soft green rim light only."
    ),
    "payment": (
        f"{_CF_STYLE} One black smartphone with a simple green checkmark success icon on OLED screen."
    ),
    "compose": (
        f"{_CF_STYLE} One black smartphone with abstract cyan code glow on OLED screen "
        "(no readable letters), optional tiny green robot figurine beside phone."
    ),
    "play_policy": (
        f"{_CF_STYLE} One smartphone with a red warning triangle icon on dark screen "
        "(no readable policy text)."
    ),
    "ai": (
        f"{_CF_STYLE} One smartphone with glowing purple neural ripple rings on black OLED screen."
    ),
    "crash": (
        f"{_CF_STYLE} One smartphone only. Dark screen with a simple red ANR-style warning dialog "
        "shape (minimal text, prefer icons)."
    ),
    "security": (
        f"{_CF_STYLE} ONE isolated modern flagship smartphone only. Black OLED screen with a large "
        "neon lime-green glowing fingerprint icon centered, plus a solid neon-lime rounded button "
        "at bottom with NO letters on it. No white modal cards, no busy UI chrome."
    ),
}


def scene_prompt(visual: str, topic: str = "") -> str:
    base = _SCENE_PROMPTS.get(visual, _SCENE_PROMPTS["compose"])
    topic = (topic or "").strip()
    if topic:
        return f"{base} Topic cue (do not render as text on image): {topic[:120]}"
    return base


def _extract_image_bytes(response) -> bytes | None:
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                data = inline.data
                return data if isinstance(data, (bytes, bytearray)) else base64.b64decode(data)
            # Newer SDK helper
            if hasattr(part, "as_image"):
                try:
                    img = part.as_image()
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    return buf.getvalue()
                except Exception:
                    pass
    # Some SDK versions expose .parts on the response
    parts = getattr(response, "parts", None) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            data = inline.data
            return data if isinstance(data, (bytes, bytearray)) else base64.b64decode(data)
    return None


def _copy_cached(cache_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_transparent_cutout(cache_path)
    if out_path.resolve() != cache_path.resolve():
        out_path.write_bytes(cache_path.read_bytes())
    return out_path


def _flood_key_cutout(
    arr,
    key_rgb: tuple[int, int, int],
    *,
    hard_dist: float,
    soft_dist: float,
):
    """Flood-fill chroma key from image edges. Returns RGBA array or None if corners not keyed."""
    from collections import deque

    import numpy as np

    alpha = arr[:, :, 3]
    key = np.array(key_rgb, dtype=np.float32)
    rgb = arr[:, :, :3].astype(np.float32)
    dist = np.sqrt(((rgb - key) ** 2).sum(axis=2))
    hard = dist < hard_dist
    soft = (dist >= hard_dist) & (dist < soft_dist)
    h, w = hard.shape
    corner_hits = sum(
        bool(hard[y, x] or soft[y, x])
        for y, x in ((2, 2), (2, w - 3), (h - 3, 2), (h - 3, w - 3))
    )
    if corner_hits < 3:
        return None

    vis = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if hard[y, x] or soft[y, x]:
                q.append((y, x))
                vis[y, x] = True
    for y in range(h):
        for x in (0, w - 1):
            if (hard[y, x] or soft[y, x]) and not vis[y, x]:
                q.append((y, x))
                vis[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not vis[ny, nx] and (hard[ny, nx] or soft[ny, nx]):
                vis[ny, nx] = True
                q.append((ny, nx))

    new_a = alpha.astype(np.float32)
    span = max(soft_dist - hard_dist, 1.0)
    new_a[vis & hard] = 0
    new_a[vis & soft] = np.clip((dist[vis & soft] - hard_dist) / span * 255.0, 0, 255)
    new_a[new_a < 40] = 0
    new_a[new_a >= 40] = 255
    out = arr.copy()
    out[:, :, 3] = new_a.astype(np.uint8)
    out[new_a < 40, :3] = 0
    return out


def _ensure_transparent_cutout(png_path: Path) -> Path:
    """Auto-remove cyan/navy plate so phone assets stay large/clean without manual babysitting.

    Idempotent: skips if the PNG already has meaningful alpha transparency.
    """
    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return png_path

    png_path = Path(png_path)
    if not png_path.exists():
        return png_path

    try:
        img = Image.open(png_path).convert("RGBA")
    except Exception:
        return png_path

    arr = np.array(img)
    alpha = arr[:, :, 3]
    # Already a cutout (like security.png) — leave alone
    if float((alpha < 12).mean()) > 0.08:
        return png_path

    # Prefer cyan chroma (Cloudflare prompts); fall back to navy plate
    keyed = _flood_key_cutout(arr, (0, 255, 255), hard_dist=90, soft_dist=140)
    if keyed is None:
        keyed = _flood_key_cutout(arr, (11, 18, 32), hard_dist=28, soft_dist=48)
    if keyed is None:
        return png_path

    result = Image.fromarray(keyed, "RGBA")
    bbox = result.split()[-1].getbbox()
    if bbox:
        result = result.crop(bbox)
    result.save(png_path, "PNG")
    print(f"  [scene_bitmap] auto-cutout → {png_path.name} {result.size}")
    return png_path


def _fallback_visual(visual: str) -> str:
    """If a niche scene is missing, reuse the closest stock bitmap."""
    if (CACHE_DIR / f"{visual}.png").exists():
        return visual
    aliases = {
        "play_policy": "crash",
        "foldable": "compose",
        "payment": "compose",
        "ai": "compose",
        "crash": "crash",
        "security": "security",
    }
    preferred = aliases.get(visual, "compose")
    if (CACHE_DIR / f"{preferred}.png").exists():
        return preferred
    for candidate in ("security", "compose", "crash", "ai"):
        if (CACHE_DIR / f"{candidate}.png").exists():
            return candidate
    return "compose"


def _save_scene_png(raw_bytes: bytes, cache_path: Path, out_path: Path) -> Path:
    """Normalize raw image bytes to 1024 PNG, cut navy plate, write cache + out."""
    from PIL import Image

    img = Image.open(BytesIO(raw_bytes)).convert("RGB")
    img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(buf.getvalue())
    _ensure_transparent_cutout(cache_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.resolve() != cache_path.resolve():
        out_path.write_bytes(cache_path.read_bytes())
    else:
        out_path.write_bytes(cache_path.read_bytes())
    return out_path


def _cloudflare_credentials() -> tuple[str, str] | None:
    account = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    token = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    if account and token:
        return account, token
    return None


def _parse_cf_image_response(resp) -> bytes:
    """Extract image bytes from Cloudflare Workers AI JSON or binary response."""
    ctype = (resp.headers.get("content-type") or "").lower()
    if "image/" in ctype:
        return resp.content

    payload = resp.json()
    if not payload.get("success", True) and payload.get("errors"):
        raise RuntimeError(f"Cloudflare AI error: {payload['errors']}")

    result = payload.get("result") or {}
    b64 = result.get("image") or result.get("image_b64")
    if isinstance(b64, str) and b64:
        return base64.b64decode(b64)
    raise RuntimeError("Cloudflare AI response missing result.image base64")


def _generate_cloudflare_image(prompt: str, *, steps: int = 8) -> bytes:
    """Call Workers AI image models; returns raw image bytes (JPEG/PNG).

    Tries FLUX.2 klein (multipart, higher quality) then FLUX.1 schnell (JSON).
    """
    import requests

    creds = _cloudflare_credentials()
    if not creds:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set")
    account_id, token = creds
    auth = {"Authorization": f"Bearer {token}"}
    prompt = prompt[:2000]
    last_error: Exception | None = None

    for model in _CF_FLUX_MODELS:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        try:
            if "flux-2" in model:
                # FLUX.2 family expects multipart form even for text-only prompts
                resp = requests.post(
                    url,
                    headers=auth,
                    files={
                        "prompt": (None, prompt),
                        "width": (None, "1024"),
                        "height": (None, "1024"),
                    },
                    timeout=180,
                )
            else:
                resp = requests.post(
                    url,
                    headers={**auth, "Content-Type": "application/json"},
                    json={"prompt": prompt, "steps": max(1, min(int(steps), 8))},
                    timeout=120,
                )
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:240]}")
            raw = _parse_cf_image_response(resp)
            print(f"  [scene_bitmap] Cloudflare model ok → {model}")
            return raw
        except Exception as exc:
            last_error = exc
            print(f"  [scene_bitmap] Cloudflare {model} failed: {exc}")

    raise RuntimeError(f"All Cloudflare image models failed. Last error: {last_error}")


def generate_scene_png(
    visual: str,
    out_path: str | Path,
    *,
    topic: str = "",
    client_factory: Callable | None = None,
    api_keys: list[str] | None = None,
    use_cache: bool = True,
) -> Path:
    """Generate a photorealistic scene PNG for the given visual key. Returns path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    visual = (visual or "compose").lower().replace(" ", "_")
    cache_key = f"{visual}.png"
    cache_path = CACHE_DIR / cache_key

    # Prefer bundled/cached photorealistic bitmaps (no SVG).
    if use_cache and cache_path.exists() and cache_path.stat().st_size > 10_000:
        print(f"  [scene_bitmap] using cached bitmap → {cache_path.name}")
        return _copy_cached(cache_path, out_path)

    prompt = scene_prompt(visual, topic)
    last_error: Exception | None = None

    # 1) Cloudflare Workers AI (primary for new images)
    if _cloudflare_credentials():
        for attempt in range(1, 3):
            try:
                raw = _generate_cloudflare_image(prompt, steps=8)
                _save_scene_png(raw, cache_path, out_path)
                print(f"  [scene_bitmap] {visual} via Cloudflare → {out_path}")
                return out_path
            except Exception as exc:
                last_error = exc
                print(f"  [scene_bitmap] Cloudflare attempt {attempt}: {exc}")
                time.sleep(1.5 * attempt)

    # 2) Gemini image models
    from google.genai import types

    if client_factory is None:
        from google import genai

        def client_factory(key: str):
            return genai.Client(api_key=key)

    if not api_keys:
        api_keys = [
            k for k in (
                os.environ.get("GEMINI_API_KEY"),
                os.environ.get("GEMINI_API_KEY_2"),
            ) if k
        ]

    if api_keys:
        for key in api_keys:
            client = client_factory(key)
            for model in _IMAGE_MODELS:
                for attempt in range(1, 3):
                    try:
                        cfg = types.GenerateContentConfig(
                            response_modalities=["IMAGE"],
                            image_config=types.ImageConfig(aspect_ratio="1:1"),
                        )
                        resp = client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=cfg,
                        )
                        raw = _extract_image_bytes(resp)
                        if not raw:
                            raise RuntimeError(f"No image bytes returned from {model}")
                        _save_scene_png(raw, cache_path, out_path)
                        print(f"  [scene_bitmap] {visual} via {model} → {out_path}")
                        return out_path
                    except Exception as exc:
                        last_error = exc
                        err = str(exc).lower()
                        print(f"  [scene_bitmap] {model} attempt {attempt}: {exc}")
                        if "429" in err or "quota" in err or "not found" in err or "404" in err:
                            break
                        time.sleep(1.5 * attempt)

    # 3) Soft fallback to nearest bundled bitmap so renders never show SVG icons.
    fb = _fallback_visual(visual)
    fb_path = CACHE_DIR / f"{fb}.png"
    if fb_path.exists() and fb_path.stat().st_size > 10_000:
        print(f"  [scene_bitmap] image APIs unavailable; falling back to {fb_path.name}")
        return _copy_cached(fb_path, out_path)

    raise RuntimeError(
        f"Failed to generate scene bitmap for '{visual}' "
        f"(no cache, no Cloudflare, no Gemini image). Last error: {last_error}"
    )


def png_to_data_uri(png_path: str | Path) -> str:
    data = Path(png_path).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def png_to_file_uri(png_path: str | Path) -> str:
    """file:// URI — Playwright composites PNG alpha more reliably than huge data URIs."""
    return Path(png_path).resolve().as_uri()


def ensure_scene_data_uri(
    visual: str,
    *,
    topic: str = "",
    force_regen: bool = False,
    as_file_uri: bool = True,
) -> str:
    """Return a scene bitmap URI (file:// by default) for template embedding."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{visual}.png"
    if force_regen and cache_path.exists():
        cache_path.unlink()
    path = generate_scene_png(visual, cache_path, topic=topic, use_cache=not force_regen)
    return png_to_file_uri(path) if as_file_uri else png_to_data_uri(path)
