"""
Topic Analyzer & Scorer for Senior Android & Mobile Engineering.
Evaluates candidate topics against relevance, freshness, technical depth,
and mobile engineering authority.
Guarantees 100% Android/Mobile relevance while exploring the full breadth of
the mobile ecosystem (OS internals, On-Device AI, Compose, Hardware/BLE, Media, Architecture).
"""

import re
import json

ANDROID_MOBILE_GATEWAY_KEYWORDS = {
    "android", "mobile", "kotlin", "compose", "jetpack", "kmp", "aosp", "ndk",
    "apk", "aar", "gradle", "play store", "google play"
}

ANDROID_CORE_KEYWORDS = {
    # Core Architecture & Modern Android
    "compose", "jetpack", "kotlin", "coroutine", "flow", "viewmodel", "lifecycle",
    "architecture", "stateflow", "kmp", "multiplatform", "navigation", "hilt",
    # OS & Runtime Internals (Android 15/16)
    "aosp", "ndk", "art", "binder", "lmk", "anr", "crash", "page size", "16kb",
    "memory", "gc", "doze", "foreground service", "android 15", "android 16",
    # Tooling, Build & Runtime Performance
    "r8", "proguard", "gradle", "k2", "baseline profile", "startup", "macrobenchmark",
    "jank", "leakcanary", "profiler",
    # Hardware, Media & Emerging Mobile Tech
    "ble", "bluetooth", "gatt", "exoplayer", "media3", "camerax", "camera",
    "nfc", "on-device", "gemini nano", "aicore", "foldable", "adaptive", "sensor",
    # Security, Network & Persistence
    "security", "keystore", "biometric", "masvs", "integrity", "room", "datastore",
    "workmanager", "idempotency", "pinning", "okhttp", "ktor"
}

HIGH_IMPACT_TREND_INDICATORS = {
    "breaking", "deprecated", "migration", "crash", "outage", "vulnerability",
    "under the hood", "internals", "optimization", "deep dive", "stable",
    "release", "alpha", "beta", "new in", "announcing", "architecture"
}

GENERIC_HYPE_KEYWORDS = {
    "revolutionary", "game changer", "unlock the power", "10x your productivity",
    "chatgpt prompts", "make money with ai", "crypto moon", "stock market",
    "funding round", "layoffs", "valuation"
}


class TopicAnalyzer:
    def __init__(self, min_score: float = 0.70):
        self.min_score = min_score

    def score_heuristic(self, title: str, summary: str, source: str) -> dict:
        text = f"{title} {summary}".lower()
        words = set(re.findall(r"\b[a-z0-9_-]+\b", text))

        # 0. Mobile Gateway Check: Must have clear Android or Mobile connection
        has_mobile_anchor = any(k in text for k in ANDROID_MOBILE_GATEWAY_KEYWORDS) or any(k in words for k in ANDROID_CORE_KEYWORDS)
        if not has_mobile_anchor:
            # Non-mobile content is rejected
            return {
                "overall_score": 0.20,
                "relevance": 0.20,
                "freshness": 0.50,
                "technical_value": 0.20,
                "originality": 0.30,
                "personal_relevance": 0.10
            }

        # 1. Relevance Score (0.0 to 1.0)
        core_matches = len(words.intersection(ANDROID_CORE_KEYWORDS))
        relevance = min(1.0, 0.45 + (core_matches * 0.12))
        if any(bad in text for bad in GENERIC_HYPE_KEYWORDS):
            relevance *= 0.3

        # 2. Freshness Score (0.0 to 1.0) - Boost breaking changes and releases
        is_trending = any(term in text for term in ["release", "update", "alpha", "beta", "stable", "announcing", "new in", "breaking"])
        freshness = 0.90 if is_trending else 0.75

        # 3. Technical Value Score (0.0 to 1.0) - Deep dives, internals, architecture
        has_tech = any(indicator in text for indicator in HIGH_IMPACT_TREND_INDICATORS)
        tech_value = 0.90 if has_tech else 0.72

        # 4. Originality Score (0.0 to 1.0) - Avoid generic beginner tutorials
        is_beginner = any(b in text for b in ["getting started", "introduction to", "basics of", "for beginners", "hello world"])
        originality = 0.50 if is_beginner else 0.85

        # 5. Personal / Senior Mobile Authority (0.0 to 1.0)
        high_value_domains = {"compose", "performance", "security", "architecture", "ble", "media3", "16kb", "art", "kmp", "ai", "nano", "aicore", "exoplayer"}
        personal_relevance = 0.95 if any(k in words for k in high_value_domains) else 0.75

        # Overall weighted score
        overall = (
            relevance * 0.30 +
            freshness * 0.20 +
            tech_value * 0.20 +
            originality * 0.15 +
            personal_relevance * 0.15
        )

        return {
            "overall_score": round(overall, 3),
            "relevance": round(relevance, 2),
            "freshness": round(freshness, 2),
            "technical_value": round(tech_value, 2),
            "originality": round(originality, 2),
            "personal_relevance": round(personal_relevance, 2)
        }

    def score_with_llm(self, title: str, summary: str, llm_generate_fn) -> dict:
        """Optional deep scoring with Gemini when ambiguity exists."""
        prompt = f"""
You are evaluating a candidate topic for a Senior Android Developer's LinkedIn post.
The post must be 100% about Android or Mobile engineering.
Topic: {title}
Summary: {summary}

Evaluate and return ONLY valid JSON with scores between 0.0 and 1.0:
{{
  "relevance": 0.85,
  "freshness": 0.80,
  "technical_value": 0.85,
  "originality": 0.75,
  "personal_relevance": 0.90
}}
"""
        try:
            raw = llm_generate_fn(prompt, "You are an expert technical content evaluator.")
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                rel = float(data.get("relevance", 0.7))
                fresh = float(data.get("freshness", 0.7))
                tech = float(data.get("technical_value", 0.7))
                orig = float(data.get("originality", 0.7))
                pers = float(data.get("personal_relevance", 0.7))
                overall = (rel * 0.30 + fresh * 0.20 + tech * 0.20 + orig * 0.15 + pers * 0.15)
                return {
                    "overall_score": round(overall, 3),
                    "relevance": rel,
                    "freshness": fresh,
                    "technical_value": tech,
                    "originality": orig,
                    "personal_relevance": pers
                }
        except Exception:
            pass

        return self.score_heuristic(title, summary, "")

    def rank_candidates(self, candidates: list[dict], min_threshold: float = None) -> list[dict]:
        threshold = min_threshold if min_threshold is not None else self.min_score
        scored = []
        for c in candidates:
            score_data = self.score_heuristic(c["title"], c["summary"], c.get("source", ""))
            if score_data["overall_score"] >= threshold:
                item = dict(c)
                item.update(score_data)
                scored.append(item)

        scored.sort(key=lambda x: x["overall_score"], reverse=True)
        return scored
