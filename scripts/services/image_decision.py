"""
Image Decision Agent.

Not every post needs a bitmap poster. Routes to:
  - text-only (no card)
  - bullet_card  (headline + 3 text bullets)
  - code_card    (before/after Kotlin snippet)
  - aware_graphic (clean product phone bitmap)
"""

from __future__ import annotations

import hashlib
import re

TEXT_ONLY_TOPICS = {
    "opinion", "career", "interview", "mindset", "culture", "hiring",
    "announcement", "soft skills", "leadership", "job search", "burnout",
    "mentorship", "imposter",
}

TECH_TOPICS = {
    "android", "kotlin", "compose", "jetpack", "anr", "crash", "play",
    "payment", "gemini", "architecture", "gradle", "biometric", "security",
    "aicore", "room", "hilt", "coroutine",
}

CODE_SIGNALS = {
    "fun ", "@composable", "viewmodelscope", "stateflow", "launch {",
    "before/after", "antipattern", "code autopsy", "snippet",
    "cancellationexception", "Dispatchers.IO", "remember(",
}

PRODUCT_VISUAL_SIGNALS = {
    "biometric", "fingerprint", "face unlock", "phone", "anr", "freeze",
    "crash", "play console", "16kb", "gemini nano", "aicore", "on-device",
    "compose list", "lazycolumn", "payment successful", "notification",
}

BULLET_SIGNALS = {
    "rule", "checklist", "3 things", "three things", "takeaway",
    "what to audit", "stop doing", "instead of", "• ", "1️⃣",
}

_TEMPLATE_AWARE = "aware_graphic_dark.html.j2"
_TEMPLATE_CODE = "code_card_dark.html.j2"
_TEMPLATE_BULLET = "bullet_card_dark.html.j2"


class ImageDecisionAgent:
    def __init__(self, llm_generate_fn=None):
        self.generate_fn = llm_generate_fn

    def decide(
        self,
        topic: str,
        post_text: str,
        archetype_id: str = "",
        theme: str = "dark",
    ) -> tuple[bool, str, str]:
        combined = f"{topic} {post_text} {archetype_id}".lower()
        arch = (archetype_id or "").upper()

        # Pure opinion / career → text-only
        if any(t in combined for t in TEXT_ONLY_TOPICS) and not any(t in combined for t in TECH_TOPICS):
            return False, "Opinion/culture/career post — text-only.", ""

        # Explicit code autopsy / Kotlin teardown → code card
        if arch == "CODE_AUTOPSY_TEARDOWN" or self._looks_like_code_post(combined):
            tpl = _TEMPLATE_CODE if theme != "light" else "code_card_light.html.j2"
            return True, "Before/after Kotlin code card.", tpl

        # Strong product/device visual → clean phone bitmap poster
        if self._looks_like_product_visual(combined):
            return True, "Clean product phone bitmap card.", _TEMPLATE_AWARE

        # Rules / checklist / contrarian callouts → text bullet card
        if arch == "CONTRARIAN_ARCHITECTURE_CALLOUT" or self._looks_like_bullet_post(combined):
            return True, "Text bullet card (no bitmap).", _TEMPLATE_BULLET

        # Variety fallback so we don't always ship the same poster style
        bucket = self._variety_bucket(topic)
        if bucket == 0:
            return False, "Variety slot — text-only (no card).", ""
        if bucket == 1:
            return True, "Variety slot — text bullet card.", _TEMPLATE_BULLET
        if bucket == 2:
            tpl = _TEMPLATE_CODE if theme != "light" else "code_card_light.html.j2"
            return True, "Variety slot — Kotlin code card.", tpl
        return True, "Variety slot — clean product bitmap card.", _TEMPLATE_AWARE

    def should_generate_image(self, topic: str, post_text: str) -> tuple[bool, str]:
        needs, reason, _ = self.decide(topic, post_text)
        return needs, reason

    @staticmethod
    def _looks_like_code_post(text: str) -> bool:
        if sum(1 for s in CODE_SIGNALS if s.lower() in text) >= 2:
            return True
        if re.search(r"```|fun\s+\w+\(|@Composable", text):
            return True
        return False

    @staticmethod
    def _looks_like_product_visual(text: str) -> bool:
        return any(s in text for s in PRODUCT_VISUAL_SIGNALS)

    @staticmethod
    def _looks_like_bullet_post(text: str) -> bool:
        return any(s in text for s in BULLET_SIGNALS)

    @staticmethod
    def _variety_bucket(topic: str) -> int:
        digest = hashlib.md5((topic or "x").encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 4
