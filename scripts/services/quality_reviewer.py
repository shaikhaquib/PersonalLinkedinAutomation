"""
Quality Review Agent.
Evaluates generated drafts against technical depth, tone authenticity, and AI clichés.
"""

import json
import re

QUALITY_REVIEW_SYSTEM_PROMPT = """
You are a ruthless Senior Mobile Engineering Director and editor reviewing a LinkedIn post written by a Senior Android Engineer.
Your job is to ensure this post is technically accurate, reads like a real developer wrote it over coffee, and is completely free of generic AI-generated fluff, marketing jargon, and fake personal stories.

Evaluate the draft on these exact metrics (scored 1 to 10):
1. technical_accuracy (1-10): Is the Android/Kotlin concept factually accurate and technically sound?
2. naturalness (1-10): Does it sound like a real person talking, rather than a LinkedIn influencer or marketing copy?
3. originality (1-10): Does it present a fresh perspective, practical tip, or non-obvious insight?
4. usefulness (1-10): Will an Android/mobile engineer learn something practical from reading this?
5. linkedin_fit (1-10): Is the formatting scannable, mobile-friendly (1-2 sentences per paragraph), with no asterisks?
6. ai_like_language (1-10): Does it use AI clichés ("In today's fast-paced world", "game changer", "revolutionary", "unlock", "delve", "testament")? (LOWER IS BETTER: 1 = zero AI fluff, 10 = completely AI-sounding).

Thresholds for PASS:
- technical_accuracy >= 8
- naturalness >= 8
- originality >= 7
- usefulness >= 7
- linkedin_fit >= 7
- ai_like_language <= 3

Return ONLY valid JSON matching this exact structure:
{
  "technical_accuracy": 9,
  "naturalness": 8,
  "originality": 8,
  "usefulness": 8,
  "linkedin_fit": 8,
  "ai_like_language": 2,
  "passed": true,
  "feedback": "Concise feedback for rewrite if passed is false"
}
"""


class QualityReviewer:
    def __init__(self, llm_generate_fn):
        self.generate_fn = llm_generate_fn

    def review(self, post_text: str, topic: str) -> dict:
        prompt = f"""
Post Topic: {topic}

Draft to review:
{post_text}

Review this draft against all guidelines and return the JSON evaluation.
"""
        try:
            raw = self.generate_fn(prompt, QUALITY_REVIEW_SYSTEM_PROMPT)
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                ta = int(data.get("technical_accuracy", 5))
                nat = int(data.get("naturalness", 5))
                orig = int(data.get("originality", 5))
                use = int(data.get("usefulness", 5))
                lfit = int(data.get("linkedin_fit", 5))
                ai_lang = int(data.get("ai_like_language", 5))

                # Check strict thresholds
                passed = (
                    ta >= 8 and
                    nat >= 8 and
                    orig >= 7 and
                    use >= 7 and
                    lfit >= 7 and
                    ai_lang <= 3
                )
                data["passed"] = passed
                return data
        except Exception as e:
            print(f"  [QualityReview] Evaluation error ({e}). Using heuristic fallback.")

        # Heuristic fallback
        return self._heuristic_review(post_text)

    def _heuristic_review(self, post_text: str) -> dict:
        text_lower = post_text.lower()
        cliches = [
            "in today's", "game changer", "revolutionary", "unlock", "delve",
            "testament", "10x", "productivity", "exciting times", "seamless"
        ]
        has_cliche = any(c in text_lower for c in cliches)
        has_asterisks = "*" in post_text
        length = len(post_text)

        passed = (not has_cliche) and (not has_asterisks) and (600 <= length <= 2500)
        return {
            "technical_accuracy": 8,
            "naturalness": 8 if not has_cliche else 5,
            "originality": 7,
            "usefulness": 8,
            "linkedin_fit": 8 if not has_asterisks else 5,
            "ai_like_language": 2 if not has_cliche else 6,
            "passed": passed,
            "feedback": "Avoid markdown asterisks and generic AI cliches." if not passed else ""
        }
