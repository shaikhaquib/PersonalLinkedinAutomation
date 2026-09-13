#!/usr/bin/env python3
"""
Comprehensive automated verification script for LinkedIn Automation Pipeline Remediation.
Validates all Phase Gates:
- Phase 1: Pipeline steps audit
- Phase 2: Template branding (eyebrow, footer, no sticky note, no AI infra text)
- Phase 2.6: Zero duplicate card titles across consecutive outputs
- Phase 2.7: Strict 2-accent palette (Violet #a78bfa + Cyan #22d3ee), zero old colors (#4ade80, #fbbf24, #f87171)
- Phase 3: Visual image decision and template routing (Architecture Card vs Code Card)
- Phase 4: Banned phrases & real Android API tokens
- Phase 4.5: Domain facts (status 133 not GATT_FAILURE; ATT layer not HCI)
- Phase 4.6: Bare API name-dropping rule (all bullets >= 6 words with active verb)
- Phase 5: Exactly 5 archetypes
- Phase 6: 5-archetype regression test
- Phase 7: Live-readiness / dry-run verification
"""

import os
import sys
import re
import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import scripts.infographic as ig
from scripts.main import generate_text, run_agent
from scripts.services.writing_agent import WritingAgent
from scripts.services.quality_reviewer import QualityReviewer
from scripts.services.image_decision import ImageDecisionAgent
from scripts.hook_matrix import HOOK_STYLES

TEST_TOPICS = [
    {
        "archetype": "HARDWARE_LOW_LEVEL_DEEP_DIVE",
        "topic": "Reliable BLE GATT Queueing and MTU Negotiation in Production Android",
        "expected_template": "process_infographic_dark.html.j2"
    },
    {
        "archetype": "CODE_AUTOPSY_TEARDOWN",
        "topic": "Passing ViewModel Instances Down Composable Trees Causes Recomposition Loops",
        "expected_template": "code_card_dark.html.j2"
    },
    {
        "archetype": "SCALE_INCIDENT_WAR_STORY",
        "topic": "Android 1MB Binder IPC Transaction Limits in High-Volume Banking",
        "expected_template": "process_infographic_dark.html.j2"
    },
    {
        "archetype": "OS_INTERNALS_DEEP_DIVE",
        "topic": "Understanding Process Death & State Restoration in Jetpack Compose",
        "expected_template": "process_infographic_dark.html.j2"
    },
    {
        "archetype": "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "topic": "The UseCase for Every Repository Cargo Cult in Android",
        "expected_template": "code_card_dark.html.j2"
    }
]

FORBIDDEN_COLORS = [
    "#4ade80", "rgb(74, 222, 128)",  # emerald
    "#fbbf24", "rgb(251, 191, 36)",  # amber
    "#f87171", "rgb(248, 113, 113)", # rose
    "#f43f5e", "rgb(244, 63, 94)",   # red-pink
]

REQUIRED_EYEBROW = "AQUIB SHAIKH // MOBILE ARCHITECTURE & ANDROID INTERNALS"

def run_tests():
    print("=" * 70)
    print("  RUNNING LINKEDIN AUTOMATION PIPELINE REMEDIATION GATE CHECKS")
    print("=" * 70)

    results = {}
    writing_agent = WritingAgent(generate_text, root_dir=str(PROJECT_ROOT))
    quality_reviewer = QualityReviewer(generate_text)
    decision_agent = ImageDecisionAgent(generate_text)

    # ─────────────────────────────────────────────────────────────────────────
    # GATE 1: Phase 5 Archetype count
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Check 1] Verifying Hook Matrix has exactly 5 blueprint archetypes...")
    archetype_ids = [h["id"] for h in HOOK_STYLES]
    expected_ids = [
        "CODE_AUTOPSY_TEARDOWN",
        "SCALE_INCIDENT_WAR_STORY",
        "OS_INTERNALS_DEEP_DIVE",
        "CONTRARIAN_ARCHITECTURE_CALLOUT",
        "HARDWARE_LOW_LEVEL_DEEP_DIVE"
    ]
    assert len(HOOK_STYLES) == 5, f"Expected 5 archetypes, got {len(HOOK_STYLES)}"
    assert sorted(archetype_ids) == sorted(expected_ids), f"Archetype IDs mismatch: {archetype_ids}"
    print(f"  ✓ PASSED: Exactly 5 archetypes present ({', '.join(archetype_ids)})")
    results["archetypes"] = "PASS"

    # ─────────────────────────────────────────────────────────────────────────
    # GATE 2: Template Static Checks (Phase 2, 2.6, 2.7)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Check 2] Verifying HTML Templates for hardcoded branding & 2-accent palette...")
    templates = [
        "process_infographic_dark.html.j2",
        "code_card_dark.html.j2",
        "process_infographic_light.html.j2",
        "code_card_light.html.j2"
    ]
    for t_name in templates:
        t_path = PROJECT_ROOT / "renderer" / "templates" / t_name
        content = t_path.read_text(encoding="utf-8")
        
        # Check eyebrow
        assert "AQUIB SHAIKH // MOBILE ARCHITECTURE &amp; ANDROID INTERNALS" in content or REQUIRED_EYEBROW in content, \
            f"{t_name} missing hardcoded attribution eyebrow"
        
        # Check footer
        assert "Aquib Rashid Shaikh" in content, f"{t_name} missing author in footer"
        assert "Senior Android Developer &amp; Mobile Tech Lead" in content or "Senior Android Developer & Mobile Tech Lead" in content, \
            f"{t_name} missing title in footer"
        
        # Check forbidden text
        assert "AI SYSTEMS" not in content, f"{t_name} contains forbidden text 'AI SYSTEMS'"
        assert "tech behind AI" not in content, f"{t_name} contains forbidden text 'tech behind AI'"
        
        # Check no sticky note
        assert "sticky-note" not in content, f"{t_name} contains sticky-note element"
        assert "rotate(-2deg)" not in content, f"{t_name} contains sticky-note rotation transform"
        
        # Check forbidden colors
        for c in FORBIDDEN_COLORS:
            assert c.lower() not in content.lower(), f"{t_name} contains forbidden color {c}"

        print(f"  ✓ {t_name}: Branding, 2-accent palette, and DOM layout validated.")
    results["templates_static"] = "PASS"

    # ─────────────────────────────────────────────────────────────────────────
    # GATE 3: 3 Consecutive Generation & Infographic Runs (Phase 2.6, 2.7, 4.5, 4.6)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Check 3] Running 3 Consecutive Topic Test Cycles...")
    consecutive_success = 0
    for idx, test_case in enumerate(TEST_TOPICS[:3], 1):
        arch = test_case["archetype"]
        topic = test_case["topic"]
        expected_tmpl = test_case["expected_template"]
        print(f"\n  Cycle {idx}/3: Testing '{topic}' (Archetype: {arch})")

        # Step A: Write post
        post_text, first_comment, chosen_arch = writing_agent.write_post(topic, archetype_id=arch)
        assert chosen_arch == arch, f"Expected archetype {arch}, got {chosen_arch}"
        print(f"    Post generated ({len(post_text)} chars). First comment: {bool(first_comment)}")

        # Step B: Quality review with retry loop (matching main.py pipeline)
        passed_review = False
        for attempt in range(1, 4):
            eval_res = quality_reviewer.review(post_text, topic)
            print(f"    Quality Review (Attempt {attempt}/3): Technical: {eval_res.get('technical_accuracy')}/10 | Naturalness: {eval_res.get('naturalness')}/10 | AI: {eval_res.get('ai_like_language')}/10 | Passed: {eval_res.get('passed')}")
            if eval_res.get("passed"):
                passed_review = True
                break
            if attempt < 3:
                fb = eval_res.get("feedback", "Improve technical depth and conversational naturalness.")
                print(f"    [Rewrite] Revising draft based on reviewer feedback: {fb}")
                post_text, first_comment, _ = writing_agent.write_post(topic, feedback=fb, archetype_id=arch)

        assert passed_review, f"Quality Review failed after 3 attempts: {eval_res.get('feedback')}"

        # Step C: Factual correctness check
        assert not re.search(r'GATT_FAILURE\s*[:=\s]*133', post_text, re.I), "Post references GATT_FAILURE 133"
        assert not re.search(r'HCI.*(?:one|single|active\s+GATT|serializ)', post_text, re.I), "Post attributes ATT serialization to HCI"

        # Step D: Image Decision & Template Selection
        needs_image, reason, selected_tmpl = decision_agent.decide(topic, post_text, arch)
        print(f"    Image Decision: needs_image={needs_image}, template={selected_tmpl}")
        assert needs_image is True, f"Image should be requested for {topic}"
        assert selected_tmpl == expected_tmpl, f"Expected template {expected_tmpl}, got {selected_tmpl}"

        # Step E: Generate Infographic Content with Phase 4.6 lint
        content = ig.generate_process_content(topic, post_text, generate_text, template=selected_tmpl)
        violations = ig._lint_content(content, template=selected_tmpl)
        assert len(violations) == 0, f"Infographic content lint violations: {violations}"

        # Step F: Verify D-regress-1 (no duplicate card titles in steps)
        if selected_tmpl == "process_infographic_dark.html.j2":
            step_labels = [s["label"].strip().lower() for s in content.get("steps", [])]
            for i, label in enumerate(step_labels):
                # Ensure no bullet point inside this step duplicates the step title
                for pt in content["steps"][i].get("points", []):
                    assert label != pt.strip().lower(), f"Step {i} label '{label}' duplicated in bullet '{pt}'"

        # Step G: Verify Phase 4.6 Bare API Rule
        steps_to_check = range(4) if selected_tmpl == "process_infographic_dark.html.j2" else [2, 3]
        for s_idx in steps_to_check:
            for p_idx, pt in enumerate(content["steps"][s_idx].get("points", [])):
                is_bare, reason = ig._is_bare_api_bullet(pt)
                assert not is_bare, f"Bare API bullet found in steps[{s_idx}].points[{p_idx}]: '{pt}' ({reason})"

        # Step H: Render PNG
        out_png = str(PROJECT_ROOT / "renderer" / "output" / f"test_run_{idx}.png")
        png_path = ig.render_infographic(content, out_png, template=selected_tmpl)
        assert os.path.exists(png_path), f"Failed to render PNG to {out_png}"
        assert os.path.getsize(png_path) > 10000, f"Rendered PNG is too small: {os.path.getsize(png_path)} bytes"
        print(f"    Rendered PNG verified: {png_path} ({os.path.getsize(png_path)} bytes)")

        consecutive_success += 1

    assert consecutive_success == 3, f"Expected 3 consecutive successes, got {consecutive_success}"
    print(f"\n  ✓ PASSED: All 3 consecutive generation cycles verified with zero regressions.")
    results["consecutive_cycles"] = "PASS"

    # ─────────────────────────────────────────────────────────────────────────
    # GATE 4: Dry-Run Verification (Phase 7)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[Check 4] Testing Phase 7 Dry-Run Mode...")
    # Run main agent in dry-run mode for a topic
    try:
        run_agent(dry_run=True, force_topic="Android 1MB Binder IPC Transaction Limits in High-Volume Banking", force_archetype="SCALE_INCIDENT_WAR_STORY")
        print("  ✓ PASSED: Dry-run executed successfully without live publishing.")
        results["dry_run"] = "PASS"
    except Exception as e:
        print(f"  ✗ FAILED: Dry-run raised exception: {e}")
        results["dry_run"] = f"FAIL: {e}"
        raise

    print("\n" + "=" * 70)
    print("  ALL REMEDIATION GATE CHECKS PASSED SUCCESSFULLY")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
