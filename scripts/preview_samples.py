#!/usr/bin/env python3
"""Generate structurally DIFFERENT preview posts for local review."""

import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from scripts.main import generate_text
from scripts.services.writing_agent import WritingAgent
from scripts.services.quality_reviewer import QualityReviewer
from scripts.services.image_decision import ImageDecisionAgent
from scripts.hook_matrix import get_archetype_by_id
import scripts.infographic as ig

# Three deliberately different formats + visuals
SAMPLES = [
    {
        "topic": "Too many UseCase classes are slowing Android teams down",
        "context": "Debate around Clean Architecture ceremony vs shipping speed for CRUD features.",
        "archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",  # HOT_TAKE + quote poster
    },
    {
        "topic": "Most teams still think Play crashes are always their Kotlin code",
        "context": "16KB page-size / native .so alignment rejects and silent startup deaths on Android 15.",
        "archetype": "OS_INTERNALS_DEEP_DIVE",  # MYTH_BUST + light poster
    },
    {
        "topic": "Checkout froze and everyone blamed the network first",
        "context": "Main-thread Room query during pay button tap. Scene-based war story.",
        "archetype": "SCALE_INCIDENT_WAR_STORY",  # MINI_STORY + dark poster
    },
]


def main():
    out_dir = os.path.join(PROJECT_ROOT, "renderer", "output")
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(out_dir, f"preview_diverse_{stamp}.md")

    writer = WritingAgent(generate_text)
    reviewer = QualityReviewer(generate_text)
    images = ImageDecisionAgent(generate_text)

    sections = [f"# Diverse preview posts — {stamp}\n"]

    for i, sample in enumerate(SAMPLES, 1):
        meta = get_archetype_by_id(sample["archetype"])
        print(f"\n=== SAMPLE {i}/{len(SAMPLES)} [{meta.get('format')}] {sample['topic']} ===")

        post_text, first_comment, archetype = writer.write_post(
            sample["topic"],
            sample["context"],
            archetype_id=sample["archetype"],
        )
        review = reviewer.review(post_text, sample["topic"])
        print(
            f"  QA passed={review.get('passed')} natural={review.get('naturalness')} "
            f"hook={review.get('engagement_hook')} ai={review.get('ai_like_language')}"
        )
        if not review.get("passed"):
            post_text, first_comment, archetype = writer.write_post(
                sample["topic"],
                sample["context"],
                feedback=review.get("feedback", ""),
                archetype_id=archetype,
            )
            review = reviewer.review(post_text, sample["topic"])
            print(f"  After rewrite passed={review.get('passed')}")

        needs, reason, template = images.decide(
            sample["topic"], post_text, archetype_id=archetype, theme="dark"
        )
        print(f"  Visual: {template} ({reason})")

        png_path = ""
        if needs and template:
            content = ig.generate_process_content(
                sample["topic"], post_text, generate_text, template=template
            )
            png_name = f"preview_diverse_{i}.png"
            png_path = os.path.join(out_dir, png_name)
            ig.render_infographic(content, png_path, template=template)
            print(f"  Poster: {png_path}")

        bullet_count = sum(
            1 for ln in post_text.splitlines()
            if ln.strip().startswith(("→", "•", "- "))
        )
        has_recruiter = "DMs are open" in post_text

        sections.append(f"## Sample {i}: {sample['topic']}\n")
        sections.append(f"- Format: `{meta.get('format')}`")
        sections.append(f"- Archetype: `{archetype}`")
        sections.append(f"- Template: `{template}`")
        sections.append(f"- Bullet lines: {bullet_count}")
        sections.append(f"- Recruiter line: {has_recruiter}")
        sections.append(
            f"- QA: passed={review.get('passed')} | naturalness={review.get('naturalness')} | "
            f"engagement_hook={review.get('engagement_hook')}"
        )
        if png_path:
            sections.append(f"- Image: `{os.path.relpath(png_path, PROJECT_ROOT)}`")
        sections.append("\n### Post\n")
        sections.append(post_text)
        sections.append("\n### First comment\n")
        sections.append(first_comment or "(none)")
        sections.append("\n---\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"\nWrote review file: {md_path}")


if __name__ == "__main__":
    main()
