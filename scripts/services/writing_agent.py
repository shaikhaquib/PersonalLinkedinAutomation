"""
Writing Agent — structurally diverse LinkedIn posts (not one tutorial template).
"""

import os
import glob
import re

POST_SYSTEM_PROMPT = """
You ghostwrite LinkedIn for Aquib Rashid Shaikh — Senior Android Developer & Mobile Tech Lead
(8+ years: Kotlin, Compose, BLE, ExoPlayer/Media3, FinTech, Maps).

Audience: mid–senior Android engineers and mobile leads. Not staff-kernel papers.

CRITICAL — BREAK THE TEMPLATE:
Posts must NOT all look the same. Obey the FORMAT assigned for this draft.
If the format says no bullets / no recruiter line — do not add them.

Banned uniform pattern (never default to this):
  pain hook → mechanism lecture → 3 → bullets → recruiter line → hashtags

Voice:
- Human, short sentences, peer-to-peer.
- Felt problems over jargon soup.
- No fake metrics, companies, or time-anchor openers.
- LinkedIn does NOT render Markdown. Never use **bold**, _italic_, `code`, or ### headers.
  Emphasis (if needed) will be converted to Unicode bold by the pipeline — prefer plain text.
- No: revolutionary, game changer, delve, testament, leverage, seamless, robust,
  "Unpopular opinion:", "Hot take:", Confession:, Plot twist:.

Formats you may be assigned:
- HOT_TAKE: blunt claim, short defense, boundary, argument question. No bullets. No recruiter.
- MYTH_BUST: myth → reality → one correction → disagreement question. No bullets. No recruiter.
- ONE_RULE: pain → why → single rule → question. No 3-bullet lists. No recruiter.
- MINI_STORY: scene → wrong blame → real cause → what you'd change → question. Optional recruiter.
- PEER_QUESTION: question first → short stance → one cue → invite replies. Optional recruiter.

Length by format:
- HOT_TAKE / MYTH_BUST / ONE_RULE: 450–800 chars
- MINI_STORY / PEER_QUESTION: 550–950 chars

Hashtags: last line only, 4–5 tags (#AndroidDev #Kotlin #JetpackCompose #MobileArchitecture #TechLeadership)

After the post:
FIRST_COMMENT: 1–2 line human seed (not a second lecture)
"""


class WritingAgent:
    def __init__(self, llm_generate_fn, root_dir: str = None):
        self.generate_fn = llm_generate_fn
        if root_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.root_dir = root_dir
        self.knowledge_context = self._load_knowledge()

    def _load_knowledge(self) -> str:
        k_dir = os.path.join(self.root_dir, "knowledge")
        if not os.path.exists(k_dir):
            return ""
        parts = []
        for path in sorted(glob.glob(os.path.join(k_dir, "*.md"))):
            base = os.path.basename(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    parts.append(f"--- Knowledge: {base} ---\n" + f.read())
            except Exception:
                pass
        return "\n\n".join(parts)

    def write_post(self, topic: str, source_context: str = "",
                   feedback: str = None, archetype_id: str = None) -> tuple[str, str, str]:
        import time
        from hook_matrix import select_hook_formula, get_archetype_by_id

        if archetype_id:
            hook_data = get_archetype_by_id(archetype_id)
        else:
            hook_data = select_hook_formula(int(time.time()), 0)

        selected_archetype_id = hook_data.get("id", "CONTRARIAN_ARCHITECTURE_CALLOUT")
        fmt = hook_data.get("format", "HOT_TAKE")
        hook_name = hook_data.get("name", "")
        hook_instruction = hook_data.get("instruction", "")
        recruiter = hook_data.get("recruiter_line", False)

        feedback_section = (
            f"\n\nCRITICAL FIXES FROM PREVIOUS REVIEW:\n{feedback}\nAddress these immediately."
            if feedback else ""
        )

        recruiter_rule = (
            "Include the stealth recruiter line once before hashtags:\n"
            "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open."
            if recruiter
            else "Do NOT include any recruiter / DMs-are-open line in this draft."
        )

        prompt = f"""
Topic: {topic}

Context:
{source_context}

ASSIGNED FORMAT: {fmt}
ARCHETYPE: {selected_archetype_id} — {hook_name}

FORMAT RULES (must follow exactly):
{hook_instruction}

{recruiter_rule}

Knowledge (use lightly, don't dump):
{self.knowledge_context[:2500]}
{feedback_section}

Write ONE LinkedIn post that matches FORMAT={fmt} only.
If someone scrolls your last 3 posts, this one must look different in structure.
Plain text only — no Markdown asterisks, underscores, backticks, or orphan * lines.

Then:
FIRST_COMMENT: ...
"""

        raw = self.generate_fn(prompt, POST_SYSTEM_PROMPT)

        post_text = raw
        first_comment = ""
        if "FIRST_COMMENT:" in raw:
            parts = raw.split("FIRST_COMMENT:")
            post_text = parts[0].strip()
            first_comment = parts[1].strip()

        from scripts.services.text_formatter import format_linkedin_text
        post_text = format_linkedin_text(post_text)
        first_comment = format_linkedin_text(first_comment)

        # Soft strip recruiter if format forbids it but model added it
        if not recruiter:
            post_text = re.sub(
                r"\n?Scaling high-impact mobile platforms[\s\S]*?DMs are open\.?\n?",
                "\n",
                post_text,
                flags=re.I,
            ).strip()
            post_text = format_linkedin_text(post_text)

        return post_text, first_comment, selected_archetype_id
