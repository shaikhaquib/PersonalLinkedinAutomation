"""
Calendar Manager for LinkedIn Post Automation.
Manages scheduled posts in data/content_calendar.json and maintains CONTENT_CALENDAR.md.
"""

import os
import json
import pathlib
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CALENDAR_JSON = DATA_DIR / "content_calendar.json"
CALENDAR_MD = PROJECT_ROOT / "CONTENT_CALENDAR.md"


class CalendarManager:
    def __init__(self, json_path: pathlib.Path = CALENDAR_JSON, md_path: pathlib.Path = CALENDAR_MD):
        self.json_path = pathlib.Path(json_path)
        self.md_path = pathlib.Path(md_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_calendar()

    def _init_calendar(self):
        if not self.json_path.exists():
            self._save_items([])

    def _load_items(self) -> list[dict]:
        if not self.json_path.exists():
            return []
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_items(self, items: list[dict]):
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        self.sync_markdown(items)

    def schedule_post(self, scheduled_date: str, scheduled_time: str, topic: str,
                      archetype: str, post_text: str, first_comment: str = "",
                      image_path: str = "", template: str = "", theme: str = "dark") -> dict:
        """
        Schedules a post for a specific date and time slot.
        scheduled_date: 'YYYY-MM-DD'
        scheduled_time: 'HH:MM' (IST)
        """
        items = self._load_items()
        post_id = f"post_{scheduled_date}_{scheduled_time.replace(':', '')}"

        # Check if already exists for this slot and update, else append
        existing = next((item for item in items if item.get("id") == post_id), None)
        entry = {
            "id": post_id,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "timezone": "Asia/Kolkata",
            "topic": topic,
            "archetype": archetype,
            "post_text": post_text,
            "first_comment": first_comment,
            "image_path": image_path,
            "template": template,
            "theme": theme,
            "status": "scheduled",
            "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "published_at": None,
            "linkedin_post_id": None
        }

        if existing:
            items = [entry if item.get("id") == post_id else item for item in items]
        else:
            items.append(entry)

        # Sort by scheduled date and time
        items.sort(key=lambda x: (x.get("scheduled_date", ""), x.get("scheduled_time", "")))
        self._save_items(items)
        print(f"  [calendar] Scheduled post for {scheduled_date} at {scheduled_time} IST: '{topic}'")
        return entry

    def get_due_post(self, target_date: str = None) -> dict | None:
        """
        Retrieves the scheduled post for a target date (default: today in Asia/Kolkata).
        Returns None if no scheduled post is queued.
        """
        if target_date is None:
            target_date = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

        items = self._load_items()
        for item in items:
            if item.get("scheduled_date") == target_date and item.get("status") == "scheduled":
                return item
        return None

    def mark_published(self, post_id: str, linkedin_post_id: str):
        items = self._load_items()
        for item in items:
            if item.get("id") == post_id:
                item["status"] = "published"
                item["published_at"] = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
                item["linkedin_post_id"] = linkedin_post_id
                break
        self._save_items(items)

    def list_posts(self) -> list[dict]:
        return self._load_items()

    def sync_markdown(self, items: list[dict] = None):
        """Generates a human-readable CONTENT_CALENDAR.md."""
        if items is None:
            items = self._load_items()

        now_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
        lines = [
            "# LinkedIn Automation Content Calendar",
            "",
            f"**Owner**: Aquib Rashid Shaikh  ",
            f"**Timezone**: Asia/Kolkata (IST)  ",
            f"**Last Synchronized**: {now_str}  ",
            "",
            "---",
            "",
            "## Scheduled & Published Queue",
            "",
            "| Date | Time (IST) | Archetype | Topic | Visual Template | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        if not items:
            lines.append("| — | — | — | *No posts currently queued in calendar* | — | — |")
        else:
            for item in items:
                status_icon = "🟢 Scheduled" if item.get("status") == "scheduled" else ("✅ Published" if item.get("status") == "published" else "📝 Draft")
                d = item.get("scheduled_date", "—")
                t = item.get("scheduled_time", "09:00")
                arch = item.get("archetype", "—")
                top = item.get("topic", "—")
                tpl = item.get("template", "text-only")
                lines.append(f"| **{d}** | {t} | `{arch}` | {top} | `{tpl}` | {status_icon} |")

        lines.extend([
            "",
            "---",
            "",
            "## How Scheduling Works",
            "",
            "1. **Pre-generation & Quality Gate**: Posts in this calendar have passed all 6 Quality Review metrics and had their visual cards pre-rendered.",
            "2. **Daily Execution Trigger**: GitHub Actions runs daily at `09:00 AM IST` (`cron: '30 3 * * *'`). When the scheduled time arrives, `scripts/main.py` checks this calendar, picks the queued post, publishes it via OAuth, drops the author first comment, and marks the status as Published.",
            "3. **LinkedIn Native UI Alternate**: If you prefer posting via LinkedIn's desktop web scheduler (clock icon), copy the post text, first comment, and pre-rendered image asset directly from the calendar entry.",
            ""
        ])

        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
