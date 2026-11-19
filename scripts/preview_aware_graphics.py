#!/usr/bin/env python3
"""Render compact content-aware graphic samples with photorealistic bitmaps."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv()

from scripts.infographic import render_infographic, _attach_aware_scene_bitmap

# Avoid already-posted UPI/fold themes in previews
SAMPLES = [
    {
        "name": "preview_aware_compose.png",
        "content": {
            "chip": "COMPOSE",
            "eyebrow": "MONDAY · ANDROID",
            "category": "JETPACK COMPOSE",
            "headline": "Same list. Fewer <em>frame drops</em>.",
            "subhead": "Stable item models beat rewriting your whole screen on every StateFlow emit.",
            "visual": "compose",
            "tags": ["Kotlin", "Compose", "LazyColumn"],
        },
    },
    {
        "name": "preview_aware_ai.png",
        "content": {
            "chip": "ON-DEVICE AI",
            "eyebrow": "WEDNESDAY · AI",
            "category": "GEMINI NANO",
            "headline": "AICore is ready. Your <em>lifecycle</em> isn't.",
            "subhead": "Warm sessions get killed under memory pressure when apps ignore AICore teardown.",
            "visual": "ai",
            "tags": ["Gemini Nano", "AICore", "Kotlin"],
        },
    },
    {
        "name": "preview_aware_crash.png",
        "content": {
            "chip": "TECH NEWS",
            "eyebrow": "FRIDAY · TRENDING",
            "category": "PRODUCTION REALITY",
            "headline": "Users blame the network. It's an <em>ANR</em>.",
            "subhead": "Main-thread work still shows up as 'slow internet' in Play reviews.",
            "visual": "crash",
            "tags": ["ANR", "Play Reviews", "Android"],
        },
    },
]


def main():
    force = "--force" in sys.argv
    out_dir = os.path.join(ROOT, "renderer", "output")
    os.makedirs(out_dir, exist_ok=True)
    for sample in SAMPLES:
        content = dict(sample["content"])
        content = _attach_aware_scene_bitmap(content, force_regen=force)
        out = os.path.join(out_dir, sample["name"])
        render_infographic(content, out, template="aware_graphic_dark.html.j2")
        print("Wrote", out)


if __name__ == "__main__":
    main()
