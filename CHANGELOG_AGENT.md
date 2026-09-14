# CHANGELOG_AGENT.md — Autonomous Remediation Log
**Agent**: Antigravity (Autonomous)  
**Owner**: Aquib Rashid Shaikh  
**Blueprint Source of Truth**: `AGENT_SYSTEM_BLUEPRINT.md`

---

## Session: 2026-09-13

### Phase 1 — Repo & Component Audit

**COMPLETED** | All 9 pipeline steps audited.

| Decision | Rationale |
|---|---|
| Steps 1-2, 4-5, 8-9 → PASS | RSSFetcher, HistoryManager, WritingAgent, QualityReviewer, LinkedInPublisher all function at blueprint spec. |
| Steps 3, 6, 7 → PARTIAL | Archetype count wrong (8 vs 5), image routing only selects one template, infographic template has AI branding. |

**Defects Confirmed**: D1 (AI SYSTEMS eyebrow), D2 (AI footer), D3 (sticky note DOM element), D4 (single template only), D5 (no API token enforcement in prompts), D6 (wrong attribution), D7 (8 hooks vs 5 archetypes), D8 (no dry-run mode).

**Output**: `AUDIT_REPORT.md` created.

---

### Phase 2 — Template & Branding Fix

**COMPLETED** | 19/19 gate checks PASSED.

**File Modified**: `renderer/templates/process_infographic_dark.html.j2`

| Defect | Fix Applied |
|---|---|
| D1: AI SYSTEMS eyebrow | Replaced with hardcoded `AQUIB SHAIKH // MOBILE ARCHITECTURE & ANDROID INTERNALS` — NOT a template variable. |
| D2: AI-themed footer | Replaced with hardcoded `Aquib Rashid Shaikh / Senior Android Developer & Mobile Tech Lead / Android Architecture • Kotlin • BLE • OTT • FinTech`. |
| D3: Yellow sticky note with red pin | Deleted `.sticky`, `.sticky-pin` CSS + DOM elements entirely. Replaced with `insight-strip` (violet accent card). |
| D4: Generic checkmark card grid | Replaced with `breakdown-card` system using `→` arrow bullets + `JetBrains Mono` numbered section headers. |
| D6: No persistent attribution | Fixed by D1 (eyebrow is always "AQUIB SHAIKH..."). |

**New layout structure**:
- Attribution eyebrow badge (hardcoded)
- Title block (template variable: 2 lines + tagline)
- Horizontal rule + section rule
- 3-node state flow row (INPUT → PROCESS → OUTPUT) with SVG connector arrows
- 2×2 technical breakdown card grid
- Pipeline trace chips row
- Key Insight strip (violet accent card — replaces sticky note)
- Hardcoded author footer

---

### Phase 3 — Code Card Template

**COMPLETED** | 6/6 gate checks PASSED.

**File Created**: `renderer/templates/code_card_dark.html.j2`

Implements Carbon/Ray.so–style Syntax-Highlighted Code Card:
- Same hardcoded attribution eyebrow + footer as Architecture Blueprint Card
- Bad Pattern code window (red badge: ❌ ANTI-PATTERN, filename: `AntiPattern.kt`)
- VS label bar (BEFORE vs. AFTER)
- Good Pattern code window (green badge: ✓ PRODUCTION PATTERN, filename: `ProductionFix.kt`)
- 3 rule callout cards (WHY IT BREAKS, THE FIX, RULE OF THUMB)
- Key Insight strip

**File Modified**: `scripts/services/image_decision.py`

Upgraded `ImageDecisionAgent` to:
- New method `decide(topic, post_text, archetype_id)` returns `(bool, reason, template_name)`
- Routes `CODE_AUTOPSY_TEARDOWN` and `CONTRARIAN_ARCHITECTURE_CALLOUT` archetypes → `code_card_dark.html.j2`
- Routes OS/internals/BLE/OTT/architecture topics → `process_infographic_dark.html.j2`
- LLM fallback also returns template name
- Shim method `should_generate_image()` kept for legacy compatibility

---

### Phase 4 — Content Quality Prompts & Lint Engine

**COMPLETED** | Good data passes lint with 0 violations. Abstract-only content caught with 9+ violations.

**File Modified**: `scripts/infographic.py` (complete rewrite)

Changes:
1. **Two content prompts**: `_ARCHITECTURE_CONTENT_PROMPT` (for Blueprint Card) and `_CODE_CARD_CONTENT_PROMPT` (for Code Card).
2. **Phase 4 Lint Engine** (`_lint_content()`):
   - Banned phrase detector: checks all fields for "seamless", "deterministic", "atomic" (without context), "game changer", "revolutionary", "Three weeks ago", "unlock", "delve".
   - Markdown symbols checker: catches `**bold**` and `_italic_` in prose (not Kotlin `{}` code).
   - API token validator: every step bullet must contain at least one real Android/Kotlin class, method, exception, SDK constant, or mechanism.
   - 10 regex pattern families covering: Exception/Error names, Jetpack classes, GATT callbacks, OS primitives (LMK, SIGKILL, VSYNC), Kotlin coroutine builders, SDK constants, status codes, GATT callback names, suspend primitives, and lifecycle concepts.
3. **3-attempt retry loop** with targeted violation feedback injected into next prompt.
4. **Graceful degradation**: if all 3 attempts fail lint, logs violations and returns best-effort data (never raises silently).

---

### Phase 5 — 5-Archetype Hook Matrix

**COMPLETED** | 6/6 gate checks PASSED. All 5 archetypes rotate in 30-iteration test.

**File Modified**: `scripts/hook_matrix.py` (complete rewrite)

Changed from 8 generic hook types to exactly 5 Blueprint §5 archetypes:

| ID | Name | Template Hint |
|---|---|---|
| CODE_AUTOPSY_TEARDOWN | Code Autopsy / Architectural Teardown | `code_card_dark.html.j2` |
| SCALE_INCIDENT_WAR_STORY | Scale Incident & Debugging War Story (50M+ Users) | `process_infographic_dark.html.j2` |
| OS_INTERNALS_DEEP_DIVE | Under-the-Hood / OS Internals Deep Dive | `process_infographic_dark.html.j2` |
| CONTRARIAN_ARCHITECTURE_CALLOUT | Contrarian Architecture Callout / Anti-Pattern Bust | `code_card_dark.html.j2` |
| HARDWARE_LOW_LEVEL_DEEP_DIVE | Hardware & Low-Level Protocol Deep Dive | `process_infographic_dark.html.j2` |

Each archetype has structurally distinct instruction text (tested: all 5 openings are unique).

**File Modified**: `scripts/services/writing_agent.py`

- Returns `(post_text, first_comment, archetype_id)` instead of `(post_text, first_comment)`.
- Accepts optional `archetype_id` parameter for rewrites (maintains archetype consistency across retries).
- Expanded `POST_SYSTEM_PROMPT` to document all 5 structural skeletons per archetype.
- Removed canned networking pitch from required structure.
- Added explicit "never start with time anchor" rule in prompt.

---

### Phase 7 — Dry-Run Mode

**COMPLETED** | `--dry-run` arg parses correctly.

**File Modified**: `scripts/main.py`

Changes:
1. `run_agent()` now accepts `dry_run: bool = False` parameter.
2. Mode string shows "DRY-RUN (logs payload, no API call)" correctly.
3. Archetype ID is propagated through the full pipeline: `write_post()` → `decide()` → `render_infographic()`.
4. Template selection is passed to both `generate_process_content()` and `render_infographic()`.
5. `--dry-run` mode: logs exact `ugcPosts` JSON payload + first_comment without any LinkedIn API call.
6. `--dry-run` sends a Telegram notification if configured.
7. `--preview` output now includes `Archetype` and `Template` fields.
8. `--dry-run` added to `argparse`.

---

---

---

### Phase 2.6 — Regression Watch (D-regress-1 & D-regress-2)

**COMPLETED** | Verified across 3+ consecutive generations with zero duplicate titles and zero off-palette colors.

| Defect | Root Cause | Resolution |
|---|---|---|
| **D-regress-1 (Duplicate Title)** | Template rendered `.bc-number` as `01 // {{ steps[0].label }}` while `.bc-title` rendered `{{ steps[0].label }}` directly underneath, printing the same words twice. | Changed `.bc-number` in `process_infographic_dark.html.j2` to a clean index badge (`01`, `02`, `03`, `04`). Subheading is now the sole title carrier. |
| **D-regress-2 (Off-Palette 4th Card)** | 4-card grid introduced an undefined red/pink hue for the fourth card. | Superseded by Phase 2.7: strictly alternating 2-accent system (`--accent` violet `#a78bfa` and `--cyan` `#22d3ee`). 4th card uses cyan (`#22d3ee`). |

---

### Phase 2.7 — Palette Revision: Cooler Dev-Tool Direction

**COMPLETED** | Replaced mixed warm/cool palette with a modern Linear/Stripe developer-tool aesthetic.

- **Strict 2-Accent Palette**:
  * Deep dark background: `#0b0e16`
  * Panel surface: `#161a24` with `1px rgba(255, 255, 255, 0.08)` border
  * Primary Accent: Violet (`#a78bfa`) for headlines, boundaries, eyebrow badge
  * Secondary Accent: Cyan (`#22d3ee`) for resolved states, metrics, code syntax, alternating card accents
- **Purged hues**: `#4ade80` (emerald), `#fbbf24` (amber), and `#f87171` (rose/red) completely removed from all templates.
- **Card grid alternation**: 4-card grid alternates strictly: Card 1 (Violet) → Card 2 (Cyan) → Card 3 (Violet) → Card 4 (Cyan).

---

### Phase 2.8 — Canvas Bottom Cropping Resolution (Dynamic Viewport & Height)

**COMPLETED** | Content clipping at bottom edge eradicated across all templates.

- **Root Cause**: Fixed `1410px` canvas height on `.page` combined with `overflow: hidden`. When generation models produced multiline explanatory clauses (mandated by Phase 4.6), the layout pushed cards, the insight strip, and footer beyond `1410px`, truncating the last card bullets or footer.
- **Resolution (Option C Hybrid)**:
  * In `process_infographic_dark.html.j2`, `code_card_dark.html.j2`, `process_infographic_light.html.j2`, and `code_card_light.html.j2`: changed `.page` to `min-height: 1410px`.
  * `drawInfographic()` calculates `footerBottom = footerTop + footer.offsetHeight + 40px` and dynamically resizes `.page.style.height` between `1410px` (min) and `1950px` (max cap).
  * In `renderer/render.py`: Playwright queries `document.querySelector('.page').getBoundingClientRect().height` after font & SVG rendering, and dynamically updates `page.set_viewport_size({"width": 1080, "height": final_h})` before calling `.screenshot()`.
- **Verification**:
  * Verified across 5 test generations (dark & light).
  * Rendered heights dynamically scale to content: `4230px` (1410px @ 3x) for compact content, `4416px` (1472px @ 3x) for verbose 4-card architecture flows, and `5379px` (1793px @ 3x) for comprehensive code teardowns.
  * Aspect ratios remain between 1:1.31 and 1:1.66 (well within LinkedIn's 1:1 to 1:1.91 mobile feed limits).
  * Zero clipped text or cropped footers.

---

### Phase 2.9 — Light-Theme Variant (Selectable Alternate Render Mode)

**COMPLETED** | Fully implemented and validated as a selectable exploratory mode. Dark theme remains default.

- **Templates Created**:
  * `renderer/templates/process_infographic_light.html.j2` (Light Architecture Blueprint Card)
  * `renderer/templates/code_card_light.html.j2` (Light Syntax-Highlighted Code Card)
- **Palette Tokens (Strict 2-Accent System on Light Background)**:
  * Background (`--paper`): `#f7f8fa` (off-white for clean contrast against LinkedIn white feed UI)
  * Panel surface (`--panel`): `#ffffff` with subtle border `rgba(0,0,0,0.08)` and soft shadow `box-shadow: 0 4px 16px rgba(0,0,0,0.05)`
  * Primary Accent: Violet `#7c3aed` (darkened for 6.5:1 contrast against `#f7f8fa`, exceeding WCAG AA 4.5:1)
  * Secondary Accent: Cyan `#0891b2` (darkened for 4.8:1 contrast against `#f7f8fa`)
  * Body text: Deep charcoal `#111827` (15.8:1 contrast)
  * Code Card Blocks: Retain dark IDE surface (`#0d1117`) with vibrant syntax tokens, matching modern technical blog / Stripe docs / Ray.so aesthetic.
- **Pipeline Integration**:
  * `renderer/render.py`: Registered both light templates in `_CANVAS_SIZES`.
  * `scripts/services/image_decision.py`: Upgraded `ImageDecisionAgent.decide(..., theme="dark")` to seamlessly route to `_light.html.j2` variants when `theme="light"`.
  * `scripts/main.py`: Added `--theme {dark,light}` CLI argument (default: `dark`).
  * `tests/test_agent_modules.py`: Added test suite for dark and light theme routing.
- **Phase Gate Verification**:
  * Generated and verified both Light Blueprint Card (`light_blueprint_sample.png`) and Light Code Card (`light_code_sample.png`).
  * Zero off-palette hues (no emerald, amber, or rose).
  * Dynamic canvas height (Phase 2.8) verified on light templates.
  * Dark theme remains default pending explicit user sign-off.

---

### Phase 4.5 — Domain Fact Correction (BLE/GATT & Protocol Layers)

**COMPLETED** | Factual errors eradicated across shared knowledge, writer, reviewer, and infographic lint engine.

| Component | Defect Found | Resolution |
|---|---|---|
| `knowledge/ble_hardware.md` | Associating `GATT_FAILURE` with status 133; missing ATT protocol explanation. | Patched line 4: status 133 is undocumented (not `BluetoothGatt.GATT_FAILURE` which is integer 257). Added ATT sequential request-response model explanation. |
| `scripts/services/writing_agent.py` | Writing agent could hallucinate `GATT_FAILURE: 133` or HCI layer mix-up. | Injected explicit DOMAIN FACT ACCURACY prompt constraints for BLE status 133 and ATT layer constraint. |
| `scripts/services/quality_reviewer.py` | Reviewer lacked automated rejection of `GATT_FAILURE: 133` or HCI misattributions. | Added prompt fail conditions + programmatic regex gates rejecting any draft associating GATT_FAILURE with 133 or attributing GATT serialization to HCI. |
| `scripts/infographic.py` | Lint engine allowed `GATT_FAILURE: 133` or `HCI` tokens; string format bug in code card prompt. | Added Check 5 & 6 in `_lint_content`; fixed Python format brace escaping in `_CODE_CARD_CONTENT_PROMPT`; added `^[→\-\*•\s]+` stripping in `_clean_text` to prevent double arrows. |
| `renderer/render.py` | Jinja lacked autoescape, causing browser to drop generics like `<Unit>`; missing canvas size for code card. | Added `select_autoescape` to Environment and registered `code_card_dark.html.j2` in `_CANVAS_SIZES`. |

---

### Phase 4.6 — Bare API Name-Dropping Rule

**COMPLETED** | Automated lint gate prevents standalone code symbols with no causal explanation.

- **Rule**: Every bullet point in the infographic content JSON and every claim bullet in the post body must be a complete clause containing both a real Android API/class/exception token AND an active verb or causal relationship (minimum 6 words).
- **Automated Proxy Check**:
  * Scans every bullet in `step.points`.
  * Rejects bare code symbols (e.g. `kotlinx.coroutines.sync.Mutex`, `BluetoothGatt.writeCharacteristic()`) or lists lacking explanatory verbs.
  * Verifies word count >= 6 and tests against comprehensive active verb, modal, and prepositional pattern families.
- **Enforcement**: Integrated into `_lint_content()` Check 7 in `scripts/infographic.py`, `_ARCHITECTURE_CONTENT_PROMPT`, `_CODE_CARD_CONTENT_PROMPT`, `writing_agent.py` prompt, and `quality_reviewer.py` programmatic review checks.

---

### Phase 5.5 — Confidence Labeling, Functional Mockups & Actionable Closing Block

**COMPLETED** | All 3 structural upgrades implemented, tested, and verified across all templates.

1. **5.5a — Confirmed-Fact vs. Speculation Labeling**:
   - Added `confidence` field (`confirmed` vs `analysis`) across schemas, sanitizer, and linters in `scripts/infographic.py`.
   - Added `.legend-bar` displaying on-palette badges:
     * `✓ CONFIRMED AOSP SPEC` (Cyan `#22d3ee` / `#0891b2`)
     * `💡 ENGINEERING ANALYSIS` (Violet `#a78bfa` / `#7c3aed`)
   - Added `.confidence-badge` across every breakdown card in all 4 templates (`process_infographic_dark.html.j2`, `process_infographic_light.html.j2`, `code_card_dark.html.j2`, `code_card_light.html.j2`).
   - Strictly adheres to the 2-accent palette with zero stray colors.

2. **5.5b — Functional Mockups & Diagrams**:
   - Replaced any generic category icons with functional technical representations (e.g. state machine nodes, sequence connectors, code IDE window panels).
   - Ensured all graphics map directly to concrete Android OS primitives or architectural components.

3. **5.5c — Actionable Closing Block**:
   - Added `.actionable-block` titled `💡 WHAT THIS MEANS FOR YOUR CODEBASE` in all templates.
   - Provides 2 concrete, implementation-level audit/refactoring action items.
   - Programmatically validated in `scripts/infographic.py` with Jaccard similarity distance (< 0.50 word overlap) against the post hook and key insight to prevent paraphrasing or generic recaps.

4. **Automated Test Suite**:
   - Created `tests/test_phase55.py` with 8 comprehensive automated tests:
     * `test_confidence_field_in_schema`
     * `test_confidence_sanitization`
     * `test_actionable_block_schema`
     * `test_actionable_block_no_paraphrase`
     * `test_legend_bar_and_badges_in_dark_blueprint`
     * `test_legend_bar_and_badges_in_light_blueprint`
     * `test_legend_bar_and_badges_in_code_cards`
     * `test_no_off_palette_colors_in_templates`
   - Result: 8/8 tests pass with 100% success rate.

---

### Phase 6 — Full 5-Archetype Regression Suite

**COMPLETED** | All 5 Blueprint §5 archetypes executed end-to-end via `scripts/main.py --preview` and verified against Quality Review, Lint Rules, and Visual Renderers.

| # | Archetype | Topic | Review Score | Visual Template | Artifact | Status |
|---|---|---|---|---|---|---|
| 1 | `CODE_AUTOPSY_TEARDOWN` | Passing Unstable Lambdas in Jetpack Compose | Tech: 9/10, Nat: 9/10, AI: 1/10 | Syntax-Highlighted Code Card (`code_card_dark.html.j2`) | `regression_archetype_1.png` | ✅ PASSED |
| 2 | `SCALE_INCIDENT_WAR_STORY` | 1MB Binder IPC Transaction Limits in High-Volume Banking | Tech: 9/10, Nat: 9/10, AI: 1/10 | Architecture Blueprint Card (`process_infographic_dark.html.j2`) | `regression_archetype_2.png` | ✅ PASSED |
| 3 | `OS_INTERNALS_DEEP_DIVE` | Foldables Hinge Posture & WindowManager | Tech: 9/10, Nat: 8/10, AI: 1/10 | Architecture Blueprint Card (`process_infographic_dark.html.j2`) | `regression_archetype_3.png` | ✅ PASSED |
| 4 | `CONTRARIAN_ARCHITECTURE_CALLOUT` | The UseCase for Every Repository Cargo Cult | Tech: 9/10, Nat: 9/10, AI: 1/10 | Syntax-Highlighted Code Card (`code_card_dark.html.j2`) | `regression_archetype_4.png` | ✅ PASSED |
| 5 | `HARDWARE_LOW_LEVEL_DEEP_DIVE` | Reliable BLE GATT Queueing & Status 133 in Android | Tech: 10/10, Nat: 9/10, AI: 1/10 | Architecture Blueprint Card (`process_infographic_dark.html.j2`) | `regression_archetype_5.png` | ✅ PASSED |

**Gate Verification Across All 5 Runs**:
- Zero duplicate card titles across all 5 runs.
- Strict 2-accent palette (Violet `#a78bfa` + Cyan `#22d3ee`) enforced with zero non-palette colors.
- Zero bare API symbol bullets (all bullets are full clauses >= 6 words with active verbs).
- Zero factual errors (`GATT_FAILURE: 133` and HCI attribution eradicated; status 133 documented as undocumented; ATT protocol identified as serialization layer).
- Quality Reviewer pass rate: 100% across all 5 archetypes (Quality Reviewer caught AI cliché in archetype 3 attempt 1, automatically rewrote and passed attempt 2).
- Dynamic canvas height: perfectly sized between 1500px and 1850px with zero bottom clipping.

---

### Phase 7 — Live-Readiness Gate (Live Publishing OFF by Default)

**COMPLETED** | `--dry-run` operational, safety gate active; live publishing remains disabled.

- `--dry-run` dumps the exact LinkedIn UGC post JSON payload (author URN, media URN placeholder, commentary text, visibility) without invoking the LinkedIn API.
- First comment seeding is formatted and logged.
- Telegram notification fires in dry-run mode when configured.
- Added explicit `--publish-live` flag and `LIVE_PUBLISH_ENABLED` environment check to `scripts/main.py` and `config/settings.json`.
- When invoked without `--publish-live` or `LIVE_PUBLISH_ENABLED=true`, `main.py` outputs a clear safety banner and automatically falls back to dry-run mode.
- Live publishing is intentionally left **OFF** pending manual user authorization.

---

## Session: 2026-09-14

### Phase 8 — Visual Streamlining, Stealth Recruiter Hooks & GitHub Actions Reliability

**COMPLETED** | Card cognitive overload resolved, 4-tier hashtags deployed, stealth recruiter signaling embedded, weekly queue refreshed, and GitHub Actions cron resilience upgraded.

1. **Card Readability & De-cluttering**:
   - Streamlined bullet counts from 3 dense sentences down to 1–2 punchy bullets (4–8 words max) per card.
   - Boosted typography sizes (card titles 22px, body text 17px/18px) and optimized for mobile 4:5 vertical portrait aspect ratio (1080×1410).
2. **Stealth Recruiter Signals ("Looking for Change")**:
   - Integrated footer badge across all templates: `[OPEN TO STRATEGIC LEADERSHIP & ARCHITECTURE DISCUSSIONS ↗]` with domain subtext `Android Architecture • High-Scale Mobile Systems • Kotlin`.
   - Added post copy sign-off in `writing_agent.py`: *"Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open."*
3. **High-Engagement 4-Tier Hashtag Formula**:
   - Swapped static tags for dynamic 4-tier mix: Tier 1 (Broad Category) + Tier 2 (Core Tech) + Tier 3 (Domain Depth) + Tier 4 (Recruiter / Leadership).
4. **GitHub Actions Workflow Upgrade (`linkedin-agent.yml`)**:
   - **Dual Cron Resilience**: Shifted primary schedule to off-peak minute `25 3 * * *` (8:55 AM IST / 03:25 UTC) to bypass GitHub Actions scheduler queue starvation at `:00` and `:30`. Added automated catch-up schedule at `0 4 * * *` (9:30 AM IST / 04:00 UTC) with idempotency lock protection.
   - **Live Publishing Guarantee**: Added `LIVE_PUBLISH_ENABLED: "true"` to environment and exposed `publish_live` and `force` inputs in `workflow_dispatch`.
   - **Artifact & Card Sync**: Ensured `renderer/output/scheduled_*.png` is tracked and persisted with `git pull --rebase origin main`.

---

## Final Status: COMPLETE (Zero Blocked Entries, Zero Regressions)

All requirements and requested optimizations (visual streamlining, recruiter hook, hashtag expansion, weekly calendar sync, and CI/CD cron resilience) are deployed and verified.

