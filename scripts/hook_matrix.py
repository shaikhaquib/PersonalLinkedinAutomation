"""
Hook Matrix — 12 diverse, non-formulaic opening styles for a Senior Android Developer & Architect.
Eliminates repetitive tropes like 'Three weeks ago, I believed...' and gives real engineering variety.
"""

import random

HOOK_STYLES = [
    {
        "id": "PROD_INCIDENT",
        "name": "Production Incident / Post-Mortem Hook",
        "instruction": (
            "Open directly with an architecture problem, crash, or unexpected behavior seen in production. "
            "Never start with 'Three weeks ago' or 'Yesterday'. "
            "Example: 'A single unhandled configuration change on a foldable device will silently wipe your ViewModel state if you're not using SavedStateHandle.' "
            "or 'GATT status 133 is the most frustrating error in Android BLE—and 90% of the time, it's caused by calling connect() before the native stack has closed.'"
        )
    },
    {
        "id": "CONTRARIAN_ENGINEERING",
        "name": "Contrarian / Anti-Pattern Callout",
        "instruction": (
            "Challenge a widely accepted developer habit or popular library shortcut with a concrete architectural reason. "
            "Example: 'Passing deep ViewModel instances down your Jetpack Compose tree isn't Clean Architecture—it breaks composable previews and causes untraceable recomposition loops.' "
            "or 'Bypassing Activity recreation with configChanges on foldables is usually technical debt in disguise.'"
        )
    },
    {
        "id": "HARD_NUMBERS_SCALE",
        "name": "Scale & Telemetry Metric",
        "instruction": (
            "Start with a realistic production metric or constraint encountered at scale. "
            "Example: 'The 1MB Binder transaction buffer is shared across your entire app process. Send one heavy Bitmap or serialized list through an Intent, and you get a TransactionTooLargeException.' "
            "or 'At 50M+ users, a 0.1% ANR rate still means 50,000 frozen user sessions.'"
        )
    },
    {
        "id": "ARCHITECTURE_TRADE_OFF",
        "name": "Direct Architecture Trade-off / Decision",
        "instruction": (
            "Open with a direct architectural choice between two patterns, highlighting the trade-off. "
            "Example: 'MVI vs MVVM in Jetpack Compose: The moment your screen needs single-shot events (navigation, snackbars), a single StateFlow will eventually betray you without a dedicated event channel.' "
            "or 'ExoPlayer's default 50-second buffer is great for home WiFi, but on mobile cellular networks, it's an OutOfMemory waiting to happen.'"
        )
    },
    {
        "id": "UNDER_THE_HOOD",
        "name": "Under-the-Hood Android OS Internals",
        "instruction": (
            "Explain an Android OS / Linux kernel mechanism that developers overlook. "
            "Example: 'Android's Low Memory Killer doesn't throw an OutOfMemoryError. It silently issues a SIGKILL to your background cached processes based on oom_adj_score.' "
            "or 'Why Jetpack WindowManager uses a reactive Kotlin Flow instead of a standard callback for hinge posture detection.'"
        )
    },
    {
        "id": "DEBUGGING_WAR_STORY",
        "name": "Grounded Debugging Insight",
        "instruction": (
            "Start in the middle of a hard-to-trace bug without fake storytelling or dramatic dates. "
            "Example: 'We spent hours debugging a memory leak in a Compose list, only to find the root cause was an unstable lambdas capturing an outer class reference.' "
            "or 'If your BLE peripheral disconnects after exactly 30 seconds, your MTU request was never completed.'"
        )
    },
    {
        "id": "TOOLING_VS_REALITY",
        "name": "Tooling vs Production Reality",
        "instruction": (
            "Highlight the gap between Android Studio emulators/profilers and physical devices in the wild. "
            "Example: 'Your app might run at a smooth 60fps on a Pixel emulator, but low-end OEM chipsets handle thread scheduling and hardware bitmap allocation completely differently.'"
        )
    },
    {
        "id": "PRAGMATIC_HOW_TO",
        "name": "Pragmatic Architecture Rule of Thumb",
        "instruction": (
            "Start with a definitive rule of thumb learned from building large Android codebases. "
            "Example: 'Rule of thumb for multi-module Gradle setups: if feature-A needs a data model from feature-B, you don't add a dependency—you extract a core-model module.' "
        )
    }
]

def select_hook_formula(day_of_year: int = 0, slot_index: int = 0) -> dict:
    """Select a diverse hook style based on hash or random rotation to guarantee variety."""
    idx = (day_of_year + slot_index + random.randint(0, len(HOOK_STYLES) - 1)) % len(HOOK_STYLES)
    return HOOK_STYLES[idx]
