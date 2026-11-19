#!/usr/bin/env python3
"""Preview: trending Android news topic + graphic (non-text-only) poster."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from scripts.main import generate_text
from scripts.services.trend_fetcher import TrendFetcher
from scripts.services.writing_agent import WritingAgent
from scripts.services.quality_reviewer import QualityReviewer
from scripts.services.image_decision import ImageDecisionAgent
import scripts.infographic as ig


def main():
    print("Fetching trending Android/tech news...")
    trends = TrendFetcher().fetch_trending(limit=10)
    for i, t in enumerate(trends[:5], 1):
        print(f"  {i}. [{t.get('source')}] {t['title'][:90]}")

    if not trends:
        topic = "Play Console is rejecting apps that miss Android 16KB page alignment"
        context = "Trending Play policy / Android 15 native library alignment issue."
        source = "manual_fallback"
    else:
        # Prefer an explicitly Android headline
        pick = next(
            (t for t in trends if any(
                k in t["title"].lower()
                for k in ("android", "kotlin", "compose", "play console", "pixel", "16kb")
            )),
            trends[0],
        )
        topic = pick["title"]
        context = f"{pick.get('summary','')} (Source: {pick.get('source')})"
        source = pick.get("source", "trend")

    print(f"\nGenerating post for: {topic}")
    writer = WritingAgent(generate_text)
    reviewer = QualityReviewer(generate_text)
    images = ImageDecisionAgent(generate_text)

    post_text, first_comment, archetype = writer.write_post(
        topic, context, archetype_id="OS_INTERNALS_DEEP_DIVE"
    )
    review = reviewer.review(post_text, topic)
    print(f"QA passed={review.get('passed')} natural={review.get('naturalness')}")

    # Force news-looking combined text so router picks graphic if needed
    needs, reason, template = images.decide(
        f"{topic} Android Play Console 16kb breaking",
        post_text,
        archetype_id=archetype,
        theme="dark",
    )
    if "news_graphic" not in (template or ""):
        template = "news_graphic_dark.html.j2"
        reason = "Forced news graphic for preview"
    print(f"Visual: {template} ({reason})")

    out_dir = os.path.join(PROJECT_ROOT, "renderer", "output")
    os.makedirs(out_dir, exist_ok=True)
    content = ig.generate_process_content(topic, post_text, generate_text, template=template)
    png_path = os.path.join(out_dir, "preview_news_graphic.png")
    ig.render_infographic(content, png_path, template=template)

    md_path = os.path.join(out_dir, "preview_news_graphic.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# News graphic preview\n\nSource pick: {source}\n\n## Topic\n{topic}\n\n## Post\n\n{post_text}\n\n## First comment\n{first_comment}\n\n## Image\n`{png_path}`\n")
    print(f"Wrote {png_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
