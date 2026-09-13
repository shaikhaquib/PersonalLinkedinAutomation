"""
History and duplicate management using SQLite.
Stores persistent state across agent runs.
"""

import os
import sqlite3
import hashlib
import re
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


class HistoryManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(root, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "content_history.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    linkedin_post_id TEXT,
                    has_image INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'published'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attempted_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    score REAL,
                    decision TEXT,
                    attempted_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def compute_hash(text: str) -> str:
        clean = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(clean.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_title(title: str) -> set:
        words = re.findall(r"\b[a-z0-9]+\b", title.lower())
        stop_words = {"the", "a", "an", "in", "on", "at", "for", "to", "of", "and", "or", "is", "it", "how", "why"}
        return set(w for w in words if w not in stop_words)

    def has_published_today(self, tz_name: str = "Asia/Kolkata") -> bool:
        """Check if a post has already been published in the current day for the specified timezone."""
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone(timedelta(hours=5, minutes=30))

        now = datetime.now(tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_of_day.astimezone(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM posts
                WHERE published_at >= ? AND status = 'published'
            """, (start_utc,))
            count = cursor.fetchone()[0]
            return count > 0

    def is_duplicate(self, topic: str, title: str, content: str = None) -> tuple[bool, str]:
        """
        Check if topic, title, or content hash is too similar to past publications.
        Returns (is_duplicate: bool, reason: str).
        """
        if content:
            chash = self.compute_hash(content)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM posts WHERE content_hash = ?", (chash,))
                if cursor.fetchone():
                    return True, "Exact content hash matches a previously published post."

        # Check recent topics (last 60 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic, title FROM posts WHERE published_at >= ?", (cutoff,))
            recent_posts = cursor.fetchall()

        topic_clean = topic.strip().lower()
        title_tokens = self.normalize_title(title)

        for past_topic, past_title in recent_posts:
            # Check exact topic match
            if topic_clean == past_topic.strip().lower():
                return True, f"Topic '{topic}' was already posted in the last 60 days."

            # Check title token similarity (Jaccard similarity > 0.60)
            past_tokens = self.normalize_title(past_title)
            if title_tokens and past_tokens:
                intersection = len(title_tokens.intersection(past_tokens))
                union = len(title_tokens.union(past_tokens))
                similarity = intersection / union if union > 0 else 0
                if similarity >= 0.60:
                    return True, f"Title '{title}' is too similar to past post '{past_title}' (similarity: {similarity:.2f})."

        return False, ""

    def record_post(self, topic: str, title: str, content: str, linkedin_post_id: str, has_image: bool = False):
        chash = self.compute_hash(content)
        now_utc = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (topic, title, content_hash, published_at, linkedin_post_id, has_image, status)
                VALUES (?, ?, ?, ?, ?, ?, 'published')
            """, (topic, title, chash, now_utc, linkedin_post_id, 1 if has_image else 0))
            conn.commit()

    def record_topic_attempt(self, topic: str, score: float, decision: str):
        now_utc = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attempted_topics (topic, score, decision, attempted_at)
                VALUES (?, ?, ?, ?)
            """, (topic, score, decision, now_utc))
            conn.commit()

    def get_recent_topics(self, days: int = 30) -> list[str]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT topic FROM posts WHERE published_at >= ?", (cutoff,))
            return [row[0] for row in cursor.fetchall()]
