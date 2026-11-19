"""
Trending Android / tech-news fetcher.

Pulls recent headlines from Google News RSS + Hacker News (Algolia),
filtered to Android/mobile engineering relevance.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import requests

from scripts.services.rss_fetcher import clean_html

GOOGLE_NEWS_QUERIES = [
    "Android developer OR Jetpack Compose OR Kotlin Multiplatform when:7d",
    "Android 15 OR Android 16 OR 16KB page size Play Console when:7d",
    "Android Studio OR Gemini Nano OR on-device AI Android when:7d",
    "Play Store policy OR Android security CVE OR biometric Android when:7d",
]

HN_QUERIES = [
    "Android",
    "Jetpack Compose",
    "Kotlin Multiplatform",
    "Play Store",
]

# Strong signals only — avoid weak matches like generic "mobile"/"AI"
ANDROID_HINTS = {
    "android", "kotlin", "jetpack", "compose", "play store", "play console",
    "pixel", "aosp", "android studio", "gradle", "firebase", "gemini nano",
    "on-device ai", "16kb", "android 15", "android 16", "material you",
    "kotlin multiplatform", "kmp",
}


class TrendFetcher:
    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "AutonomousLinkedInAgent/1.0 (Android Trend Monitor)"
        }

    def fetch_trending(self, limit: int = 25) -> list[dict]:
        items: list[dict] = []
        items.extend(self._fetch_google_news())
        items.extend(self._fetch_hacker_news())

        # De-dupe by normalized title
        seen = set()
        unique = []
        for it in items:
            key = re.sub(r"\W+", "", it["title"].lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)

        # Prefer Google/news wires over noisy HN Show HN, then score
        def _rank(item: dict) -> tuple:
            src = item.get("source", "")
            news_wire = 1 if "Google News" in src or "Authority" in src or "Police" in src else 0
            return (news_wire, item.get("trend_score", 0))

        unique.sort(key=_rank, reverse=True)
        return unique[:limit]

    def _fetch_google_news(self) -> list[dict]:
        import feedparser

        out = []
        for q in GOOGLE_NEWS_QUERIES:
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
            )
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code != 200:
                    print(f"  [Trend] Google News HTTP {resp.status_code} for query")
                    continue
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:8]:
                    title = clean_html(entry.get("title", ""))
                    summary = clean_html(entry.get("summary", entry.get("description", "")))
                    if not title or not self._is_androidish(f"{title} {summary}"):
                        continue
                    out.append({
                        "title": title,
                        "summary": (summary or title)[:600],
                        "source": "Google News (Trending)",
                        "category": "breaking_news",
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "trend_score": self._score(title, summary, base=0.85),
                    })
            except Exception as e:
                print(f"  [Trend] Google News error: {e}")
        print(f"  [Trend] Google News candidates: {len(out)}")
        return out

    def _fetch_hacker_news(self) -> list[dict]:
        out = []
        for q in HN_QUERIES:
            url = (
                "https://hn.algolia.com/api/v1/search_by_date"
                f"?query={quote_plus(q)}&tags=story&hitsPerPage=8"
            )
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for hit in data.get("hits", []):
                    title = clean_html(hit.get("title") or "")
                    summary = clean_html(hit.get("story_text") or hit.get("url") or title)
                    if not title or not self._is_androidish(f"{title} {summary}"):
                        continue
                    points = int(hit.get("points") or 0)
                    out.append({
                        "title": title,
                        "summary": summary[:600],
                        "source": "Hacker News",
                        "category": "breaking_news",
                        "link": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                        "published": hit.get("created_at", ""),
                        "trend_score": self._score(title, summary, base=0.70) + min(0.2, points / 500.0),
                    })
            except Exception as e:
                print(f"  [Trend] HN error: {e}")
        print(f"  [Trend] Hacker News candidates: {len(out)}")
        return out

    def _is_androidish(self, text: str) -> bool:
        t = text.lower()
        if not any(h in t for h in ANDROID_HINTS):
            return False
        # Drop consumer phone-spec rumor spam (not useful for engineering posts)
        spam = (
            "specs:", " surfaces in ", "appears on google play console with",
            "dimensity", "snapdragon", "gb ram", "mah battery", "launched in",
        )
        if any(s in t for s in spam) and not any(
            k in t for k in ("16kb", "compose", "kotlin", "studio", "policy", "cve", "gemini", "developer")
        ):
            return False
        return True

    def _score(self, title: str, summary: str, base: float = 0.7) -> float:
        text = f"{title} {summary}".lower()
        bump = 0.0
        for token in (
            "android 16", "android 15", "16kb", "play console", "compose",
            "kotlin", "gemini", "security", "cve", "policy", "pixel", "studio",
        ):
            if token in text:
                bump += 0.04
        # Freshness hint if published today-ish string present
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today in text:
            bump += 0.05
        return min(1.0, base + bump)
