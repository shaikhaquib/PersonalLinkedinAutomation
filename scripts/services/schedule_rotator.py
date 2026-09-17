"""
Schedule Rotator: Enforces daily format and visual diversity.
Ensures consecutive posts never use the same format, archetype, or visual theme.

Weekly Matrix:
- Monday:    Architecture Blueprint Flow (Dark) — Scale & System Incidents
- Tuesday:   Code Autopsy & Refactoring (Dark)  — Before/After Kotlin Teardowns
- Wednesday: Editorial Blueprint (Light)        — OS Internals & Breaking Android News
- Thursday:  Contrarian Code Card (Light)       — Anti-Patterns & Architecture Debates
- Friday:    Hardware & Low-Level Flow (Dark)   — BLE, Media3, NDK, Protocol Deep Dives
"""

from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

WEEKDAY_ROTATION = {
    0: {  # Monday
        "day_name": "Monday",
        "theme_name": "System Architecture Blueprint",
        "preferred_archetype": "SCALE_INCIDENT_WAR_STORY",
        "template": "process_infographic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Dark 3-Node Architecture Flow Blueprint"
    },
    1: {  # Tuesday
        "day_name": "Tuesday",
        "theme_name": "Code Autopsy & Refactoring",
        "preferred_archetype": "CODE_AUTOPSY_TEARDOWN",
        "template": "code_card_dark.html.j2",
        "theme": "dark",
        "format_desc": "Dark Before vs After Kotlin Syntax-Highlighted Code Card"
    },
    2: {  # Wednesday
        "day_name": "Wednesday",
        "theme_name": "Trending Tech & OS Internals",
        "preferred_archetype": "OS_INTERNALS_DEEP_DIVE",
        "template": "process_infographic_light.html.j2",
        "theme": "light",
        "format_desc": "Editorial Light System Mechanism Blueprint"
    },
    3: {  # Thursday
        "day_name": "Thursday",
        "theme_name": "Contrarian Architecture Teardown",
        "preferred_archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "template": "code_card_light.html.j2",
        "theme": "light",
        "format_desc": "Light Modern Code & Pattern Comparison Card"
    },
    4: {  # Friday
        "day_name": "Friday",
        "theme_name": "Hardware, Media & Protocol Deep Dive",
        "preferred_archetype": "HARDWARE_LOW_LEVEL_DEEP_DIVE",
        "template": "process_infographic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Dark Hardware/Protocol Low-Level Architecture Flow"
    },
    5: {  # Saturday
        "day_name": "Saturday",
        "theme_name": "Mobile Engineering Leadership & Philosophy",
        "preferred_archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "template": "process_infographic_light.html.j2",
        "theme": "light",
        "format_desc": "Editorial Weekend Thought Leadership Card"
    },
    6: {  # Sunday
        "day_name": "Sunday",
        "theme_name": "Weekly Android Engineering Review",
        "preferred_archetype": "SCALE_INCIDENT_WAR_STORY",
        "template": "process_infographic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Dark High-Scale Recap Blueprint"
    }
}


def get_weekday_rotation(dt: datetime = None, tz_name: str = "Asia/Kolkata") -> dict:
    """Returns the visual format and archetype rotation rule for the given date (default: today IST)."""
    if dt is None:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = None
        dt = datetime.now(tz) if tz else datetime.now()

    weekday = dt.weekday()
    return WEEKDAY_ROTATION.get(weekday, WEEKDAY_ROTATION[0])
