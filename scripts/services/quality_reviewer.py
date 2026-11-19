"""
Quality Review Agent.
Scores technical accuracy, human voice, felt-pain hook, and engagement fitness.
"""

import json
import re

QUALITY_REVIEW_SYSTEM_PROMPT = """
You are a ruthless LinkedIn editor for a Senior Android engineer posting to mid–senior
Android peers. Reject documentation voice and API-soup openers even if technically correct.

Score 1–10:
1. technical_accuracy — Android/Kotlin facts sound
2. naturalness — sounds like a real engineer, not a whitepaper or AI essay
3. originality — non-obvious, worth a comment
4. usefulness — mid–senior engineer can apply something
5. linkedin_fit — scannable, mobile-friendly, no asterisks
6. ai_like_language — LOWER IS BETTER (1 = human, 10 = AI sludge)
7. engagement_hook — first 2 lines name a felt problem people notice (crash, jank, Play reject, freeze, payment fail, angry users, battery). API-first lectures score <=4.

FAIL if any apply:
- Time-anchor opener ("Three weeks ago", "Yesterday", "On Tuesday,")
- Markdown ** or _
- Confession: / Plot twist: / Unpopular opinion:
- First 2 lines are stacked jargon with no human pain (e.g. "Streaming raw unbounded generative UI schemas...")
- Reads like SDK documentation or a conference abstract
- Tutorial clone: pain intro + mechanism paragraph + exactly three →/• fix bullets + recruiter line (too templated)
- GATT_FAILURE associated with status 133
- GATT serialization attributed to HCI instead of ATT
- Bare API bullets (<6 words, no verb)

PASS thresholds:
- technical_accuracy >= 7
- naturalness >= 8
- originality >= 7
- usefulness >= 7
- linkedin_fit >= 7
- ai_like_language <= 3
- engagement_hook >= 7

Return ONLY JSON:
{
  "technical_accuracy": 9,
  "naturalness": 8,
  "originality": 8,
  "usefulness": 8,
  "linkedin_fit": 8,
  "ai_like_language": 2,
  "engagement_hook": 8,
  "passed": true,
  "feedback": "Concise rewrite guidance if failed"
}
"""

_JARGON_SOUP = re.compile(
    r"\b(schema|pipeline|serialization|recomposition|latching|hal\d|surfaceflinger|"
    r"hardwarebuffer|untyped|generative|idempotency|choreographer)\b",
    re.I,
)


class QualityReviewer:
    def __init__(self, llm_generate_fn):
        self.generate_fn = llm_generate_fn

    def review(self, post_text: str, topic: str) -> dict:
        if re.search(r"gatt_failure.*?133|133.*?gatt_failure", post_text, re.I):
            return self._fail(
                "Factual error: BluetoothGatt.GATT_FAILURE is 257; status 133 is undocumented.",
                technical_accuracy=3,
            )

        if re.search(r"hci.*?(?:one\s+active|single\s+active|serializ|gatt\s+transaction)", post_text, re.I):
            return self._fail(
                "Factual error: GATT serialization belongs to ATT, not HCI.",
                technical_accuracy=4,
            )

        # LinkedIn does not render Markdown — fail raw MD before it hits the calendar
        if re.search(r"\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|^#{1,6}\s+", post_text, re.M):
            return self._fail(
                "Markdown detected (** / __ / ` / headers). LinkedIn does not render MD — use plain text.",
                linkedin_fit=3,
            )
        if re.search(r"(?m)^[\*\-_=~`]+$", post_text):
            return self._fail(
                "Orphan markdown residue line (lone * / ---). Strip it — LinkedIn shows it as noise.",
                linkedin_fit=4,
            )

        for line in post_text.splitlines():
            line_str = line.strip()
            if line_str.startswith(("→", "•", "-", "*")):
                clean_bullet = re.sub(r"^[→•\-\*\d\.\s]+", "", line_str).strip()
                if clean_bullet:
                    words = clean_bullet.split()
                    if len(words) < 6 and re.search(
                        r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+|[A-Z][a-zA-Z]+(Exception|Error|Manager|Service|View|Gatt)",
                        clean_bullet,
                    ):
                        return self._fail(
                            f"Bare API bullet '{clean_bullet}'. Use a full clause (6+ words).",
                            usefulness=6,
                        )

        # Programmatic engagement-hook sniff on first ~2 non-empty lines
        opener = " ".join([ln.strip() for ln in post_text.splitlines() if ln.strip()][:2])
        pain_words = (
            "crash", "anr", "freeze", "frozen", "jank", "lag", "users", "review",
            "payment", "battery", "reject", "fail", "angry", "slow", "stuck",
            "broken", "drop", "kill", "leak", "outage", "complaint",
        )
        if opener and _JARGON_SOUP.search(opener) and not any(p in opener.lower() for p in pain_words):
            return self._fail(
                "Opener is API/jargon soup with no felt pain. Rewrite first 2 lines around a user/team problem.",
                naturalness=5,
                engagement_hook=3,
            )

        prompt = f"""
Post Topic: {topic}

Draft to review:
{post_text}

Review against all guidelines and return the JSON evaluation.
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
                hook = int(data.get("engagement_hook", 5))

                passed = (
                    ta >= 7
                    and nat >= 8
                    and orig >= 7
                    and use >= 7
                    and lfit >= 7
                    and ai_lang <= 3
                    and hook >= 7
                )
                data["passed"] = passed
                data["engagement_hook"] = hook
                return data
        except Exception as e:
            print(f"  [QualityReview] Evaluation error ({e}). Using heuristic fallback.")

        return self._heuristic_review(post_text)

    def _fail(self, feedback: str, **overrides) -> dict:
        base = {
            "technical_accuracy": 7,
            "naturalness": 7,
            "originality": 7,
            "usefulness": 7,
            "linkedin_fit": 7,
            "ai_like_language": 2,
            "engagement_hook": 5,
            "passed": False,
            "feedback": feedback,
        }
        base.update(overrides)
        return base

    def _heuristic_review(self, post_text: str) -> dict:
        text_lower = post_text.lower()
        cliches = [
            "in today's", "game changer", "revolutionary", "unlock", "delve",
            "testament", "10x", "productivity", "exciting times", "seamless",
            "three weeks ago", "two weeks ago", "four weeks ago", "six weeks ago",
            "days ago, i", "yesterday i ", "on monday,", "on tuesday,", "confession:",
            "plot twist:", "unpopular opinion:",
        ]
        has_cliche = any(c in text_lower for c in cliches)
        has_asterisks = "*" in post_text
        length = len(post_text)
        pain = any(
            p in text_lower
            for p in ("crash", "anr", "jank", "freeze", "users", "payment", "battery", "reject")
        )

        passed = (not has_cliche) and (not has_asterisks) and (600 <= length <= 2500) and pain
        return {
            "technical_accuracy": 8,
            "naturalness": 8 if not has_cliche else 5,
            "originality": 7,
            "usefulness": 8,
            "linkedin_fit": 8 if not has_asterisks else 5,
            "ai_like_language": 2 if not has_cliche else 6,
            "engagement_hook": 8 if pain else 4,
            "passed": passed,
            "feedback": "Lead with felt pain; avoid AI cliches and markdown." if not passed else "",
        }
