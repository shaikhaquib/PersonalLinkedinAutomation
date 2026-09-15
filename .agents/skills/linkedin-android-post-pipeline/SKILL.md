---
name: linkedin-android-post-pipeline
description: >-
  Generate Senior Android Developer LinkedIn posts with v2 editorial infographic
  cards (Architecture Blueprint or Code Autopsy), render PNGs via Playwright,
  and schedule into the content calendar for 09:00 AM IST auto-publish.
  Use when creating, styling, rendering, or scheduling LinkedIn posts for
  PersonalLinkedinAutomation repo.
---

# LinkedIn Android Post Pipeline — v2 Editorial Style

## Repository

- **Path:** `/Users/perennial/Documents/Personal/LinkedinPostAutomation/LinkedIN-Post-automation`
- **Remote:** `shaikhaquib/PersonalLinkedinAutomation` (public — required for GitHub Actions `schedule` cron)
- **Timezone:** `Asia/Kolkata` (IST). Default publish slot: **09:00**

## When to use this skill

Trigger when the user asks to:
- Create a new LinkedIn post
- Generate or redesign infographic images
- Schedule a post for tomorrow or a specific date
- Refresh card visuals to match the new editorial look

---

## Quick commands (preferred path)

Always activate venv first:

```bash
cd /Users/perennial/Documents/Personal/LinkedinPostAutomation/LinkedIN-Post-automation
source .venv/bin/activate
```

### Schedule a new post (full pipeline: write → QA → render → calendar)

```bash
# Tomorrow 09:00 IST
python scripts/scheduler.py --schedule-tomorrow

# Specific date
python scripts/scheduler.py --schedule-date 2026-09-20 --time 09:00

# With custom topic + archetype + theme
python scripts/scheduler.py --schedule-date 2026-09-20 \
  --topic "Your topic here" \
  --archetype CODE_AUTOPSY_TEARDOWN \
  --theme dark
```

### Preview / test without scheduling

```bash
python scripts/main.py --preview --topic "Your topic"
python scripts/main.py --dry-run --topic "Your topic"
```

### Manage queue

```bash
python scripts/scheduler.py --list
python scripts/scheduler.py --publish-due          # manual publish today's due post
```

### Run tests after template changes

```bash
python -m unittest discover tests -q
```

---

## End-to-end pipeline (what the agent must do)

Follow this exact order when scheduling a post:

### Step 1 — Write post (`WritingAgent`)
- Persona: **Senior Android Developer & Mobile Tech Lead**, 8+ years
- Config: `config/persona.json`
- Grounding: `knowledge/*.md` domain guides
- Pick one of **5 archetypes** from `scripts/hook_matrix.py`:
  1. `CODE_AUTOPSY_TEARDOWN` → usually **Code Card**
  2. `SCALE_INCIDENT_WAR_STORY` → usually **Architecture Card**
  3. `OS_INTERNALS_DEEP_DIVE` → usually **Architecture Card**
  4. `CONTRARIAN_ARCHITECTURE_CALLOUT` → usually **Code Card**
  5. `HARDWARE_LOW_LEVEL_DEEP_DIVE` → usually **Architecture Card**

**Post structure (required):**
1. Strong technical hook (no time anchors like "three weeks ago")
2. Mechanism explanation with real Android/Kotlin APIs
3. 3 bullet production fixes
4. Engagement question
5. Recruiter hook (stealth, not #OpenToWork):
   > "Scaling high-impact mobile platforms or engineering teams? Open to exchanging notes with mobile leaders — DMs are open."
6. **4–5 hashtags** on last line (mix broad + niche)

**Banned phrases:** see `config/persona.json` — no "game changer", "revolutionary", "unlock the power of", etc.

**Output split:** post text + `---FIRST_COMMENT---` + first comment (author seed comment for LinkedIn)

### Step 2 — Quality review (`QualityReviewer`)
- Up to **3 rewrite attempts**
- Must pass: technical accuracy, naturalness, low AI-like language
- Proceed with best candidate if borderline

### Step 3 — Image decision (`ImageDecisionAgent`)
Only **two** visual templates allowed:

| Template | File | Use for |
|----------|------|---------|
| Architecture Blueprint | `process_infographic_{dark,light}.html.j2` | OS internals, BLE/IPC flows, pipelines, scale incidents |
| Code Autopsy | `code_card_{dark,light}.html.j2` | Before/after Kotlin teardowns, anti-patterns |

Text-only for pure opinion/career posts.

Logic: `scripts/services/image_decision.py`

### Step 4 — Generate card JSON (`scripts/infographic.py`)
Call `generate_process_content(topic, post_text, llm_fn, template=...)`
- Runs lint (`_lint_architecture_content` or `_lint_code_card_content`)
- Up to 3 regeneration attempts on lint failure

### Step 5 — Render PNG (`render_infographic`)
```python
import scripts.infographic as ig
content = ig.generate_process_content(topic, post_text, generate_text, template=selected_template)
png_path = ig.render_infographic(content, out_png, template=selected_template)
```

Output path convention:
`renderer/output/scheduled_{YYYY-MM-DD}_{HHMM}.png`
Example: `renderer/output/scheduled_2026-09-17_0900.png`

**PNG git rule:** `renderer/output/*.png` is gitignored EXCEPT `scheduled_*.png` — use `git add -f` for scheduled PNGs.

### Step 6 — Schedule (`CalendarManager`)
Writes to:
- `data/content_calendar.json` (machine queue)
- `CONTENT_CALENDAR.md` (human-readable)

Entry fields:
```json
{
  "id": "post_2026-09-20_0900",
  "scheduled_date": "2026-09-20",
  "scheduled_time": "09:00",
  "timezone": "Asia/Kolkata",
  "topic": "...",
  "archetype": "CODE_AUTOPSY_TEARDOWN",
  "post_text": "...",
  "first_comment": "...",
  "image_path": "renderer/output/scheduled_2026-09-20_0900.png",
  "template": "code_card_dark.html.j2",
  "theme": "dark",
  "status": "scheduled"
}
```

### Step 7 — Auto-publish (GitHub Actions)
Workflow: `.github/workflows/linkedin-agent.yml`
- Cron: `25 3 * * *` (8:55 AM IST) + backup `0 4 * * *` (9:30 AM IST)
- `main.py` checks `calendar.get_due_post()` and publishes today's scheduled entry
- Requires secrets: `GEMINI_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_ID`

---

## v2 Visual Design System (CRITICAL — do NOT use old Phase 5.5 layout)

### Design philosophy
- **Editorial, not dashboard.** No legend bars, confidence badges, breakdown cards, insight strips, or "WHAT THIS MEANS FOR YOUR CODEBASE" blocks.
- **One focal visual** + **3 takeaways** + **minimal footer**.
- **Content-height canvas** — NO forced 1180px minimum (causes huge bottom dead space).

### Shared design tokens (both card types)

| Token | Dark | Light |
|-------|------|-------|
| Paper/bg | `#12141a` | `#f8f9fc` |
| Surface | `#1a1d26` | `#ffffff` |
| Ink/text | `#f3f4f6` | `#111827` |
| Muted | `#9ca3af` | `#6b7280` |
| Accent (purple) | `#7c6cff` | `#6d5cff` |
| Success/cyan | `#34d399` | `#059669` |
| Code bg | `#0d1117` | `#0f172a` |

**Fonts:** DM Sans (headlines/body) + JetBrains Mono (labels/code)
**Canvas width:** 1080px
**Canvas height:** dynamic — trim to content (~650–900px typical)
**Render scale:** 3x DPR (~3240px wide export)
**Footer (both cards):**
- Left: `Aquib Rashid Shaikh` / `Senior Android Developer & Mobile Tech Lead`
- Right: `ANDROID / KOTLIN`
- Top-right pill: `Android` or `Kotlin`

### Layout structure (both card types)

```
[CATEGORY pill]                    [Lang pill]
HEADLINE
Subhead (accent color)
Tagline (muted, one line)

--- MAIN VISUAL ---
(Architecture: 3-node flow  OR  Code: side-by-side BEFORE/AFTER panels)

→ Takeaway 1
→ Takeaway 2
→ Takeaway 3

─────────────────────────────────
Aquib Rashid Shaikh          ANDROID / KOTLIN
Senior Android Developer...
```

### Template files
- `renderer/templates/process_infographic_dark.html.j2`
- `renderer/templates/process_infographic_light.html.j2`
- `renderer/templates/code_card_dark.html.j2`
- `renderer/templates/code_card_light.html.j2`

### Rendering rules (`renderer/render.py`)
- Initial viewport: 1080×900
- JS `drawInfographic()` sets page height = actual `.content` height (min 600, max 1500)
- **DO NOT** use `min-height: 1180px` on `.page`
- **DO NOT** use `Math.max(1180, contentHeight)` in JS
- Screenshot element: `.page` only

---

## Card Type A — Architecture Blueprint (v2 JSON schema)

**Template:** `process_infographic_*.html.j2`

```json
{
  "category": "OS INTERNALS",
  "headline": "16KB Page Size",
  "subhead": "Native Library Alignment",
  "tagline": "Unaligned ELF .so files crash at process startup on Android 15",
  "flow_nodes": [
    {"label": "App Startup", "detail": "native System.loadLibrary()", "highlight": false},
    {"label": "Dynamic Linker", "detail": "NDK LOAD segment 0x4000", "highlight": true},
    {"label": "Fatal Crash", "detail": "UnsatisfiedLinkError", "highlight": false}
  ],
  "takeaways": [
    "Compile NDK libs with -Wl,-z,max-page-size=16384",
    "Audit native .so LOAD segments via readelf before release",
    "Verify third-party SDKs ship 16KB-compatible native builds"
  ]
}
```

**Rules:**
- Exactly **3 flow_nodes** — middle node `highlight: true` (root cause)
- Node `detail` must contain real API/exception token (max ~35 chars)
- Exactly **3 takeaways**, 6–14 words, imperative, real APIs
- Flow arcs: INPUT→PROCESS→OUTPUT | PROBLEM→ROOT CAUSE→FIX | USER SPACE→KERNEL→EFFECT

**Lint:** `_lint_architecture_content()` in `scripts/infographic.py`

---

## Card Type B — Code Autopsy (v2 JSON schema)

**Template:** `code_card_*.html.j2`

```json
{
  "category": "COROUTINE AUTOPSY",
  "headline": "Stop Swallowing",
  "subhead": "CancellationException",
  "tagline": "Orphaned jobs survive after viewModelScope clears",
  "before_label": "AntiPattern.kt",
  "after_label": "ProfileViewModel.kt",
  "before_code": "viewModelScope.launch {\n    try {\n        repository.loadUserProfile()\n    } catch (e: Exception) {\n        Log.e(TAG, \"Failed\", e)\n    }\n}",
  "after_code": "viewModelScope.launch {\n    try {\n        repository.loadUserProfile()\n    } catch (e: CancellationException) {\n        throw e\n    } catch (e: Exception) {\n        _uiState.update { it.copy(error = e.toUserMessage()) }\n    }\n}",
  "takeaways": [
    "Rethrow CancellationException before handling domain failures",
    "Map repository errors with sealed Result at the data boundary",
    "Inspect runCatching failures before exposing UI error states"
  ]
}
```

**Rules:**
- Real compilable-looking Kotlin (6–16 lines per panel)
- BEFORE panel: red badge; AFTER panel: green badge
- Same scenario in both panels — only the fix differs
- `_prepare_code_card_for_render()` applies Kotlin syntax highlighting before render

**Lint:** `_lint_code_card_content()` in `scripts/infographic.py`

---

## Forbidden in v2 cards (never reintroduce)

- `legendBar`, `CONFIRMED AOSP SPEC`, `actionableBlock`
- 4 breakdown step cards with confidence labels
- Recruiter badge on the image itself
- Decorative icons ("Bluetooth icon", "network logo")
- Generic adjectives: seamless, robust, game changer, revolutionary
- Markdown `**bold**` or emoji in card content
- Fixed 1180px / 1410px canvas floors

---

## Archetype → template quick map

| Archetype | Default template | Card style |
|-----------|-------------------|------------|
| `CODE_AUTOPSY_TEARDOWN` | `code_card_dark.html.j2` | Before/After Kotlin |
| `CONTRARIAN_ARCHITECTURE_CALLOUT` | `code_card_dark.html.j2` | Before/After Kotlin |
| `OS_INTERNALS_DEEP_DIVE` | `process_infographic_dark.html.j2` | 3-node flow |
| `SCALE_INCIDENT_WAR_STORY` | `process_infographic_dark.html.j2` | 3-node flow |
| `HARDWARE_LOW_LEVEL_DEEP_DIVE` | `process_infographic_dark.html.j2` | 3-node flow |

Override with `--theme light` → `*_light.html.j2` variants.

---

## Quality checklist before marking done

- [ ] Post passes quality reviewer (or best of 3 attempts)
- [ ] Card JSON passes lint with zero violations
- [ ] PNG rendered with **no large bottom dead space** (content should end ~48px above canvas bottom)
- [ ] PNG saved as `renderer/output/scheduled_{date}_{time}.png`
- [ ] Entry added to `data/content_calendar.json` with `status: "scheduled"`
- [ ] `CONTENT_CALENDAR.md` synced
- [ ] `python -m unittest discover tests -q` passes
- [ ] If committing: include template/code changes + `git add -f` for PNG
