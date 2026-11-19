"""
Topic Analyzer — pain-first, engagement-oriented scoring for mid–senior Android audience.

Prioritizes felt production problems people notice (ANR, crash, jank, Play reject,
battery, payment fail) over ultra-niche OS internals that get zero feed engagement.
"""

import re
import json

ANDROID_MOBILE_GATEWAY_KEYWORDS = {
    "android", "mobile", "kotlin", "compose", "jetpack", "kmp", "aosp", "ndk",
    "apk", "aar", "gradle", "play store", "google play", "play console",
}

ANDROID_CORE_KEYWORDS = {
    "compose", "jetpack", "kotlin", "coroutine", "flow", "viewmodel", "lifecycle",
    "architecture", "stateflow", "kmp", "multiplatform", "navigation", "hilt",
    "aosp", "ndk", "art", "binder", "lmk", "anr", "crash", "page size", "16kb",
    "memory", "gc", "doze", "foreground service", "android 15", "android 16",
    "r8", "proguard", "gradle", "k2", "baseline profile", "startup", "macrobenchmark",
    "jank", "leakcanary", "profiler",
    "ble", "bluetooth", "gatt", "exoplayer", "media3", "camerax", "camera",
    "nfc", "on-device", "gemini nano", "aicore", "foldable", "adaptive", "sensor",
    "security", "keystore", "biometric", "masvs", "integrity", "room", "datastore",
    "workmanager", "idempotency", "pinning", "okhttp", "ktor", "play", "policy",
}

# Problems mid–senior engineers actually feel and debate on LinkedIn
FELT_PAIN_KEYWORDS = {
    "anr", "crash", "jank", "freeze", "frozen", "lag", "slow", "battery", "drain",
    "oom", "memory leak", "leak", "play reject", "policy", "review rejected",
    "payment", "double charge", "process death", "recomposition", "startup",
    "cold start", "build time", "ci", "flake", "flaky", "timeout", "outage",
    "production", "users complain", "app store", "rating", "hotfix", "regression",
    "security", "breach", "pii", "biometric", "login", "offline", "sync",
    "notification", "background kill", "doze", "permission", "privacy",
}

# Ultra-niche internals — keep only when paired with felt pain
ULTRA_NICHE_KEYWORDS = {
    "hal3", "hardwarebuffer", "surfaceflinger", "vsync latch", "binder pool",
    "oom_adj", "fluoride", "att layer", "elf .so", "load segment", "choreographer",
    "generative ui schema", "untyped agent schema", "native surface pipeline",
    "yuv frames", "graphic buffers", "frame latching",
    "kernel memory", "aosp runtime", "gc pause", "under the hood", "art gc",
}

DIGEST_OR_RELEASE_ONLY = {
    "weekly issue", "android weekly", "newsletter", "roundup", "this week in",
    "release notes", "changelog digest",
}

TREND_SIGNAL_KEYWORDS = {
    "breaking", "deprecated", "migration", "vulnerability", "cve", "outage",
    "banned", "policy change", "mandatory", "deadline", "android 16", "android 15",
    "play console", "16kb", "page size", "compose bom", "kmp", "gemini",
    "on-device", "controversy", "debate", "why you should", "stop using",
}

GENERIC_HYPE_KEYWORDS = {
    "revolutionary", "game changer", "unlock the power", "10x your productivity",
    "chatgpt prompts", "make money with ai", "crypto moon", "stock market",
    "valuation",
}

# Already posted manually — never score these for regeneration
BLOCKED_TOPIC_PHRASES = {
    "upi", "mdr", "merchant discount", "foldable", "fold was already",
    "the fold", "apple fold", "galaxy fold",
}

TECH_NEWS_KEYWORDS = {
    "apple", "openai", "layoff", "layoffs", "funding", "wwdc", "pixel",
    "samsung", "breaking", "launch", "acquisition", "regulation", "antitrust",
    "chatgpt", "gemini", "siri", "copilot", "ai news",
}

AI_ANDROID_KEYWORDS = {
    "gemini", "gemini nano", "aicore", "on-device", "ml kit", "mediapipe",
    "llm", "genai", "android ai", "ai core", "inference", "npu",
}


class TopicAnalyzer:
    def __init__(self, min_score: float = 0.65):
        self.min_score = min_score

    def score_heuristic(self, title: str, summary: str, source: str, pillar: str = "android") -> dict:
        text = f"{title} {summary}".lower()
        words = set(re.findall(r"\b[a-z0-9_-]+\b", text))

        if any(p in text for p in BLOCKED_TOPIC_PHRASES):
            return {
                "overall_score": 0.05,
                "relevance": 0.05,
                "freshness": 0.10,
                "technical_value": 0.05,
                "originality": 0.05,
                "personal_relevance": 0.05,
                "pain_score": 0.05,
                "blocked": True,
            }

        has_mobile_anchor = (
            any(k in text for k in ANDROID_MOBILE_GATEWAY_KEYWORDS)
            or any(k in words for k in ANDROID_CORE_KEYWORDS)
        )
        has_ai_anchor = any(k in text for k in AI_ANDROID_KEYWORDS) or "ai" in words
        has_tech_news_anchor = any(k in text for k in TECH_NEWS_KEYWORDS)

        # Friday tech-news pillar can rank broader industry news; other days stay mobile-first.
        if pillar == "tech_news":
            if not (has_mobile_anchor or has_tech_news_anchor or has_ai_anchor):
                return {
                    "overall_score": 0.20,
                    "relevance": 0.20,
                    "freshness": 0.50,
                    "technical_value": 0.20,
                    "originality": 0.30,
                    "personal_relevance": 0.10,
                    "pain_score": 0.10,
                }
        elif pillar == "ai_android":
            if not (has_ai_anchor or has_mobile_anchor):
                return {
                    "overall_score": 0.22,
                    "relevance": 0.22,
                    "freshness": 0.50,
                    "technical_value": 0.20,
                    "originality": 0.30,
                    "personal_relevance": 0.15,
                    "pain_score": 0.10,
                }
        elif not has_mobile_anchor:
            return {
                "overall_score": 0.20,
                "relevance": 0.20,
                "freshness": 0.50,
                "technical_value": 0.20,
                "originality": 0.30,
                "personal_relevance": 0.10,
                "pain_score": 0.10,
            }

        # Reject pure digests / newsletter roundups
        if any(d in text for d in DIGEST_OR_RELEASE_ONLY):
            return {
                "overall_score": 0.35,
                "relevance": 0.40,
                "freshness": 0.40,
                "technical_value": 0.30,
                "originality": 0.25,
                "personal_relevance": 0.30,
                "pain_score": 0.20,
            }

        core_matches = len(words.intersection(ANDROID_CORE_KEYWORDS))
        relevance = min(1.0, 0.45 + (core_matches * 0.10))
        if any(bad in text for bad in GENERIC_HYPE_KEYWORDS):
            relevance *= 0.3
        # Friday may cover layoffs / industry moves — don't treat as spam that day
        if pillar == "tech_news" and any(k in text for k in ("layoff", "layoffs", "funding")):
            relevance = max(relevance, 0.72)
            freshness_boost = True
        else:
            freshness_boost = False

        if pillar == "ai_android" and has_ai_anchor:
            relevance = max(relevance, 0.86)
            pain_score_floor = 0.55
        else:
            pain_score_floor = 0.0
        if pillar == "android" and has_mobile_anchor:
            relevance = max(relevance, 0.78)

        pain_hits = sum(1 for k in FELT_PAIN_KEYWORDS if k in text)
        pain_score = min(1.0, 0.35 + pain_hits * 0.18)
        if pain_score_floor:
            pain_score = max(pain_score, pain_score_floor)

        niche_hits = sum(1 for k in ULTRA_NICHE_KEYWORDS if k in text)
        if niche_hits and pain_hits == 0:
            # Ultra-niche with no felt pain → engagement poison
            pain_score = min(pain_score, 0.35)
            relevance *= 0.75

        trend_hits = sum(1 for k in TREND_SIGNAL_KEYWORDS if k in text)
        is_release_noise = any(
            t in text for t in ("release notes", "what's new in", "announcing")
        ) and pain_hits == 0
        freshness = 0.55 if is_release_noise else min(1.0, 0.55 + trend_hits * 0.12)
        if freshness_boost:
            freshness = max(freshness, 0.88)
        if any(term in text for term in ("breaking", "vulnerability", "deadline", "mandatory", "policy")):
            freshness = max(freshness, 0.92)
        if pillar == "tech_news" and has_tech_news_anchor:
            freshness = max(freshness, 0.90)

        # Practical value for mid–senior audience (not kernel-paper depth)
        practical = any(
            t in text
            for t in (
                "how to", "fix", "avoid", "stop", "why", "mistake", "anti-pattern",
                "crash", "anr", "jank", "production", "play", "users",
            )
        )
        tech_value = 0.88 if practical or pain_hits else 0.62
        if niche_hits and not pain_hits:
            tech_value = 0.55

        is_beginner = any(
            b in text
            for b in ("getting started", "introduction to", "basics of", "for beginners", "hello world")
        )
        originality = 0.45 if is_beginner else (0.88 if pain_hits else 0.72)

        broad_domains = {
            "compose", "performance", "security", "architecture", "crash", "anr",
            "jank", "battery", "play", "payment", "biometric", "startup", "gradle",
            "notification", "offline", "kmp", "ai", "nano",
        }
        personal_relevance = 0.92 if any(k in words or k in text for k in broad_domains) else 0.70

        source_l = (source or "").lower()
        if any(s in source_l for s in (
            "google news", "hacker news", "android authority", "android police",
            "9to5", "the verge", "ars technica", "breaking",
        )):
            freshness = max(freshness, 0.92)
            overall_boost = 0.06
        else:
            overall_boost = 0.0

        overall = (
            relevance * 0.16
            + freshness * 0.22
            + tech_value * 0.12
            + originality * 0.10
            + personal_relevance * 0.12
            + pain_score * 0.28
            + overall_boost
        )

        return {
            "overall_score": round(min(1.0, overall), 3),
            "relevance": round(relevance, 2),
            "freshness": round(freshness, 2),
            "technical_value": round(tech_value, 2),
            "originality": round(originality, 2),
            "personal_relevance": round(personal_relevance, 2),
            "pain_score": round(pain_score, 2),
        }

    def score_with_llm(self, title: str, summary: str, llm_generate_fn) -> dict:
        prompt = f"""
You evaluate topics for Aquib Shaikh's LinkedIn — mid to senior Android engineers and mobile leads.
Prefer topics with a FELT user/dev problem people will comment on. Penalize ultra-niche OS papers
with no production pain. Reject newsletters/digests.

Topic: {title}
Summary: {summary}

Return ONLY JSON scores 0.0–1.0:
{{
  "relevance": 0.85,
  "freshness": 0.80,
  "technical_value": 0.85,
  "originality": 0.75,
  "personal_relevance": 0.90,
  "pain_score": 0.88
}}
"""
        try:
            raw = llm_generate_fn(prompt, "You are an expert LinkedIn engagement editor for Android engineering.")
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                rel = float(data.get("relevance", 0.7))
                fresh = float(data.get("freshness", 0.7))
                tech = float(data.get("technical_value", 0.7))
                orig = float(data.get("originality", 0.7))
                pers = float(data.get("personal_relevance", 0.7))
                pain = float(data.get("pain_score", 0.6))
                overall = (
                    rel * 0.18 + fresh * 0.18 + tech * 0.14 + orig * 0.12 + pers * 0.13 + pain * 0.25
                )
                return {
                    "overall_score": round(overall, 3),
                    "relevance": rel,
                    "freshness": fresh,
                    "technical_value": tech,
                    "originality": orig,
                    "personal_relevance": pers,
                    "pain_score": pain,
                }
        except Exception:
            pass

        return self.score_heuristic(title, summary, "")

    def rank_candidates(
        self,
        candidates: list[dict],
        min_threshold: float = None,
        pillar: str = "android",
        topic_boost: list[str] | None = None,
    ) -> list[dict]:
        threshold = min_threshold if min_threshold is not None else self.min_score
        boost_terms = [t.lower() for t in (topic_boost or [])]
        scored = []
        for c in candidates:
            score_data = self.score_heuristic(
                c["title"], c["summary"], c.get("source", ""), pillar=pillar
            )
            if score_data.get("blocked"):
                continue
            blob = f"{c.get('title', '')} {c.get('summary', '')}".lower()
            if boost_terms and any(t in blob for t in boost_terms):
                score_data["overall_score"] = round(min(1.0, score_data["overall_score"] + 0.08), 3)
                score_data["pillar_match"] = True
            if score_data["overall_score"] >= threshold:
                item = dict(c)
                item.update(score_data)
                scored.append(item)

        scored.sort(
            key=lambda x: (x.get("pillar_match", False), x.get("pain_score", 0), x["overall_score"]),
            reverse=True,
        )
        return scored
