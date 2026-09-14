#!/usr/bin/env python3
"""
Refresh scheduled posts for the week:
1. Embeds stealth recruiter sign-off in post copy.
2. Updates hashtags to 4-tier high-engagement mix.
3. Re-generates and re-renders visual cards using streamlined templates.
4. Updates data/content_calendar.json and CONTENT_CALENDAR.md.
"""

import os
import sys
import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from scripts.main import generate_text
import scripts.infographic as ig
from scripts.services.calendar_manager import CalendarManager

POST_UPDATES = {
    "post_2026-09-15_0900": {
        "recruiter_hook": "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open.",
        "hashtags": "#AndroidDev #Kotlin #MobileArchitecture #IoT #TechLeadership"
    },
    "post_2026-09-16_0900": {
        "recruiter_hook": "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open.",
        "hashtags": "#AndroidDev #Kotlin #JetpackCompose #MobileArchitecture #SoftwareArchitecture"
    },
    "post_2026-09-17_0900": {
        "recruiter_hook": "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open.",
        "hashtags": "#AndroidDev #Kotlin #Android15 #MobileArchitecture #TechLeadership"
    },
    "post_2026-09-18_0900": {
        "recruiter_hook": "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open.",
        "hashtags": "#AndroidDev #Kotlin #MobileArchitecture #CleanCode #TechLeadership"
    }
}


def update_post_text(original_text: str, hook: str, hashtags: str) -> str:
    lines = [line for line in original_text.strip().splitlines() if not line.strip().startswith("#")]
    while lines and not lines[-1].strip():
        lines.pop()

    clean_body = "\n".join(lines)
    return f"{clean_body}\n\n{hook}\n\n{hashtags}"


def main():
    calendar = CalendarManager()
    calendar_path = PROJECT_ROOT / "data" / "content_calendar.json"

    with open(calendar_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    for post in posts:
        post_id = post.get("id")
        if post.get("status") != "scheduled" or post_id not in POST_UPDATES:
            print(f"Skipping {post_id} (status: {post.get('status')})")
            continue

        meta = POST_UPDATES[post_id]
        print(f"\n=======================================================")
        print(f"  UPDATING SCHEDULED POST: {post_id} ({post.get('scheduled_date')})")
        print(f"  Topic: {post.get('topic')}")
        print(f"=======================================================")

        # 1. Update text copy
        new_post_text = update_post_text(post["post_text"], meta["recruiter_hook"], meta["hashtags"])
        post["post_text"] = new_post_text
        print(f"  [Copy] Updated post copy with recruiter hook & 4-tier hashtags.")

        # 2. Re-generate infographic content & re-render visual
        template = post.get("template", "process_infographic_dark.html.j2")
        out_png = str(PROJECT_ROOT / post.get("image_path", f"renderer/output/{post_id}.png"))

        print(f"  [Infographic] Generating punchy visual content with Gemini (Template: {template})...")
        content = ig.generate_process_content(post["topic"], new_post_text, generate_text, template=template)

        print(f"  [Render] Rendering streamlined card to {out_png}...")
        ig.render_infographic(content, out_png, template=template)
        print(f"  [Render] Complete: {out_png}")

    # Save updated calendar
    with open(calendar_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    calendar.sync_markdown(posts)
    print("\n✅ All scheduled posts for the week successfully updated and synced!")


if __name__ == "__main__":
    main()
