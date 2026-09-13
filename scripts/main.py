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

def run_agent(preview: bool = False, force_topic: str = None):
    print("=" * 65)
    print("  AUTONOMOUS LINKEDIN AGENT — Senior Android Developer")
    print("=" * 65)
    print(f"  Mode     : {'PREVIEW ONLY (No LinkedIn Post)' if preview else 'LIVE PUBLISHING'}")
    print(f"  Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + "\n")

    notifier = TelegramNotifier()
    history = HistoryManager()

    # Step 1: Idempotency Lock
    if not preview:
        if history.has_published_today(SETTINGS.get("timezone", "Asia/Kolkata")):
            print("[IDEMPOTENCY] A post has already been published today in the current posting window.")
            print("[IDEMPOTENCY] Aborting to strictly enforce 1 post/day schedule.")
            return

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
            {"title": "Understanding Process Death & State Restoration in Jetpack Compose", "summary": "How Android LMK destroys processes in the background and why rememberSaveable is required.", "source": "curated_fallback"},
            {"title": "Idempotency in Mobile Banking & Payment Transactions", "summary": "Preventing double charges over flaky mobile networks using client-side UUID tokens.", "source": "curated_fallback"},
            {"title": "Eliminating JIT Stalls on App Startup with Baseline Profiles", "summary": "How AOT compilation reduces cold start times by 30% on production Android devices.", "source": "curated_fallback"}
        ]

    # Step 3: Candidate Evaluation Loop
    print("\n[ Step 2 ] Finding and evaluating suitable topic...")
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
        post_text, first_comment = writing_agent.write_post(topic, source_context)

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
                post_text, first_comment = writing_agent.write_post(topic, source_context, feedback=feedback)

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

    # Step 6: Image Decision & Generation
    print("\n[ Step 5 ] Evaluating infographic requirement...")
    decision_agent = ImageDecisionAgent(generate_text)
    needs_image, reason = decision_agent.should_generate_image(topic, post_text)
    print(f"  Image Required: {needs_image} ({reason})")

    png_path = None
    if needs_image:
        try:
            import scripts.infographic as ig
            out_png = os.path.join(PROJECT_ROOT, "renderer", "output", "infographic.png")
            print("  Rendering infographic with Playwright...")
            content = ig.generate_process_content(topic, post_text, generate_text)
            png_path = ig.render_infographic(content, out_png, template="process_infographic_dark.html.j2")
            print(f"  Infographic successfully rendered: {png_path}")
        except Exception as e:
            print(f"  [WARN] Infographic rendering failed ({e}). Gracefully continuing text-only.")
            png_path = None

    # Step 7: Publishing or Preview
    if preview:
        print("\n" + "=" * 60)
        print("  PREVIEW COMPLETE — Verification Successful")
        print(f"  Topic           : {topic}")
        print(f"  Characters      : {len(post_text)}")
        print(f"  Has Infographic : {bool(png_path)}")
        print("  LinkedIn UGC    : Skipped (--preview mode)")
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

    # Record to history
    history.record_post(topic, topic, post_text, post_id, has_image=bool(image_urn))
    print("  Saved post record to data/content_history.db")

    if SETTINGS.get("daily_report"):
        notifier.send_daily_report(topic, post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print("\n" + "=" * 60)
    print("  WORKFLOW COMPLETE — Autonomous Run Successful")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous LinkedIn Agent")
    parser.add_argument("--preview", action="store_true", help="Preview only, do not publish to LinkedIn")
    parser.add_argument("--topic", type=str, default=None, help="Force a specific topic")
    args = parser.parse_args()

    run_agent(preview=args.preview, force_topic=args.topic)
