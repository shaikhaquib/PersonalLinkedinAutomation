"""
Hook Matrix — exactly 5 archetypes per AGENT_SYSTEM_BLUEPRINT.md §5.
Each archetype has a structurally distinct opening style calibrated against
the blueprint's 5 sample posts to prevent opener repetition.

Blueprint §5 Archetypes:
  1. CODE_AUTOPSY_TEARDOWN       — Before/After code comparison
  2. SCALE_INCIDENT_WAR_STORY    — 50M+ user scale production incident
  3. OS_INTERNALS_DEEP_DIVE      — Android OS / Linux kernel mechanism
  4. CONTRARIAN_ARCHITECTURE_CALLOUT — Cargo-cult anti-pattern callout
  5. HARDWARE_LOW_LEVEL_DEEP_DIVE — BLE/IPC/OTT hardware protocol layer
"""

import random

HOOK_STYLES = [
    {
        "id": "CODE_AUTOPSY_TEARDOWN",
        "name": "Code Autopsy / Architectural Teardown",
        "template_hint": "code_card_dark.html.j2",
        "instruction": (
            "Open directly with a subtle production bug rooted in a widely-used code pattern. "
            "Do NOT open with a time anchor ('three weeks ago', 'yesterday'). "
            "Start with the architectural problem itself: what the bad code does, "
            "and why it causes silent failure in Compose recomposition, BLE GATT state, "
            "or process death recovery. "
            "Example: 'Passing ViewModel instances down your Composable tree is not Clean Architecture. "
            "It is the number one cause of untraceable recomposition loops in production apps.' "
            "Follow with the specific Android mechanism (Compose compiler stability, "
            "SavedStateHandle, GATT callback contract), then show the production fix pattern. "
            "Structure: Bad pattern → what breaks at the OS/compiler level → production pattern → rule of thumb."
        ),
    },
    {
        "id": "SCALE_INCIDENT_WAR_STORY",
        "name": "Scale Incident & Debugging War Story (50M+ Users)",
        "template_hint": "process_infographic_dark.html.j2",
        "instruction": (
            "Open with a production-scale constraint or metric that most developers never encounter. "
            "Do NOT open with a time anchor or personal confession opener. "
            "Start directly with the production number or system constraint: "
            "Example: 'At 50 million users, a 0.05% crash rate means 25,000 broken sessions every week.' "
            "or 'Android's 1MB Binder transaction buffer is shared across your entire app process. "
            "Send one heavy Bitmap through an Intent, and you get TransactionTooLargeException.' "
            "Then walk through: the symptom → the Android OS mechanism causing it "
            "(Binder IPC, LMK oom_adj_score, GC compaction, main thread starvation) → "
            "the production engineering fix → the measurable outcome. "
            "All metrics must be realistic and grounded in real Android SDK constraints."
        ),
    },
    {
        "id": "OS_INTERNALS_DEEP_DIVE",
        "name": "Under-the-Hood / OS Internals Deep Dive",
        "template_hint": "process_infographic_dark.html.j2",
        "instruction": (
            "Open by naming a specific Android OS or Linux kernel mechanism that senior developers "
            "know exists but rarely inspect in depth. "
            "Do NOT start with a story or time anchor. "
            "Jump straight into the OS reality: "
            "Example: 'Android's Low Memory Killer doesn't throw OutOfMemoryError. "
            "It silently sends SIGKILL to cached background processes based on oom_adj_score.' "
            "or 'Jetpack WindowManager uses a reactive Kotlin Flow for FoldingFeature "
            "hinge posture — not a callback — because posture is a continuous hardware signal, not an event.' "
            "Explain exactly what happens at the OS/kernel/ART/hardware layer "
            "(FusedLocation batching windows, Choreographer VSYNC, ART GC compaction, "
            "Binder thread pool exhaustion) and what it means for production app behavior."
        ),
    },
    {
        "id": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "name": "Contrarian Architecture Callout / Anti-Pattern Bust",
        "template_hint": "code_card_dark.html.j2",
        "instruction": (
            "Open by directly challenging a widely accepted Android development practice. "
            "Do NOT use 'Unpopular opinion:' or 'Hot take:' as openers — just state the contrarian claim directly. "
            "Example: 'Creating a dedicated UseCase class for every single repository method "
            "is one of the biggest productivity drains in modern Android engineering.' "
            "or 'Suppressing configuration changes with android:configChanges on foldables "
            "is technical debt that breaks Jetpack WindowManager reactive posture detection.' "
            "Then give the architectural reason with real API names: what Dagger/Hilt does with the graph, "
            "what the Compose compiler stability classifier marks, what the GATT native stack serializes. "
            "End with a concrete pragmatic rule that names the real class or pattern to use instead."
        ),
    },
    {
        "id": "HARDWARE_LOW_LEVEL_DEEP_DIVE",
        "name": "Hardware & Low-Level Protocol Deep Dive",
        "template_hint": "process_infographic_dark.html.j2",
        "instruction": (
            "Open by naming the specific error code, hardware constraint, or protocol layer rule "
            "that defines the problem. "
            "Do NOT start with a time anchor or personal story. "
            "Jump straight to the protocol or hardware truth: "
            "Example: 'GATT status 133 is Android's catch-all BLE connection failure code. "
            "Nine out of ten times, it is caused by calling gatt.connect() "
            "before the BluetoothGatt native stack has closed the previous handle.' "
            "or 'ExoPlayer's DefaultLoadControl has a 50-second max buffer by default. "
            "On mobile cellular networks, this is an OutOfMemoryError waiting to happen "
            "because MediaCodec allocates hardware-backed DRM secure buffers per keyframe.' "
            "Walk through: the hardware/protocol constraint → the Android SDK behavior that exposes it → "
            "the production engineering fix (MTU negotiation, GATT queue serialization via Mutex Channel, "
            "custom LoadControl thresholds, BLE connection state machine, HLS segment prefetch limits)."
        ),
    },
]


def select_hook_formula(day_of_year: int = 0, slot_index: int = 0) -> dict:
    """
    Select a diverse archetype based on hash + random rotation to guarantee variety.
    Returns the full archetype dict including template_hint.
    """
    idx = (day_of_year * 3 + slot_index + random.randint(0, len(HOOK_STYLES) - 1)) % len(HOOK_STYLES)
    return HOOK_STYLES[idx]


def get_archetype_by_id(archetype_id: str) -> dict:
    """Retrieve a specific archetype by its ID string."""
    for style in HOOK_STYLES:
        if style["id"] == archetype_id:
            return style
    return HOOK_STYLES[0]
