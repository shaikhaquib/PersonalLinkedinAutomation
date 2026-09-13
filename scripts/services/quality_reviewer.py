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
6. ai_like_language (1-10): Does it use AI clichés ("In today's fast-paced world", "game changer", "revolutionary", "unlock", "delve", "testament", "Three weeks ago", "Two weeks ago", "Six weeks ago", "On Tuesday, I ran", "Confession:", "Plot twist:")? (LOWER IS BETTER: 1 = zero AI fluff, 10 = completely AI-sounding).

ADDITIONAL FAIL CONDITIONS (mark passed: false if any apply):
- Post starts with a time-anchor phrase: "Three weeks ago", "Two weeks ago", "Four weeks ago", "Six weeks ago", "Yesterday", "On [day of week],", "Days ago, I"
- Post uses markdown bold (**text**) or italic (_text_) anywhere
- Post starts with "Confession:", "Plot twist:", "Unpopular opinion:"
- FACTUAL ERROR: Associates status 133 with GATT_FAILURE (BluetoothGatt.GATT_FAILURE is 257; status 133 is undocumented)
- FACTUAL ERROR: Attributes GATT single-transaction serialization to HCI instead of ATT (Attribute Protocol)
- Ungrounded constant: Pairs a named SDK constant with an unverified numeric value without SDK grounding
- BARE API BULLET (Phase 4.6): Bullet points (→) that are just bare class/method names or constants without full explanatory sentence structure (min 6 words explaining cause/effect).

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
        # Programmatic factual accuracy checks (Phase 4.5)
        if re.search(r'gatt_failure.*?133|133.*?gatt_failure', post_text, re.I):
            return {
                "technical_accuracy": 3,
                "naturalness": 7,
                "originality": 7,
                "usefulness": 6,
                "linkedin_fit": 7,
                "ai_like_language": 2,
                "passed": False,
                "feedback": "Factual error: BluetoothGatt.GATT_FAILURE is integer 257. Status 133 is undocumented; do not associate GATT_FAILURE with status 133."
            }

        if re.search(r'hci.*?(?:one\s+active|single\s+active|serializ|gatt\s+transaction)', post_text, re.I):
            return {
                "technical_accuracy": 4,
                "naturalness": 7,
                "originality": 7,
                "usefulness": 6,
                "linkedin_fit": 7,
                "ai_like_language": 2,
                "passed": False,
                "feedback": "Factual error: GATT serialization constraint belongs to the ATT (Attribute Protocol) request-response layer, not HCI."
            }

        # Programmatic bare API bullet check (Phase 4.6)
        for line in post_text.splitlines():
            line_str = line.strip()
            if line_str.startswith(('→', '•', '-', '*')):
                clean_bullet = re.sub(r'^[→•\-\*\d\.\s]+', '', line_str).strip()
                if clean_bullet:
                    words = clean_bullet.split()
                    if len(words) < 6 and re.search(r'[A-Za-z0-9_]+\.[A-Za-z0-9_]+|[A-Z][a-zA-Z]+(Exception|Error|Manager|Service|View|Gatt)', clean_bullet):
                        return {
                            "technical_accuracy": 5,
                            "naturalness": 7,
                            "originality": 7,
                            "usefulness": 6,
                            "linkedin_fit": 7,
                            "ai_like_language": 2,
                            "passed": False,
                            "feedback": f"Bare API name-dropping in bullet '{clean_bullet}'. Every bullet must be a complete clause (min 6 words) explaining mechanism with an active verb."
                        }

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
            "testament", "10x", "productivity", "exciting times", "seamless",
            "three weeks ago", "two weeks ago", "four weeks ago", "six weeks ago",
            "days ago, i", "yesterday i ", "on monday,", "on tuesday,", "on wednesday,",
            "on thursday,", "on friday,", "confession:", "plot twist:", "unpopular opinion:"
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
