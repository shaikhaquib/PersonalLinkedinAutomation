"""
Hook Matrix — 5 archetypes with STRUCTURALLY different post formats.

Each archetype must produce a visibly different LinkedIn post shape.
Never collapse all of them into: pain → lecture → 3 bullets → recruiter.
"""

import random

HOOK_STYLES = [
    {
        "id": "CODE_AUTOPSY_TEARDOWN",
        "name": "One Bad Pattern / One Rule",
        "format": "ONE_RULE",
        "template_hint": "hook_poster_dark.html.j2",
        "recruiter_line": False,
        "instruction": (
            "FORMAT = ONE_RULE (short). Do NOT write a tutorial.\n"
            "Shape:\n"
            "1) 1–2 lines: name the bad pattern via what users/devs feel.\n"
            "2) 2–3 lines: why it breaks (one API max).\n"
            "3) ONE rule of thumb in plain language (no → bullet list).\n"
            "4) One peer question.\n"
            "5) Hashtags only. NO recruiter DM line.\n"
            "Hard ban: 3-bullet fix lists, 'Core Fixes', numbered teaching blocks."
        ),
    },
    {
        "id": "SCALE_INCIDENT_WAR_STORY",
        "name": "Mini Scene / War Story",
        "format": "MINI_STORY",
        "template_hint": "hook_poster_dark.html.j2",
        "recruiter_line": True,
        "instruction": (
            "FORMAT = MINI_STORY. Write like a peer recounting a messy day — not a blog.\n"
            "Shape:\n"
            "1) A concrete scene (checkout freeze, Play reject email, ANR spike) — no fake company names.\n"
            "2) What the team wrongly blamed first.\n"
            "3) The real cause in one plain sentence + one API.\n"
            "4) What you'd do differently next time (2 sentences max).\n"
            "5) Question + optional recruiter line + hashtags.\n"
            "Hard ban: three → bullets, kernel lectures, 'At 50 million users' fake-sounding openers."
        ),
    },
    {
        "id": "OS_INTERNALS_DEEP_DIVE",
        "name": "Myth Bust",
        "format": "MYTH_BUST",
        "template_hint": "hook_poster_light.html.j2",
        "recruiter_line": False,
        "instruction": (
            "FORMAT = MYTH_BUST.\n"
            "Shape:\n"
            "1) Line 1: 'Most Android teams still believe X.' (or equivalent myth)\n"
            "2) Line 2–3: What actually happens in production (symptom first).\n"
            "3) One plain correction naming at most one API/mechanism.\n"
            "4) One sharp question that invites disagreement.\n"
            "5) Hashtags only. NO recruiter line. NO bullet lists.\n"
            "Hard ban: 3-step fix guides, ELF/kernel deep dives, essay tone."
        ),
    },
    {
        "id": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "name": "Hot Take",
        "format": "HOT_TAKE",
        "template_hint": "hook_poster_quote_dark.html.j2",
        "recruiter_line": False,
        "instruction": (
            "FORMAT = HOT_TAKE. Punchy. Opinionated. Scroll-stopping.\n"
            "Shape:\n"
            "1) One blunt claim in the first line (no 'Hot take:' label).\n"
            "2) 3–5 short lines defending it with production pain, not jargon soup.\n"
            "3) One boundary: when the unpopular side is actually right.\n"
            "4) A question that begs a comment argument.\n"
            "5) Hashtags only. NO bullets. NO recruiter line.\n"
            "Target length: 450–750 characters. If it looks like a blog post, rewrite shorter."
        ),
    },
    {
        "id": "HARDWARE_LOW_LEVEL_DEEP_DIVE",
        "name": "Peer Question Lead",
        "format": "PEER_QUESTION",
        "template_hint": "hook_poster_light.html.j2",
        "recruiter_line": True,
        "instruction": (
            "FORMAT = PEER_QUESTION. Lead with curiosity, not a lecture.\n"
            "Shape:\n"
            "1) Open with a real peer question engineers argue about.\n"
            "2) 2–4 lines of your stance / what you've seen break.\n"
            "3) One practical cue (API or check) — not a full guide.\n"
            "4) Invite others to share what worked for them.\n"
            "5) Optional recruiter line + hashtags.\n"
            "Hard ban: 3-bullet SOPs, architecture sermons, protocol textbooks."
        ),
    },
]


def select_hook_formula(day_of_year: int = 0, slot_index: int = 0) -> dict:
    idx = (day_of_year * 3 + slot_index + random.randint(0, len(HOOK_STYLES) - 1)) % len(HOOK_STYLES)
    return HOOK_STYLES[idx]


def get_archetype_by_id(archetype_id: str) -> dict:
    for style in HOOK_STYLES:
        if style["id"] == archetype_id:
            return style
    return HOOK_STYLES[0]
