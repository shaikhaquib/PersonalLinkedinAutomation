"""
Image Decision Agent.
Determines whether an infographic genuinely adds technical value to a LinkedIn post.
"""

import re
import json

INFOGRAPHIC_VALUABLE_TOPICS = {
    "architecture", "lifecycle", "workflow", "comparison", "flow", "coroutine",
    "memory", "leak", "jank", "recomposition", "internals", "security", "keystore",
    "idempotency", "pipeline", "process", "binder", "ipc", "performance", "benchmark"
}

TEXT_ONLY_TOPICS = {
    "opinion", "career", "interview", "mindset", "observation", "culture",
    "hiring", "announcement", "soft skills", "leadership lesson"
}


class ImageDecisionAgent:
    def __init__(self, llm_generate_fn=None):
        self.generate_fn = llm_generate_fn

    def should_generate_image(self, topic: str, post_text: str) -> tuple[bool, str]:
        """
        Decides if an infographic adds value.
        Returns (should_generate: bool, reason: str).
        """
        combined = f"{topic} {post_text}".lower()

        # Check explicit text-only triggers
        if any(term in combined for term in TEXT_ONLY_TOPICS) and not any(v in combined for v in INFOGRAPHIC_VALUABLE_TOPICS):
            return False, "Post is focused on engineering culture, career, or opinion; text-only performs better."

        # Check technical/visual triggers
        if any(term in combined for term in INFOGRAPHIC_VALUABLE_TOPICS):
            return True, "Technical concept or workflow benefits strongly from a step-by-step visual diagram."

        # If LLM available, ask LLM
        if self.generate_fn:
            prompt = f"""
Post Topic: {topic}
Post Excerpt: {post_text[:400]}

Question: Would this LinkedIn post benefit significantly from a technical step-by-step process diagram/infographic, or is it better as text-only?
Diagrams are good for: architecture, workflows, mechanisms, comparisons, data flows.
Text-only is good for: opinions, short observations, career lessons, announcements.

Return ONLY valid JSON:
{{"needs_image": true, "reason": "brief reason"}}
"""
            try:
                raw = self.generate_fn(prompt, "You are a visual technical content strategist.")
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    res = json.loads(match.group(0))
                    return bool(res.get("needs_image", True)), res.get("reason", "LLM decision")
            except Exception:
                pass

        # Default fallback
        return True, "Defaulting to visual infographic for technical topic."
