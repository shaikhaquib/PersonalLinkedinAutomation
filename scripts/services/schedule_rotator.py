"""
Schedule Rotator — 3 posts/week (Mon / Wed / Fri) with day content pillars.
"""

from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Only these weekdays auto-publish (Mon=0, Wed=2, Fri=4)
PUBLISH_WEEKDAYS = (0, 2, 4)

WEEKDAY_ROTATION = {
    0: {  # Monday — Android engineering
        "day_name": "Monday",
        "pillar": "android",
        "publishes": True,
        "theme_name": "Android Engineering",
        "preferred_archetype": "SCALE_INCIDENT_WAR_STORY",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Android production / Compose / Kotlin / Play — content-aware card",
        "topic_hints": [
            "android", "kotlin", "compose", "jetpack", "anr", "crash", "jank",
            "play console", "gradle", "room", "coroutines", "architecture",
        ],
        "topic_boost": [
            "compose", "kotlin", "anr", "crash", "play", "gradle", "room",
            "viewmodel", "jank", "startup", "16kb", "baseline profile",
        ],
    },
    1: {  # Tuesday — no publish
        "day_name": "Tuesday",
        "pillar": "off",
        "publishes": False,
        "theme_name": "No Publish",
        "preferred_archetype": "CODE_AUTOPSY_TEARDOWN",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Skip — weekly cadence is Mon/Wed/Fri only",
        "topic_hints": [],
        "topic_boost": [],
    },
    2: {  # Wednesday — AI for Android / AI development
        "day_name": "Wednesday",
        "pillar": "ai_android",
        "publishes": True,
        "theme_name": "AI for Android",
        "preferred_archetype": "OS_INTERNALS_DEEP_DIVE",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "AI growing + on-device / Gemini / ML for Android — content-aware card",
        "topic_hints": [
            "ai", "gemini", "gemini nano", "on-device", "aicore", "ml kit",
            "llm", "genai", "mediapipe", "android ai",
        ],
        "topic_boost": [
            "gemini", "nano", "aicore", "on-device", "ml kit", "llm", "genai",
            "mediapipe", "ai", "inference",
        ],
    },
    3: {  # Thursday — no publish
        "day_name": "Thursday",
        "pillar": "off",
        "publishes": False,
        "theme_name": "No Publish",
        "preferred_archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Skip — weekly cadence is Mon/Wed/Fri only",
        "topic_hints": [],
        "topic_boost": [],
    },
    4: {  # Friday — trending tech news
        "day_name": "Friday",
        "pillar": "tech_news",
        "publishes": True,
        "theme_name": "Trending Tech News",
        "preferred_archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Trending tech / Apple AI / layoffs / platform news — content-aware card",
        "topic_hints": [
            "apple", "openai", "layoff", "funding", "policy", "regulation",
            "breaking", "launch", "wwdc", "pixel", "samsung", "ai news",
        ],
        "topic_boost": [
            "apple", "openai", "layoff", "layoffs", "breaking", "launch",
            "pixel", "samsung", "policy", "funding", "wwdc", "google i/o",
        ],
    },
    5: {  # Saturday — no publish
        "day_name": "Saturday",
        "pillar": "off",
        "publishes": False,
        "theme_name": "No Publish",
        "preferred_archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Skip — weekly cadence is Mon/Wed/Fri only",
        "topic_hints": [],
        "topic_boost": [],
    },
    6: {  # Sunday — no publish
        "day_name": "Sunday",
        "pillar": "off",
        "publishes": False,
        "theme_name": "No Publish",
        "preferred_archetype": "SCALE_INCIDENT_WAR_STORY",
        "template": "aware_graphic_dark.html.j2",
        "theme": "dark",
        "format_desc": "Skip — weekly cadence is Mon/Wed/Fri only",
        "topic_hints": [],
        "topic_boost": [],
    },
}

# Manual posts already shipped — never regenerate these themes
BLOCKED_TOPIC_PHRASES = (
    "upi",
    "mdr",
    "merchant discount",
    "foldable",
    "fold was already",
    "the fold",
    "apple fold",
    "galaxy fold",
    "windowsizeclass fold",
)


def get_weekday_rotation(dt: datetime = None, tz_name: str = "Asia/Kolkata") -> dict:
    """Returns the visual format and pillar rule for the given date (default: today IST)."""
    if dt is None:
        try:
            dt = datetime.now(ZoneInfo(tz_name))
        except Exception:
            dt = datetime.now()
    return WEEKDAY_ROTATION[dt.weekday()]


def is_publish_day(dt: datetime = None, tz_name: str = "Asia/Kolkata") -> bool:
    """True only on Monday / Wednesday / Friday."""
    rotation = get_weekday_rotation(dt, tz_name)
    return bool(rotation.get("publishes"))


def is_blocked_topic(text: str) -> bool:
    """True if topic matches already-posted manual themes (UPI / fold)."""
    blob = (text or "").lower()
    return any(p in blob for p in BLOCKED_TOPIC_PHRASES)
