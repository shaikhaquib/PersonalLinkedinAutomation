"""
RSS and Atom feed aggregator for Android and engineering sources.
"""

import os
import json
import re
import feedparser
import requests

HTML_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = HTML_TAG_RE.sub(" ", raw_html)
    return re.sub(r"\s+", " ", text).strip()


class RSSFetcher:
    def __init__(self, sources_path: str = None):
        if sources_path is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sources_path = os.path.join(root, "config", "sources.json")
        self.sources_path = sources_path
        self.sources = self._load_sources()

    def _load_sources(self) -> list[dict]:
        if not os.path.exists(self.sources_path):
            return []
        try:
            with open(self.sources_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sources", [])
        except Exception as e:
            print(f"[WARN] Failed to load sources from {self.sources_path}: {e}")
            return []

    def fetch_all(self, max_items_per_source: int = 10) -> list[dict]:
        candidates = []
        headers = {
            "User-Agent": "AutonomousLinkedInAgent/1.0 (Android Engineering News Aggregator)"
        }

        for source in self.sources:
            name = source.get("name")
            url = source.get("url")
            category = source.get("category", "android")

            if not url:
                continue

            try:
                # Fetch with explicit timeout to avoid hanging indefinitely
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code != 200:
                    print(f"  [RSS] Skip {name} (HTTP {resp.status_code})")
                    continue

                feed = feedparser.parse(resp.content)
                if feed.bozo and not feed.entries:
                    print(f"  [RSS] Parse warning on {name}: {feed.bozo_exception}")
                    continue

                items_added = 0
                for entry in feed.entries[:max_items_per_source]:
                    title = clean_html(entry.get("title", ""))
                    summary = clean_html(entry.get("summary", entry.get("description", "")))
                    link = entry.get("link", "")
                    published = entry.get("published", entry.get("updated", ""))

                    if not title or len(title) < 8:
                        continue

                    candidates.append({
                        "title": title,
                        "summary": summary[:600],
                        "source": name,
                        "category": category,
                        "link": link,
                        "published": published
                    })
                    items_added += 1

                print(f"  [RSS] Fetched {items_added} items from {name}")

            except Exception as e:
                print(f"  [RSS] Error fetching {name} ({url}): {e}. Continuing with other sources...")
                continue

        return candidates
