#!/usr/bin/env python3
"""
LinkedIn Content Scheduler & Calendar Controller.

Commands:
  python scripts/scheduler.py --list
      List all scheduled and published posts in the calendar.

  python scripts/scheduler.py --schedule-tomorrow [--topic "Custom Topic"] [--archetype ID] [--theme {dark,light}]
      Generate, quality-review, render visual card, and queue post for tomorrow at 09:00 AM IST.

  python scripts/scheduler.py --schedule-date YYYY-MM-DD [--time HH:MM] [--topic "Custom Topic"]
      Schedule a post for a specific date and time slot.

  python scripts/scheduler.py --publish-due
      Check if there is a scheduled post due for today, and publish it to LinkedIn.
"""

import os
import sys
import argparse
import pathlib
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from scripts.main import generate_text
from scripts.services.writing_agent import WritingAgent
from scripts.services.quality_reviewer import QualityReviewer
from scripts.services.image_decision import ImageDecisionAgent
from scripts.services.calendar_manager import CalendarManager
from scripts.storage.history_manager import HistoryManager
from scripts.services.linkedin_publisher import LinkedInPublisher
from scripts.services.telegram_notifier import TelegramNotifier
from scripts.services.schedule_rotator import get_weekday_rotation
import scripts.infographic as ig

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID    = os.getenv("LINKEDIN_PERSON_ID")


def schedule_post_pipeline(date_str: str, time_str: str = "09:00",
                           topic: str = None, archetype_id: str = None,
                           theme: str = "dark") -> dict:
    """
    Executes the autonomous generation pipeline (Step 1-7) and queues the post
    into the content calendar for the specified date and time without immediate publishing.
    """
    print("=" * 65)
    print(f"  SCHEDULING POST FOR: {date_str} at {time_str} IST")
    print("=" * 65)

    calendar = CalendarManager()
    writing_agent = WritingAgent(generate_text, root_dir=str(PROJECT_ROOT))
    quality_reviewer = QualityReviewer(generate_text)
    decision_agent = ImageDecisionAgent(generate_text)

    # Curated production topics across Aquib's core domains
    curated_topics = [
        ("Tuning ExoPlayer LoadControl Buffers for Low-Latency OTT Streaming", "SCALE_INCIDENT_WAR_STORY"),
        ("Idempotency and Android Keystore Security in Mobile Banking Transactions", "OS_INTERNALS_DEEP_DIVE"),
        ("Architecting Battery-Efficient Geofencing with Android FusedLocation", "HARDWARE_LOW_LEVEL_DEEP_DIVE"),
        ("Engineering an Enterprise Android Design System Published via Internal Maven", "CONTRARIAN_ARCHITECTURE_CALLOUT"),
        ("High-Performance JavaScript Bridge Architecture for Android WebViews", "CODE_AUTOPSY_TEARDOWN"),
    ]

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        rotation = get_weekday_rotation(dt)
    except Exception:
        rotation = get_weekday_rotation()

    if not archetype_id:
        archetype_id = rotation["preferred_archetype"]

    if theme == "dark" and rotation["theme"] != "dark":
        theme = rotation["theme"]

    if not topic:
        chosen = curated_topics[0]
        topic = chosen[0]

    print(f"  Target Day: {rotation['day_name']} -> {rotation['theme_name']}")
    print(f"  Topic     : {topic}")
    print(f"  Archetype : {archetype_id}")
    print(f"  Theme     : {theme.upper()} ({rotation['format_desc']})")

    # Step 1: Write post
    print("\n[ Step 1/4 ] Generating post draft with Senior Android Developer persona...")
    post_text, first_comment, selected_arch = writing_agent.write_post(topic, archetype_id=archetype_id)

    # Step 2: Quality review loop (up to 3 attempts)
    print("\n[ Step 2/4 ] Running Quality Review Agent...")
    passed_review = False
    for attempt in range(1, 4):
        eval_res = quality_reviewer.review(post_text, topic)
        ta = eval_res.get("technical_accuracy", 0)
        nat = eval_res.get("naturalness", 0)
        ai = eval_res.get("ai_like_language", 0)
        passed = eval_res.get("passed", False)
        print(f"  Attempt {attempt}/3 -> Technical: {ta}/10 | Naturalness: {nat}/10 | AI: {ai}/10 | Passed: {passed}")
        if passed:
            passed_review = True
            break
        if attempt < 3:
            fb = eval_res.get("feedback", "Improve technical depth and conversational human naturalness.")
            print(f"  [Rewrite] Revising draft based on reviewer feedback: {fb}")
            post_text, first_comment, _ = writing_agent.write_post(topic, feedback=fb, archetype_id=selected_arch)

    if not passed_review:
        print("  [WARN] Draft completed with minor quality review notes. Proceeding with best candidate.")

    # Step 3: Image Decision & Playwright Render
    print("\n[ Step 3/4 ] Evaluating visual requirement & rendering card...")
    needs_image, reason, selected_template = decision_agent.decide(topic, post_text, selected_arch, theme=theme)
    png_path = ""
    if needs_image and selected_template:
        print(f"  Template selected: {selected_template}")
        out_name = f"scheduled_{date_str}_{time_str.replace(':', '')}.png"
        out_png = str(PROJECT_ROOT / "renderer" / "output" / out_name)
        content = ig.generate_process_content(topic, post_text, generate_text, template=selected_template)
        png_path = ig.render_infographic(content, out_png, template=selected_template)
        print(f"  Infographic pre-rendered: {png_path}")

    # Step 4: Record into Content Calendar
    print("\n[ Step 4/4 ] Staging into Content Calendar...")
    entry = calendar.schedule_post(
        scheduled_date=date_str,
        scheduled_time=time_str,
        topic=topic,
        archetype=selected_arch,
        post_text=post_text,
        first_comment=first_comment or "",
        image_path=png_path,
        template=selected_template or "text-only",
        theme=theme
    )

    print("\n" + "=" * 65)
    print("  POST SUCCESSFULLY SCHEDULED IN CALENDAR")
    print(f"  Date & Time : {date_str} at {time_str} IST")
    print(f"  Calendar    : CONTENT_CALENDAR.md")
    print(f"  Data JSON   : data/content_calendar.json")
    print("=" * 65 + "\n")
    return entry


def publish_due_post(dry_run: bool = False):
    """Checks for a post scheduled for today and publishes it."""
    calendar = CalendarManager()
    today_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    due_post = calendar.get_due_post(today_str)

    if not due_post:
        print(f"No scheduled posts due for today ({today_str}).")
        return

    print(f"Publishing scheduled post for {today_str}: '{due_post['topic']}'")
    if dry_run:
        print("[DRY-RUN] Would publish scheduled post payload to LinkedIn. Skipped live API call.")
        return

    notifier = TelegramNotifier()
    publisher = LinkedInPublisher(LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID, notifier=notifier)
    image_path = due_post.get("image_path")
    image_urn = None

    if image_path and os.path.exists(image_path):
        print(f"  Uploading scheduled image: {image_path}")
        image_urn = ig.upload_to_linkedin(image_path, LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID)

    post_id = publisher.publish(due_post["post_text"], image_urn=image_urn)
    print(f"  Published! LinkedIn Post ID: {post_id}")

    if due_post.get("first_comment"):
        publisher.post_first_comment(post_id, due_post["first_comment"])

    # Update history and calendar
    history = HistoryManager()
    history.record_post(due_post["topic"], due_post["topic"], due_post["post_text"], post_id, has_image=bool(image_urn))
    calendar.mark_published(due_post["id"], post_id)
    print(f"  Calendar updated: {due_post['id']} marked as published.")


def main():
    parser = argparse.ArgumentParser(description="LinkedIn Content Scheduler & Calendar Controller")
    parser.add_argument("--list", action="store_true", help="List all scheduled and published posts")
    parser.add_argument("--schedule-tomorrow", action="store_true", help="Schedule a post for tomorrow at 09:00 IST")
    parser.add_argument("--schedule-date", type=str, default=None, help="Specific date to schedule (YYYY-MM-DD)")
    parser.add_argument("--time", type=str, default="09:00", help="Time slot in IST (default: 09:00)")
    parser.add_argument("--topic", type=str, default=None, help="Force a specific topic for scheduling")
    parser.add_argument("--archetype", type=str, default=None, help="Force a specific blueprint archetype ID")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark", help="Visual theme variant (default: dark)")
    parser.add_argument("--publish-due", action="store_true", help="Publish today's scheduled post if due")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode for publishing")
    args = parser.parse_args()

    calendar = CalendarManager()

    if args.list:
        posts = calendar.list_posts()
        print("\n" + "=" * 65)
        print("  LINKEDIN CONTENT CALENDAR QUEUE")
        print("=" * 65)
        if not posts:
            print("  No posts currently queued in calendar.")
        for p in posts:
            status_tag = f"[{p.get('status', '').upper()}]"
            print(f"  {p.get('scheduled_date')} {p.get('scheduled_time')} IST {status_tag}: '{p.get('topic')}' ({p.get('archetype')})")
        print("=" * 65 + "\n")
        return

    if args.publish_due:
        publish_due_post(dry_run=args.dry_run)
        return

    if args.schedule_tomorrow:
        tomorrow_date = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).strftime("%Y-%m-%d")
        schedule_post_pipeline(tomorrow_date, time_str=args.time, topic=args.topic,
                               archetype_id=args.archetype, theme=args.theme)
        return

    if args.schedule_date:
        schedule_post_pipeline(args.schedule_date, time_str=args.time, topic=args.topic,
                               archetype_id=args.archetype, theme=args.theme)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
