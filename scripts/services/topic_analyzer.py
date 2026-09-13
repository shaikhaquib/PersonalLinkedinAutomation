"""
Topic Analyzer & Scorer.
Evaluates candidate topics against relevance, freshness, technical depth, and persona fit.
"""

import re
import json

ANDROID_CORE_KEYWORDS = {
    "compose", "jetpack", "kotlin", "coroutine", "flow", "viewmodel", "lifecycle",
    "architecture", "security", "keystore", "biometric", "performance", "jank",
    "startup", "baseline", "profile", "gradle", "k2", "room", "workmanager",
    "memory", "leak", "r8", "proguard", "fintech", "banking", "idempotency",
    "crypto", "ipc", "binder", "ndk", "aosp", "masvs", "owasp", "cert", "pinning"
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
        words = set(re.findall(r"\b[a-z0-9]+\b", text))

        # 1. Relevance Score (0.0 to 1.0)
        core_matches = len(words.intersection(ANDROID_CORE_KEYWORDS))
        relevance = min(1.0, 0.4 + (core_matches * 0.15))
        if any(bad in text for bad in GENERIC_HYPE_KEYWORDS):
            relevance *= 0.3

        # 2. Freshness Score (0.0 to 1.0)
        # RSS feeds typically contain current content; boost official release notes or announcements
        freshness = 0.85 if any(term in text for term in ["release", "update", "alpha", "beta", "stable", "announcing", "new in"]) else 0.75

        # 3. Technical Value Score (0.0 to 1.0)
        # High value for architectural, performance, and deep engineering topics
        tech_indicators = ["how", "internals", "optimization", "architecture", "migration", "fix", "pattern", "under the hood", "deep dive"]
        has_tech = any(indicator in text for indicator in tech_indicators)
        tech_value = 0.85 if has_tech else 0.70

        # 4. Originality Score (0.0 to 1.0)
        # Avoid generic "Getting started" posts
        is_beginner = any(b in text for b in ["getting started", "introduction to", "basics of", "for beginners"])
        originality = 0.60 if is_beginner else 0.80

        # 5. Personal Relevance Score (0.0 to 1.0)
        # Senior Android developer fit
        personal_relevance = 0.90 if any(k in words for k in ["kotlin", "compose", "performance", "security", "architecture", "fintech"]) else 0.65

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
            # extract json block
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
