"""
Image Decision Agent — Phase 3 compliant.
Determines whether a post needs a visual, and if so, which of the exactly two
permitted template types to use:
  1. process_infographic_dark.html.j2  — Architecture Blueprint Card
     (state flows, OS internals, pipeline diagrams, IPC/BLE/OTT mechanisms)
  2. code_card_dark.html.j2            — Syntax-Highlighted Code Card
     (before/after code teardowns, anti-pattern callouts, concrete Kotlin fixes)

No third layout is permitted per Blueprint §4.
Text-only is used for opinion, career, and culture posts.
"""

import re
import json

# Topics that benefit from the Architecture Blueprint Card (state flow / pipeline)
ARCHITECTURE_CARD_TOPICS = {
    "architecture", "lifecycle", "flow", "pipeline", "coroutine", "memory",
    "binder", "ipc", "leak", "jank", "internals", "security", "keystore",
    "ble", "bluetooth", "gatt", "exoplayer", "media3", "streaming", "hls",
    "geofencing", "fused", "location", "lmk", "process death", "modular",
    "windowmanager", "foldable", "multi-resume", "transaction", "idempotency",
    "benchmark", "performance", "gradle", "startup", "baseline"
}

# Topics that benefit from the Code Card (before/after Kotlin teardown)
CODE_CARD_TOPICS = {
    "recomposition", "composable", "compose", "lambda", "state hoist",
    "viewmodel", "usecase", "clean architecture", "mvvm", "mvi", "repository",
    "dependency injection", "hilt", "dagger", "singleton", "sealed",
    "extension", "operator", "coroutine scope", "channel", "mutex",
    "savedstatehandle", "remember", "derivedstateof", "stableclass",
    "unstable", "anti-pattern", "teardown", "code review", "pattern"
}

# Topics that are always text-only
TEXT_ONLY_TOPICS = {
    "opinion", "career", "interview", "mindset", "culture", "hiring",
    "announcement", "soft skills", "leadership", "job search", "burnout"
}

_TEMPLATE_ARCH_DARK  = "process_infographic_dark.html.j2"
_TEMPLATE_CODE_DARK  = "code_card_dark.html.j2"
_TEMPLATE_ARCH_LIGHT = "process_infographic_light.html.j2"
_TEMPLATE_CODE_LIGHT = "code_card_light.html.j2"
_TEMPLATE_CAROUSEL   = "carousel_card.html.j2"

# Backward-compatible defaults
_TEMPLATE_ARCH = _TEMPLATE_ARCH_DARK
_TEMPLATE_CODE = _TEMPLATE_CODE_DARK


class ImageDecisionAgent:
    def __init__(self, llm_generate_fn=None):
        self.generate_fn = llm_generate_fn

    def decide(self, topic: str, post_text: str, archetype_id: str = "", theme: str = "dark") -> tuple[bool, str, str]:
        """
        Decides image type based on topic, archetype, length, and requested theme.
        Returns (should_generate: bool, reason: str, template_name: str).
        template_name is one of the permitted templates or "" (text-only).
        """
        arch_template = _TEMPLATE_ARCH_LIGHT if theme == "light" else _TEMPLATE_ARCH_DARK
        code_template = _TEMPLATE_CODE_LIGHT if theme == "light" else _TEMPLATE_CODE_DARK

        combined = f"{topic} {post_text} {archetype_id}".lower()

        # 1. Check if content is long and benefits from a swipeable multi-slide carousel
        is_long = len(post_text) >= 1100 or post_text.count("•") >= 4
        if is_long:
            return True, f"Deep multi-point content ({len(post_text)} chars / {post_text.count('•')} takeaways) — Swipeable Multi-Slide PDF Carousel selected for maximum dwell time.", _TEMPLATE_CAROUSEL

        # 2. Check if text-only
        if any(t in combined for t in TEXT_ONLY_TOPICS) and not any(
            t in combined for t in ARCHITECTURE_CARD_TOPICS | CODE_CARD_TOPICS
        ):
            return False, "Opinion/culture/career post — text-only performs better.", ""

        # 3. Code Card — Code Autopsy or Contrarian anti-pattern archetype
        if archetype_id in ("CODE_AUTOPSY_TEARDOWN", "CONTRARIAN_ARCHITECTURE_CALLOUT"):
            return True, f"Code teardown/anti-pattern archetype — Syntax-Highlighted Code Card ({theme}) selected.", code_template

        # 3. Code Card — topic signals code comparison
        code_score = sum(1 for t in CODE_CARD_TOPICS if t in combined)
        arch_score = sum(1 for t in ARCHITECTURE_CARD_TOPICS if t in combined)

        if code_score > arch_score and code_score >= 2:
            return True, f"Code pattern comparison topic — Syntax-Highlighted Code Card ({theme}) selected.", code_template

        # 4. Architecture Blueprint Card — technical mechanism/pipeline/OS internals
        if arch_score >= 1 or any(t in combined for t in ARCHITECTURE_CARD_TOPICS):
            return True, f"Technical architecture/OS internals topic — Architecture Blueprint Card ({theme}) selected.", arch_template

        # 5. LLM fallback with template routing
        if self.generate_fn:
            prompt = f"""Post Topic: {topic}
Archetype: {archetype_id}
Post Excerpt: {post_text[:400]}

Decide: Which visual template best fits this LinkedIn post by a Senior Android Developer?
Options:
- "architecture_card": State flows, OS internals, BLE/OTT/IPC pipeline diagrams, process death, foldables.
- "code_card": Before/after Kotlin code comparison, anti-pattern teardown, composable hoisting, API misuse.
- "text_only": Opinion, career, culture, leadership lesson.

Return ONLY valid JSON:
{{"template": "architecture_card", "reason": "brief reason"}}"""
            try:
                raw = self.generate_fn(prompt, "You are a technical visual content strategist for Android engineering posts.")
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    res = json.loads(match.group(0))
                    tpl = res.get("template", "architecture_card")
                    reason = res.get("reason", "LLM decision")
                    if tpl == "text_only":
                        return False, reason, ""
                    elif tpl == "code_card":
                        return True, reason, code_template
                    else:
                        return True, reason, arch_template
            except Exception:
                pass

        # Default: Architecture Blueprint Card for any technical topic
        return True, f"Default — Architecture Blueprint Card ({theme}) for technical topic.", arch_template

    def should_generate_image(self, topic: str, post_text: str) -> tuple[bool, str]:
        """Legacy compatibility shim — returns (needs_image, reason)."""
        needs, reason, _ = self.decide(topic, post_text)
        return needs, reason
