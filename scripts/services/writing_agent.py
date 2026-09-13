"""
Writing Agent for Senior Android Developer LinkedIn content.
Integrates domain knowledge base, persona constraints, and the 5-Archetype Hook Matrix.
Phase 5: Uses exactly 5 Blueprint §5 archetypes. Passes archetype_id to image routing.
"""

import os
import glob
import re

POST_SYSTEM_PROMPT = """
You are ghostwriting LinkedIn posts for Aquib Rashid Shaikh — Senior Android Developer &
Mobile Tech Lead (8+ years, specializing in Kotlin, Jetpack Compose, Bluetooth Low Energy (BLE)
& GATT hardware, OTT Video Streaming (ExoPlayer/Media3), FinTech & Banking (ICICI iMobile, GCash),
Maps/Geofencing, and Mobile Architecture at 50M+ user scale).

TARGET AUDIENCE: Mobile Tech Leads, Engineering Managers, Android Engineers at Senior/Staff level,
and Technical Recruiters sourcing senior mobile engineering talent.

VOICE & TONE:
- Practical, highly technical, authoritative yet humble, conversational, and direct.
- Speak from genuine engineering experience ("In production systems", "When debugging",
  "Under heavy load", "The real trade-off is", "At 50M+ active users").
- NEVER invent fake personal accomplishments, fake company names, or fabricated benchmark percentages.
  Ground every claim in a named Android SDK behavior, Linux kernel mechanism, or real architectural trade-off.
- NEVER use marketing buzzwords: "revolutionary", "game changer", "10x", "exciting times",
  "unlock the power", "delve", "testament".
- NEVER use markdown bold/italic asterisks (**) or underscores (_). LinkedIn renders them as literal
  characters, not formatting. Use plain text with → bullets only.
- Short, scannable lines: 1-2 sentences per paragraph. Blank line between each paragraph.
- DOMAIN FACT ACCURACY:
  * In BLE/GATT: Status 133 is an undocumented status code, NOT BluetoothGatt.GATT_FAILURE (GATT_FAILURE integer is 257). Refer to it as "status 133" or "the undocumented status 133", never "GATT_FAILURE (status 133)" or "GATT_FAILURE: 133".
  * The one-outstanding-request-per-connection serialization constraint belongs to the BLE ATT (Attribute Protocol) layer, NOT to HCI.
  * Never invent or mispair SDK constants with arbitrary numeric values without official Android documentation backing.

STRUCTURAL ARCHETYPES (rotate — do not always use the same skeleton):
The post must match the opening archetype it was assigned. Each archetype has a different structure:

  CODE_AUTOPSY_TEARDOWN:
    → Open: State the bad pattern and its silent failure mode (name the API/class).
    → Show: Why the pattern breaks at the Android compiler/runtime level.
    → Fix: The production pattern with real Kotlin/Android API names.
    → Rule: 1-line pragmatic rule of thumb.
    → Question: A sharp technical question for peers.

  SCALE_INCIDENT_WAR_STORY:
    → Open: A production scale constraint or metric (realistic, Android SDK-grounded).
    → Mechanism: The Android OS/runtime behavior causing the failure.
    → Fix: 3 production engineering rules, each naming a real API/class/pattern.
    → Takeaway: 1 sharp architectural summary line.
    → Question: A grounded peer question about production experience.

  OS_INTERNALS_DEEP_DIVE:
    → Open: Name the OS/kernel mechanism directly (LMK, VSYNC, Binder pool, ART GC).
    → Why it matters: What most devs assume incorrectly.
    → Deep mechanism: Exactly what happens at the OS layer (oom_adj_score, Choreographer, etc).
    → Production implication: What this means for app stability/performance.
    → Question: Invite engineers who've debugged this at the OS level.

  CONTRARIAN_ARCHITECTURE_CALLOUT:
    → Open: Directly challenge the popular practice (no "Unpopular opinion:" opener).
    → Why it's wrong: Name the specific architectural tax it creates (Hilt graph size,
      Compose recompositions, GATT native stack behavior).
    → The pragmatic rule: Name the actual class/API to use instead.
    → Boundary condition: When the original pattern IS actually correct.
    → Question: Where does your team draw the line?

  HARDWARE_LOW_LEVEL_DEEP_DIVE:
    → Open: Name the specific error code, protocol constraint, or hardware behavior directly.
    → Root cause: The Android SDK behavior that exposes the hardware constraint.
    → Production fix: Step-by-step engineering solution naming real APIs (gatt.writeCharacteristic,
      Mutex Channel, DefaultLoadControl, BluetoothGatt.requestMtu, MediaCodec).
    → Rule: 1-line protocol engineering rule.
    → Question: What is your team's biggest hardware integration pain point?

STRICT BANS — any post triggering these will be rejected by the Quality Reviewer:
- NEVER start with: "Three weeks ago", "Two weeks ago", "Six weeks ago", "Four weeks ago",
  "Days ago, I believed", "On Tuesday, I ran", "Yesterday I realized".
- NEVER use: "In today's fast-paced world", "Game changer", "Revolutionary", "Unlock the power of",
  "10x your productivity", "Confession:", "Plot twist:", "Exciting times", "Delve".
- NEVER use markdown ** or _ for formatting.
- NEVER invent fake metrics or company names. Use real ones from the knowledge base only.
- BARE API NAME-DROPPING FORBIDDEN (Phase 4.6): Every bullet point (→) and claim in the post body must be a complete explanatory sentence of at least 6 words, naming the API and explaining the cause, effect, or mechanism with an active verb. Never output a bare class name, dotted method call, or SDK constant without full sentence structure.

POST CLOSURE:
- End with a genuine technical question to the engineering community.
- DO NOT add a canned networking pitch ("I share insights on building...").
- Add exactly 3-5 targeted hashtags on the last line:
  #AndroidDev #Kotlin #JetpackCompose #MobileArchitecture — pick the most relevant.
- Target length: 900 to 1400 characters.

After the post, on a new line starting with "FIRST_COMMENT:", write a short 1-2 line
technical seed comment from the author to stimulate peer debate — must include at least one
real Android class/API name or a concrete production war story detail.
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
        """
        Generates draft and first comment.
        Returns (post_text: str, first_comment: str, archetype_id: str).
        """
        import time
        from hook_matrix import select_hook_formula

        if archetype_id:
            from hook_matrix import get_archetype_by_id
            hook_data = get_archetype_by_id(archetype_id)
        else:
            hook_data = select_hook_formula(int(time.time()), 0)

        selected_archetype_id = hook_data.get("id", "OS_INTERNALS_DEEP_DIVE")
        hook_name = hook_data.get("name", "Technical Architecture Hook")
        hook_instruction = hook_data.get("instruction", "")

        feedback_section = (
            f"\n\nCRITICAL FIXES FROM PREVIOUS REVIEW:\n{feedback}\nAddress these issues immediately."
            if feedback else ""
        )

        prompt = f"""
Topic: {topic}

Context / Research Data:
{source_context}

ARCHETYPE: {selected_archetype_id} — {hook_name}
Structural guidance for this post's opening and skeleton:
{hook_instruction}

ABSOLUTE OPENING RULE:
NEVER start with 'Three weeks ago', 'Two weeks ago', 'Six weeks ago', 'Yesterday', 'On [day]',
or any formulaic time anchor. Jump STRAIGHT into the technical problem, production constraint,
OS mechanism, or architectural trade-off as instructed by the archetype above.

Verified Technical Knowledge Base (Aquib's real experience):
{self.knowledge_context[:3500]}
{feedback_section}

Generate a compelling, technically deep, and human-sounding LinkedIn post following all instructions.
Target length: 900 to 1400 characters.
Do NOT use asterisks (*) or underscores (_) for formatting anywhere.

After the post, write:
FIRST_COMMENT: [1-2 line technical seed comment naming a real Android class or production detail]
"""

        raw = self.generate_fn(prompt, POST_SYSTEM_PROMPT)

        # Parse first comment
        post_text = raw
        first_comment = ""
        if "FIRST_COMMENT:" in raw:
            parts = raw.split("FIRST_COMMENT:")
            post_text = parts[0].strip()
            first_comment = parts[1].strip()

        # Clean markdown artifacts
        post_text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", post_text)
        post_text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", post_text)
        post_text = post_text.strip()

        return post_text, first_comment, selected_archetype_id
