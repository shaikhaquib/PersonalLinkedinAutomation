#!/usr/bin/env python3
"""
Autonomous LinkedIn Content Agent.
Main orchestration pipeline for discovering, generating, reviewing, and publishing
high-quality Senior Android Developer content.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

from scripts.storage.history_manager import HistoryManager
from scripts.services.rss_fetcher import RSSFetcher
from scripts.services.topic_analyzer import TopicAnalyzer
from scripts.services.writing_agent import WritingAgent
from scripts.services.quality_reviewer import QualityReviewer
from scripts.services.image_decision import ImageDecisionAgent
from scripts.services.telegram_notifier import TelegramNotifier
from scripts.services.linkedin_publisher import LinkedInPublisher
from scripts.services.calendar_manager import CalendarManager
from scripts.services.text_formatter import format_linkedin_text
from scripts.services.schedule_rotator import get_weekday_rotation

# ── API Keys & Settings ───────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY_2 = os.environ.get("GEMINI_API_KEY_2")
EURON_API_KEY = os.environ.get("EURON_API_KEY")
LINKEDIN_ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_PERSON_ID = os.environ.get("LINKEDIN_PERSON_ID")

GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]

# Load settings
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "config", "settings.json")
SETTINGS = {
    "posts_per_day": 1,
    "preferred_time": "09:00",
    "timezone": "Asia/Kolkata",
    "min_topic_score": 0.70,
    "daily_report": False,
    "max_review_attempts": 3,
}
if os.path.exists(SETTINGS_PATH):
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            SETTINGS.update(json.load(f))
    except Exception as e:
        print(f"[WARN] Failed to load settings.json: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# LLM Generation Engine with Key & Model Rotation
# ══════════════════════════════════════════════════════════════════════════════

def create_gemini_client(api_key: str):
    from google import genai
    return genai.Client(api_key=api_key)


def generate_text(prompt: str, system_instruction: str = "") -> str:
    """Robust text generation with Gemini key rotation and model fallbacks."""
    api_keys = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY_2] if k]
    if not api_keys:
        raise RuntimeError("No GEMINI_API_KEY configured. Please set GEMINI_API_KEY in your .env or GitHub Secrets.")

    from google.genai import types

    last_error = None
    for key in api_keys:
        client = create_gemini_client(key)
        for model in GEMINI_MODELS:
            for attempt in range(1, 4):
                try:
                    cfg = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    )
                    resp = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=cfg
                    )
                    if resp and resp.text:
                        return resp.text.strip()
                except Exception as exc:
                    err_str = str(exc).lower()
                    last_error = exc
                    if "429" in err_str or "quota" in err_str:
                        print(f"  [LLM] Quota exceeded on {model} (key ...{key[-4:]}). Rotating...")
                        break  # try next key or model
                    print(f"  [LLM] Transient error on {model} attempt {attempt}: {exc}")
                    time.sleep(2 * attempt)

    # Fallback to Euron if available
    if EURON_API_KEY:
        try:
            import requests
            resp = requests.post(
                "https://api.euron.one/v1/chat/completions",
                headers={"Authorization": f"Bearer {EURON_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  [LLM] Euron fallback failed: {e}")

    raise RuntimeError(f"All LLM generation options exhausted. Last error: {last_error}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATION PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def run_agent(preview: bool = False, force_topic: str = None, force_publish: bool = False,
              dry_run: bool = False, force_archetype: str = None, theme: str = "dark",
              publish_live: bool = False):
    # Live publishing safety gate (Phase 7 requirement)
    live_enabled = (
        os.environ.get("LIVE_PUBLISH_ENABLED", "").lower() in ("true", "1", "yes")
        or SETTINGS.get("live_publish_enabled", False)
    )
    if not preview and not dry_run and not publish_live and not live_enabled:
        print("\n" + "=" * 65)
        print("  [SAFETY GATE] Live publishing is disabled by default.")
        print("  To protect your LinkedIn account, live posting requires explicit opt-in.")
        print("  Pass --publish-live flag or set LIVE_PUBLISH_ENABLED=true in settings/env.")
        print("  Automatically falling back to DRY-RUN mode.")
        print("=" * 65 + "\n")
        dry_run = True

    mode_str = 'PREVIEW ONLY' if preview else ('DRY-RUN (logs payload, no API call)' if dry_run else 'LIVE PUBLISHING')
    print("=" * 65)
    print("  AUTONOMOUS LINKEDIN AGENT — Senior Android Developer")
    print("=" * 65)
    print(f"  Mode     : {mode_str}")
    print(f"  Theme    : {theme.upper()} (Phase 2.9 selectable variant)")
    print(f"  Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    notifier = TelegramNotifier()
    history = HistoryManager()

    # Step 1: Idempotency Lock (bypassed if preview, manual force_publish, or manual topic override)
    if not preview and not force_publish and not force_topic:
        if history.has_published_today(SETTINGS.get("timezone", "Asia/Kolkata")):
            print("[IDEMPOTENCY] A post has already been published today in the current posting window.")
            print("[IDEMPOTENCY] Aborting to strictly enforce 1 post/day schedule.")
            return

    # Check for pre-scheduled post in Content Calendar
    calendar = CalendarManager()
    due_post = calendar.get_due_post() if (not force_topic and not force_archetype) else None

    if due_post:
        print("\n[ CALENDAR ] Found queued scheduled post for today!")
        print(f"  Topic           : {due_post['topic']}")
        print(f"  Archetype       : {due_post.get('archetype', '—')}")
        print(f"  Scheduled Slot  : {due_post.get('scheduled_time', '09:00')} IST")
        print("  Using pre-approved post text, first comment, and pre-rendered visual card.")
        topic = due_post["topic"]
        post_text = due_post["post_text"]
        first_comment = due_post.get("first_comment", "")
        archetype_id = due_post.get("archetype", "")
        raw_png = due_post.get("image_path")
        selected_template = due_post.get("template", "text-only")
        needs_image = bool(raw_png and selected_template != "text-only")
        png_path = None
        if needs_image and raw_png:
            if not os.path.isabs(raw_png):
                candidate = os.path.join(PROJECT_ROOT, raw_png)
            else:
                candidate = raw_png
            if os.path.exists(candidate):
                png_path = candidate
            else:
                # Portable fallback: check by filename in renderer/output
                fname = os.path.basename(raw_png)
                candidate_rel = os.path.join(PROJECT_ROOT, "renderer", "output", fname)
                if os.path.exists(candidate_rel):
                    png_path = candidate_rel
                elif selected_template:
                    try:
                        import scripts.infographic as ig
                        print(f"  [Notice] Pre-rendered image not found on disk ({raw_png}). Re-rendering dynamically...")
                        content = ig.generate_process_content(topic, post_text, generate_text, template=selected_template)
                        png_path = ig.render_infographic(content, candidate_rel, template=selected_template)
                        print(f"  Dynamic render successful: {png_path}")
                    except Exception as re_err:
                        print(f"  [WARN] Dynamic render failed: {re_err}. Proceeding without image.")
                        png_path = None
    else:
        # Step 2: Topic Discovery
        print("[ Step 1 ] Discovering candidate topics...")
        candidates = []
        if force_topic:
            print(f"  Using forced topic from argument: {force_topic}")
            candidates = [{"title": force_topic, "summary": force_topic, "source": "manual_override"}]
        else:
            rss_fetcher = RSSFetcher()
            rss_candidates = rss_fetcher.fetch_all()
            print(f"  Fetched {len(rss_candidates)} candidate items from RSS.")

            analyzer = TopicAnalyzer(min_score=SETTINGS.get("min_topic_score", 0.70))
            candidates = analyzer.rank_candidates(rss_candidates)
            print(f"  Scored & filtered: {len(candidates)} high-value candidates.")

        # Fallback topics if RSS is empty
        if not candidates:
            print("  [WARN] No RSS candidates met score threshold. Using curated Android topics fallback.")
            candidates = [
                {"title": "Understanding Process Death & State Restoration in Jetpack Compose", "summary": "How Android LMK destroys processes in the background and why rememberSaveable and DataStore are required.", "source": "curated_fallback"},
                {"title": "Reliable BLE GATT Queueing and MTU Negotiation in Production Android", "summary": "Solving GATT status 133, connection serialization via Coroutines Channels, and MTU 517 byte negotiation.", "source": "curated_fallback"},
                {"title": "Tuning ExoPlayer LoadControl Buffers for Low-Latency OTT Streaming", "summary": "Customizing DefaultLoadControl buffer thresholds and ABR track selection to prevent OOMs on mobile devices.", "source": "curated_fallback"},
                {"title": "Architecting Battery-Efficient Geofencing with Android FusedLocation", "summary": "Balancing real-time proximity detection with Android 14 foreground service types and Doze mode restrictions.", "source": "curated_fallback"},
                {"title": "Engineering an Enterprise Android Design System Published via Internal Maven", "summary": "Building unified UI component packages across multiple Android pods to reduce feature integration time.", "source": "curated_fallback"},
                {"title": "Idempotency and Keystore Security in Mobile Banking Transactions", "summary": "Preventing double charges over flaky mobile networks with biometric prompts and client-side UUID tokens.", "source": "curated_fallback"},
                {"title": "High-Performance JavaScript Bridge Architecture for Android WebViews", "summary": "Safely bridging web-hosted micro-frontends with native Android capabilities using native JS plugin architecture.", "source": "curated_fallback"}
            ]

        # Step 3: Candidate Evaluation Loop
        rotation = get_weekday_rotation()
        target_archetype = force_archetype or rotation["preferred_archetype"]
        target_theme = theme if theme != "dark" else rotation["theme"]
        print(f"\n[ Step 2 ] Finding and evaluating suitable topic...")
        print(f"  [Weekday Matrix] {rotation['day_name']} Theme: {rotation['theme_name']}")
        print(f"  Target Archetype: {target_archetype} | Visual: {rotation['format_desc']}")

        writing_agent = WritingAgent(generate_text)
        quality_reviewer = QualityReviewer(generate_text)
        max_attempts = SETTINGS.get("max_review_attempts", 3)

        passed_review = False
        selected_candidate = None
        post_text = None
        first_comment = None

        for cand in candidates:
            is_dup, reason = history.is_duplicate(cand["title"], cand["title"])
            if is_dup:
                print(f"  [Duplicate] Skipped '{cand['title']}': {reason}")
                history.record_topic_attempt(cand["title"], cand.get("overall_score", 0.7), "rejected_duplicate")
                continue

            topic = cand["title"]
            source_context = f"{cand.get('summary', '')} (Source: {cand.get('source', 'Web')})"
            print(f"\n  Attempting Topic: {topic}")

            print("\n[ Step 3 ] Generating post draft with Senior Android Developer persona...")
            post_text, first_comment, archetype_id = writing_agent.write_post(
                topic, source_context, archetype_id=target_archetype
            )
            print(f"  Archetype selected: {archetype_id}")

            print("\n[ Step 4 ] Running Quality Review Agent...")
            for attempt in range(1, max_attempts + 1):
                eval_result = quality_reviewer.review(post_text, topic)
                ta = eval_result.get("technical_accuracy", 0)
                nat = eval_result.get("naturalness", 0)
                ai_score = eval_result.get("ai_like_language", 0)
                print(f"  Attempt {attempt}/{max_attempts} -> Technical: {ta}/10 | Naturalness: {nat}/10 | AI-Jargon: {ai_score}/10 | Passed: {eval_result.get('passed')}")

                if eval_result.get("passed"):
                    passed_review = True
                    selected_candidate = cand
                    break

                if attempt < max_attempts:
                    feedback = eval_result.get("feedback", "Improve technical depth and eliminate marketing language.")
                    print(f"  [Rewrite] Rewriting draft based on reviewer feedback: {feedback}")
                    post_text, first_comment, archetype_id = writing_agent.write_post(
                        topic, source_context, feedback=feedback, archetype_id=archetype_id
                    )

            if passed_review:
                break

            print(f"  [QualityReview] Topic '{topic}' failed quality thresholds after maximum retries. Trying next candidate...")
            history.record_topic_attempt(topic, cand.get("overall_score", 0.7), "rejected_quality")

        if not passed_review or not selected_candidate:
            msg = "No candidates passed quality review and duplicate filtering."
            print(f"  [ERROR] {msg}")
            return

        print("\n" + "─" * 60)
        print("APPROVED POST DRAFT:")
        print("─" * 60)
        print(post_text)
        print("─" * 60)
        if first_comment:
            print(f"FIRST COMMENT:\n{first_comment}")
            print("─" * 60)

        # Step 6: Image Decision & Generation (Phase 3: routes to correct template)
        print("\n[ Step 5 ] Evaluating infographic requirement...")
        decision_agent = ImageDecisionAgent(generate_text)
        needs_image, reason, selected_template = decision_agent.decide(topic, post_text, archetype_id, theme=target_theme)
        print(f"  Image Required: {needs_image} ({reason})")
        if needs_image:
            print(f"  Template selected: {selected_template}")

        png_path = None
        if needs_image and selected_template:
            try:
                import scripts.infographic as ig
                out_png = os.path.join(PROJECT_ROOT, "renderer", "output", "infographic.png")
                print("  Rendering infographic with Playwright...")
                content = ig.generate_process_content(topic, post_text, generate_text, template=selected_template)
                png_path = ig.render_infographic(content, out_png, template=selected_template)
                print(f"  Infographic successfully rendered: {png_path}")
            except Exception as e:
                print(f"  [WARN] Infographic rendering failed ({e}). Gracefully continuing text-only.")
                png_path = None

    # Format post text and first comment to native LinkedIn Unicode format (bold, clean code)
    post_text = format_linkedin_text(post_text)
    if first_comment:
        first_comment = format_linkedin_text(first_comment)

    # Step 7: Publishing or Preview or Dry-Run
    if preview:
        print("\n" + "=" * 60)
        print("  PREVIEW COMPLETE — Verification Successful")
        print(f"  Topic           : {topic}")
        print(f"  Archetype       : {archetype_id}")
        print(f"  Characters      : {len(post_text)}")
        print(f"  Has Infographic : {bool(png_path)}")
        print(f"  Template        : {selected_template or 'text-only'}")
        print("  LinkedIn UGC    : Skipped (--preview mode)")
        print("=" * 60 + "\n")
        return

    if dry_run:
        # Phase 7: Log exact LinkedIn payload without hitting the API
        author_urn = f"urn:li:person:{LINKEDIN_PERSON_ID}"
        dry_payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "IMAGE" if png_path else "NONE",
                    **({
                        "media": [{"status": "READY", "media": "[IMAGE_ASSET_URN_PLACEHOLDER]"}]
                    } if png_path else {}),
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        import json as _json
        print("\n" + "=" * 60)
        print("  DRY-RUN MODE — LinkedIn API Payload (NOT sent)")
        print("=" * 60)
        print(_json.dumps(dry_payload, indent=2, ensure_ascii=False))
        print(f"\n  FIRST_COMMENT (would be posted): {first_comment}")
        print(f"  PNG: {png_path or 'text-only'}")
        # Dry-run Telegram notification
        if notifier.is_configured():
            notifier.send_alert(
                "DRY-RUN Complete",
                f"Topic: {topic[:80]}",
                f"Archetype: {archetype_id} | Template: {selected_template or 'text-only'} | Chars: {len(post_text)}"
            )
            print("  Telegram dry-run notification sent.")
        else:
            print("  Telegram not configured — dry-run notification skipped.")
        print("=" * 60 + "\n")
        return

    print("\n[ Step 6 ] Publishing to LinkedIn...")
    publisher = LinkedInPublisher(LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID, notifier=notifier)

    image_urn = None
    if png_path and os.path.exists(png_path):
        try:
            import scripts.infographic as ig
            print("  Uploading image to LinkedIn media assets...")
            image_urn = ig.upload_to_linkedin(png_path, LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_ID)
        except Exception as e:
            print(f"  [WARN] Image upload failed ({e}). Proceeding with text-only post.")
            image_urn = None

    post_id = publisher.publish(post_text, image_urn=image_urn)
    print(f"  Success! Post published to LinkedIn. ID: {post_id}")

    if first_comment:
        publisher.post_first_comment(post_id, first_comment)

    # Record to history & update calendar
    history.record_post(topic, topic, post_text, post_id, has_image=bool(image_urn))
    print("  Saved post record to data/content_history.db")
    if due_post:
        calendar.mark_published(due_post["id"], post_id)
        print(f"  Updated calendar: marked {due_post['id']} as published.")

    if SETTINGS.get("daily_report"):
        notifier.send_daily_report(topic, post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("\n" + "=" * 60)
    print("  WORKFLOW COMPLETE — Autonomous Run Successful")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous LinkedIn Agent")
    parser.add_argument("--preview", action="store_true", help="Preview only — generate and QA post, do not publish")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Dry-run — log the exact LinkedIn API payload without sending it")
    parser.add_argument("--schedule-tomorrow", action="store_true",
                        help="Generate, quality-review, render card, and schedule in calendar for tomorrow 09:00 IST")
    parser.add_argument("--topic", type=str, default=None, help="Force a specific topic")
    parser.add_argument("--archetype", type=str, default=None, help="Force a specific blueprint archetype ID")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark",
                        help="Visual theme variant for infographic (default: dark, options: dark, light)")
    parser.add_argument("--force", action="store_true", help="Bypass idempotency lock and force publish")
    parser.add_argument("--publish-live", action="store_true", dest="publish_live",
                        help="Explicit authorization to post live to LinkedIn (default: disabled, runs dry-run)")
    args = parser.parse_args()

    if args.schedule_tomorrow:
        from scripts.scheduler import schedule_post_pipeline
        from datetime import datetime, timedelta
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo
        tomorrow_str = (datetime.now(ZoneInfo("Asia/Kolkata")) + timedelta(days=1)).strftime("%Y-%m-%d")
        schedule_post_pipeline(tomorrow_str, topic=args.topic, archetype_id=args.archetype, theme=args.theme)
    else:
        run_agent(preview=args.preview, force_topic=args.topic, force_publish=args.force,
                  dry_run=args.dry_run, force_archetype=args.archetype, theme=args.theme,
                  publish_live=args.publish_live)
