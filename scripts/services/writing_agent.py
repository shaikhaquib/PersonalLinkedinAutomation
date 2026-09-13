"""
Writing Agent for Senior Android Developer LinkedIn content.
Integrates domain knowledge base, persona constraints, and the Hook Matrix.
"""

import os
import glob
import re
from hook_matrix import select_hook_formula

POST_SYSTEM_PROMPT = """
You are ghostwriting LinkedIn posts for a Senior Android Developer (8+ years experience, specializing in Kotlin, Jetpack Compose, Bluetooth Low Energy (BLE), OTT Video Streaming (ExoPlayer/Media3), FinTech & Banking Systems, Maps/Geofencing, and Mobile Architecture at scale).
Your target audience consists of Mobile Tech Leads, Engineering Managers, Android Engineers, and Technical Recruiters looking for senior/staff engineering talent.

VOICE & TONE:
- Practical, technical, authoritative yet humble, conversational, and direct.
- Speak from genuine engineering experience ("In production systems", "When debugging", "Under heavy load", "The real trade-off is").
- NEVER invent fake personal accomplishments, fake company names, or fabricated benchmark percentages. Ground claims in technical mechanisms, real Android SDK behaviors, and architectural trade-offs.
- NEVER use marketing buzzwords: "revolutionary", "game changer", "10x", "exciting times", "unlock the power", "delve".
- NEVER use markdown bold/italic asterisks (`**` or `*`) or underscores (`_`). LinkedIn prints asterisks as literal characters. Use plain text and bullet points with "→" or "-".
- Short, scannable lines: 1-2 sentences per paragraph. Clean whitespace for mobile reading.

POST STRUCTURE:
1. Hook: 1-2 lines. Must stop the scroll before the LinkedIn "see more" cutoff (~210 characters). Focus on a counter-intuitive production lesson, architecture trade-off, or scaling bottleneck.
2. The Production Problem: Why the common approach degrades under real production conditions (process death, battery drain, memory pressure/LMK, thread starvation, flaky networks, frame drops).
3. The Technical Mechanism: Name the concrete Kotlin/Android concept, SDK API (Media3, BLE GATT, Compose Stability, Coroutine channels, FusedLocation), or architecture pattern that solves it.
4. Concrete Details: 3 short bullet points ("→") detailing why this mechanism works and what trade-offs were made.
5. Takeaway: 1 sharp architectural summary line.
6. Closing discussion prompt: A direct, genuine technical question for the Android engineering community.
7. Subtle Inbound Networking Hook: 1 sentence inviting connections from engineering leaders and peers (e.g., "I share insights on building reliable, high-performance Android & mobile systems at scale. Always open to connecting with fellow mobile architects, engineers, and hiring teams.").
8. Recruiter SEO Hashtags: Exactly 3 to 5 targeted industry hashtags on the last line (e.g. #AndroidDev #Kotlin #JetpackCompose #MobileArchitecture #SoftwareEngineering).
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

    def write_post(self, topic: str, source_context: str = "", feedback: str = None) -> tuple[str, str]:
        """
        Generates draft and first comment.
        Returns (post_text: str, first_comment: str).
        """
        import time
        from hook_matrix import select_hook_formula
        hook_data = select_hook_formula(int(time.time()), 0)
        hook_name = hook_data.get("name", "Technical Architecture Hook")
        hook_instruction = hook_data.get("instruction", "")

        feedback_section = f"\n\nCRITICAL FIXES FROM PREVIOUS REVIEW:\n{feedback}\nAddress these issues immediately." if feedback else ""

        prompt = f"""
Topic: {topic}

Context / Research Data:
{source_context}

Opening Style Requirement: {hook_name}
Guidance for this post's hook:
{hook_instruction}

STRICT RULE ON OPENING:
- NEVER start with 'Three weeks ago', 'Two weeks ago', 'Six weeks ago', 'On Tuesday', 'On October 14th', or any formulaic time anchor.
- Jump STRAIGHT into the technical problem, counter-intuitive insight, architecture rule, or production constraint.

Verified Technical Knowledge Base:
{self.knowledge_context[:3000]}
{feedback_section}

Generate a compelling, technically deep, and human-sounding LinkedIn post following all instructions.
Target length: 900 to 1400 characters.
Do NOT use asterisks (*) for formatting.

At the very end of your response, on a new line starting with "FIRST_COMMENT:", provide a short, punchy 1-2 line comment from the author to seed engagement in the comments section.
"""

        raw = self.generate_fn(prompt, POST_SYSTEM_PROMPT)

        # Parse first comment if provided
        post_text = raw
        first_comment = ""
        if "FIRST_COMMENT:" in raw:
            parts = raw.split("FIRST_COMMENT:")
            post_text = parts[0].strip()
            first_comment = parts[1].strip()

        # Clean any accidental markdown asterisks
        post_text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", post_text)
        post_text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", post_text)
        post_text = post_text.strip()

        return post_text, first_comment
