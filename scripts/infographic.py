"""
Infographic generator for LinkedIn posts.

Pipeline:
  generate_process_content()  → Gemini → structured content dict
  render_infographic()        → Playwright → PNG
  upload_to_linkedin()        → LinkedIn media API → asset URN

Two templates are supported:
  process_infographic_dark.html.j2  — Architecture Blueprint Card
  code_card_dark.html.j2            — Syntax-Highlighted Code Card (before/after)
"""

import os
import re
import json
import pathlib
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 & 4.6: ARCHITECTURE BLUEPRINT CARD CONTENT PROMPT
# Every field MUST name a real Android API, class, exception, or mechanism.
# Abstract adjectives (deterministic, seamless, atomic, robust, erratic) are
# banned unless immediately followed by the named mechanism causing that property.
# BARE API NAME-DROPPING IS STRICTLY FORBIDDEN:
# Every bullet in steps[].points MUST be a complete clause (min 6 words with verb).
# ─────────────────────────────────────────────────────────────────────────────
_ARCHITECTURE_CONTENT_PROMPT = """
Generate content for a dark-theme Android Architecture Blueprint Card infographic.
This card visualises a technical mechanism, state flow, or OS-internals deep dive
from the post below. The audience is Senior Android Developers, Tech Leads, and EMs.

Topic: {topic}

The LinkedIn post this card accompanies (use the SAME narrative — same APIs, same claims):
{post_text}

STRICT FIELD REQUIREMENTS:
- Every stage snippet MUST be a real code token, Android API call, exception name, or system state
  (e.g. "gatt.writeCharacteristic()", "LMK SIGKILL", "StateFlow.collect", "MTU: 517 bytes").
- Every step label MUST name a real Android/Kotlin class, method, or architectural concept.
- BARE API NAME-DROPPING IS STRICTLY FORBIDDEN (Phase 4.6):
  Every single bullet point in steps[].points MUST be a complete, explanatory clause of at least 6 words,
  containing BOTH a real Android API/class/exception token AND an active verb or causal relationship.
  Explain HOW or WHY the mechanism works, what calls what, or what constraint is enforced.
  NEVER output standalone class names, dotted methods, or short symbol lists without sentence structure.
  * REJECTED (bare symbols / incomplete clauses):
    - "kotlinx.coroutines.sync.Mutex"
    - "BluetoothGatt.writeCharacteristic()"
    - "BluetoothGattCallback.onCharacteristicWrite()"
  * ACCEPTED (complete explanatory clauses with min 6 words and verb):
    - "Mutex serializes outgoing writeCharacteristic calls to prevent ATT request collisions"
    - "BluetoothGattCallback onCharacteristicWrite signals the next queued packet to proceed"
    - "Requesting an MTU of 517 bytes reduces payload chunking across ATT transfer packets"
- BANNED abstract adjectives (unless paired with the mechanism name):
  deterministic, seamless, atomic, robust, erratic, reliable, scalable, efficient,
  performant, elegant, comprehensive, revolutionary, game changer, unlocks.
- All flow_a_items and flow_b_items must be real API tokens or short mechanism names,
  NOT generic action verbs ("check", "process", "handle", "update").

Identify the 3-part arc that best matches the post:
- Mechanism post:    INPUT → PROCESS → OUTPUT (e.g. BLE command → GATT queue → ACK)
- Problem/solution:  PROBLEM STATE → ROOT CAUSE → PRODUCTION FIX
- OS internals:      USER SPACE → KERNEL/SYSTEM → OBSERVED EFFECT

Return ONLY valid JSON — no markdown, no explanation:
{{
  "title_line1": "Short punchy hook phrase (3-5 words), Title Case",
  "title_line2": "Payoff line (3-5 words), Title Case — names the Android mechanism",
  "tagline": "One sharp setup line under 10 words — names a real API or exception",
  "section_label": "2-4 words all-caps e.g. 'BLE GATT INTERNALS' or 'COMPOSE STATE FLOW'",
  "hook": "One quotable takeaway under 20 words — must name a real class or API",
  "stages": [
    {{"label": "2-3 words Title Case", "snippet": "real code token max 25 chars"}},
    {{"label": "2-3 words Title Case", "snippet": "real code token max 25 chars"}},
    {{"label": "2-3 words Title Case", "snippet": "real code token max 25 chars"}}
  ],
  "steps": [
    {{"label": "Real Android Class or Pattern Name", "points": ["Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words"]}},
    {{"label": "Real Android Class or Pattern Name", "points": ["Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words"]}},
    {{"label": "Real Android Class or Pattern Name", "points": ["Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words"]}},
    {{"label": "Real Android Class or Pattern Name", "points": ["Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words", "Complete clause naming real API and active verb min 6 words"]}}
  ],
  "flow_a_items": ["RealClass.method()", "SystemCall", "StateToken", "APIConstant", "OutputState"],
  "flow_b_items": ["SDK.class", "Mechanism", "Outcome", "Fix"]
}}
""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 & 4.6: SYNTAX-HIGHLIGHTED CODE CARD CONTENT PROMPT
# Generates before/after Kotlin code comparison data.
# ─────────────────────────────────────────────────────────────────────────────
_CODE_CARD_CONTENT_PROMPT = """
Generate content for a Syntax-Highlighted Code Card infographic (Carbon/Ray.so style).
This card shows a BEFORE (anti-pattern) vs. AFTER (production fix) Kotlin code comparison
for a Senior Android Developer's LinkedIn post.

Topic: {topic}

The LinkedIn post this card accompanies:
{post_text}

STRICT REQUIREMENTS:
- steps[0] is the ANTI-PATTERN: label = the faulty function/class name, points = [badParamType, whyItBreaks, badCallSite]
- steps[1] is the PRODUCTION FIX: label = the corrected function/class name, points = [correctParamType, whatChanged, cleanCallSite]
- steps[2] is WHY IT BREAKS: label = names the specific Android failure mechanism (e.g. "Recomposition Loop", "Binder IPC Overflow"), points = 3 complete explanatory clauses (min 6 words with active verb) each naming a real API/system/exception
- steps[3] is THE FIX RULE: label = the architectural rule of thumb (short, imperative), points = 3 complete explanatory clauses (min 6 words with active verb) naming real Kotlin/Android patterns
- BARE API NAME-DROPPING IS STRICTLY FORBIDDEN (Phase 4.6):
  Every point in steps[2].points (Why It Breaks) and steps[3].points (The Fix) MUST be a complete explanatory clause with at least 6 words and an active verb. Never output bare class names or symbols without sentence structure.
- flow_a_items = 3-5 short one-liners naming real APIs in the solution path
- flow_b_items = 3-4 words forming the rule of thumb (e.g. ["Hoist State", "Pass Lambdas", "Stay Stable"])
- hook = one sharp takeaway sentence under 20 words naming the real Android class or mechanism

BANNED abstract adjectives: deterministic, seamless, atomic, robust, erratic.
BANNED generic phrases: "game changer", "revolutionary", "unlock", "delve", "Three weeks ago".
Every point bullet in steps[2] and steps[3] MUST include at least one of: real class name, Kotlin API method, Android SDK constant, or named exception.

Return ONLY valid JSON — no markdown:
{{
  "title_line1": "Short punchy anti-pattern hook (3-5 words) Title Case",
  "title_line2": "The production fix revelation (3-5 words) Title Case",
  "tagline": "One line setup naming the real Android API or pattern under 10 words",
  "section_label": "2-4 words ALL CAPS e.g. 'CODE AUTOPSY' or 'COMPOSE TEARDOWN'",
  "hook": "One takeaway sentence under 20 words naming the real fix mechanism",
  "stages": [
    {{"label": "Anti-Pattern Name", "snippet": "BadCall.invoke()"}},
    {{"label": "Root Cause", "snippet": "GATT_STATUS 133"}},
    {{"label": "Production Fix", "snippet": "Mutex.withLock {{}}"}}
  ],
  "steps": [
    {{"label": "anti_pattern_function_name", "points": ["BadParamType", "// reason it breaks", "badCallSite.call()"]}},
    {{"label": "clean_function_name", "points": ["ImmutableState", "() -> Unit", "// Preview and test-safe"]}},
    {{"label": "Why This Breaks at Scale", "points": ["RealException thrown when buffer exceeds memory threshold", "SystemBehavior triggering unexpected recomposition loop", "Observable symptom causing frame drops in production"]}},
    {{"label": "The Production Rule", "points": ["Kotlin pattern applied to preserve state across recreations", "SavedStateHandle used to persist arguments across process death", "Produces stable lambdas to avoid unnecessary Compose invalidations"]}}
  ],
  "flow_a_items": ["Step1.api()", "Step2.call()", "Step3.result", "OutputState"],
  "flow_b_items": ["Short", "Rule", "Of Thumb"]
}}
""".strip()

_SYSTEM = "You generate structured JSON content for technical Android developer infographics. Return only valid JSON, no extra text, no markdown code fences."

# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Content lint — validates fields for real Android API tokens
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that must match at least one token per bullet point
_ANDROID_TOKEN_PATTERNS = [
    re.compile(r'\b[A-Z][a-zA-Z]*Exception\b'),              # e.g. TransactionTooLargeException
    re.compile(r'\b[A-Z][a-zA-Z]*Error\b'),                  # e.g. OutOfMemoryError
    re.compile(r'\b(StateFlow|SharedFlow|ViewModel|Composable|Coroutine|Binder|Bundle|Intent|WindowSizeClass|FusedLocation|BluetoothGatt|ExoPlayer|Media3|LoadControl|DefaultLoadControl|TrackSelector|DefaultTrackSelector|MediaItem|DataStore|SavedStateHandle|WorkManager|CoroutineScope|Mutex|Channel|Room|Hilt|Dagger|Dispatchers|rememberSaveable|derivedStateOf|LazyColumn|HiltViewModel|NavController|ActivityResultLauncher|BroadcastReceiver|JobScheduler|AlarmManager|BluetoothManager|BluetoothAdapter|Activity|Fragment|Service|Application|Process|Parcelable|Parcel|Serializable|AIDL|IBinder|IInterface|RemoteService|RemoteException)\b', re.I),
    re.compile(r'\b(Compose|Composable|recomposition|recompose|SnapshotStateObserver|Immutable|Stable|remember|rememberSaveable|derivedStateOf|collectAsState|collectAsStateWithLifecycle|produceState|snapshotFlow|Modifier|Surface|Scaffold|LazyColumn|LazyRow|UiState|State)\b', re.I),
    re.compile(r'\bgatt\s*\.'),                               # gatt.write*, gatt.read*, gatt.connect()
    re.compile(r'\b(oom_adj|SIGKILL|MTU|ANR|LMK|IPC|NDK|AOSP|ART|JNI|VSYNC|Choreographer|binder|Fluoride|BTA|HCI|BLE|GATT|ATT|continuation|withTimeoutOrNull|withTimeout|callback|radio|firmware|hardware|protocol|socket|peripheral|central|ACK|transaction|database|repository|cache|heap|memory|buffer|native|stack|connection)\b', re.I),
    re.compile(r'\b(BluetoothGattCallback|BluetoothDevice|BluetoothSocket|characteristic|descriptor|payload|packet|buffer|queue|queueing|recomposition|recompose|stability|immutability)\b', re.I),
    re.compile(r'\b(collect|emit|launch|withLock|connectGatt|writeCharacteristic|readCharacteristic|registerUpload|putExtra|getParcelable|observe|observeAsState|collectAsStateWithLifecycle|requestMtu|onMtuChanged|onCharacteristicWrite|onCharacteristicRead|onConnectionStateChange|withContext|suspendCoroutine|suspendCancellableCoroutine|cancel|close|build|invoke|send|receive)\b'),
    re.compile(r'\b(status|state|code|score|threshold|bytes|ms|seconds?|error)\s*[:=\s]\s*\d+', re.I),  # e.g. "status: 133" or "status 133"
    re.compile(r'\b[A-Z][a-zA-Z]+\.(GATT_|STATE_|ACTION_|FLAG_|IMPORTANCE_|TYPE_|MODE_|FORMAT_|BIND_|PERMISSION_)'),  # SDK constants
    re.compile(r'(launch\s*\{|withContext\s*\(|runBlocking\s*\{|async\s*\{|flow\s*\{|coroutineScope\s*\{|viewModelScope|lifecycleScope|rememberCoroutineScope|suspend\s+fun)'),  # Kotlin coroutine builders
    re.compile(r'\b(process death|activity recreation|configuration change|foreground service|background restriction|doze mode|app standby|process death recovery)\b', re.I),  # Android lifecycle concepts
    re.compile(r'\b(onCharacteristicWrite|onCharacteristicRead|onCharacteristicChanged|onMtuChanged|onConnectionStateChange|onDescriptorWrite|onServicesDiscovered)\b'),  # GATT callback names
    re.compile(r'\b(suspendCoroutine|suspendCancellableCoroutine|callbackFlow|channelFlow|produceState|snapshotFlow)\b'),  # Kotlin coroutine primitives
    re.compile(r'\b(STATUS_\d+|GATT_\w+|STATE_\w+|ACTION_\w+|TYPE_\w+|MODE_\w+|FORMAT_\w+|FLAG_\w+)\b'),  # SDK constant names
    re.compile(r'\d+ms\s+(grace|delay|window|timeout|backoff)\b', re.I),  # timing constraints
]

# Abstract-only adjectives (banned per Blueprint §4 / D5 fix)
_BANNED_ABSTRACT = re.compile(
    r'\b(deterministic|seamless|atomic(?! +queue| +operation| +reference)|robust|erratic|'
    r'game[- ]?changer|revolutionary|unlock(?! +the)?|delve|testament|'
    r'three weeks ago|two weeks ago|six weeks ago|days ago,? i believed|'
    r'on tuesday,? i ran|in today\'?s fast[- ]paced)\b',
    re.IGNORECASE
)

# Markdown formatting in PROSE (not code): **bold** or _italic_ — catches only letter-based bold/italic, not Kotlin {} or ()
_MARKDOWN_SYMBOLS = re.compile(r'(?<![a-zA-Z0-9_\{\(])([*]{1,3}|_{1,2})(?=[a-zA-Z]).+?\1')

# Phase 4.6: Verbs, causal relationships, and action terms for complete clauses
_VERB_CAUSAL_PATTERN = re.compile(
    r'\b('
    r'[a-zA-Z]{3,}(?:s|ed|ing)|'  # regular verbs: calls, called, calling, expands, optimizes, governs, skips
    r'must|should|can|could|will|would|is|are|was|were|has|have|had|be|been|'
    r'make|makes|made|take|takes|took|get|gets|got|set|sets|keep|keeps|kept|'
    r'run|runs|ran|hold|holds|held|send|sends|sent|write|writes|wrote|'
    r'lead|leads|led|throw|throws|threw|drop|drops|dropped|break|breaks|broke|'
    r'via|before|after|when|while|during|because|to\s+[a-z]+'
    r')\b',
    re.IGNORECASE
)


def _has_android_token(text: str) -> bool:
    """Returns True if text contains at least one real Android/Kotlin API reference."""
    return any(p.search(text) for p in _ANDROID_TOKEN_PATTERNS)


def _is_bare_api_bullet(text: str) -> tuple[bool, str]:
    """
    Evaluates whether a bullet is a bare API symbol/token rather than a complete explanatory clause.
    Per Phase 4.6: Word count >= 6 AND contains a verb or causal/functional relationship.
    Returns (is_bare: bool, reason: str).
    """
    cleaned = text.strip()
    cleaned = re.sub(r'^[→\-\*•\s]+', '', cleaned).strip()
    words = cleaned.split()
    if len(words) < 6:
        return True, f"word count {len(words)} < 6 (must be a full clause)"
    if not _VERB_CAUSAL_PATTERN.search(cleaned):
        return True, "lacks an active verb or causal relationship"
    return False, ""


def _lint_content(data: dict, template: str = "process_infographic_dark.html.j2") -> list[str]:
    """
    Runs Phase 4 & 4.6 lint checks on a generated content dict.
    Returns a list of violation strings (empty = passed).
    """
    violations = []
    all_text_fields = []

    # Collect all text for banned-phrase scan
    for key in ("title_line1", "title_line2", "tagline", "hook", "section_label"):
        all_text_fields.append(data.get(key, ""))

    for stage in data.get("stages", []):
        all_text_fields.extend([stage.get("label", ""), stage.get("snippet", "")])

    for step in data.get("steps", []):
        all_text_fields.append(step.get("label", ""))
        for pt in step.get("points", []):
            all_text_fields.append(pt)

    all_text_fields.extend(data.get("flow_a_items", []))
    all_text_fields.extend(data.get("flow_b_items", []))

    full_text = " ".join(all_text_fields)

    # Check 1: No banned abstract phrases
    banned_match = _BANNED_ABSTRACT.search(full_text)
    if banned_match:
        violations.append(f"BANNED_PHRASE: '{banned_match.group(0)}' found in content")

    # Check 2: No markdown asterisks/underscores
    if _MARKDOWN_SYMBOLS.search(full_text):
        violations.append("MARKDOWN_SYMBOLS: asterisks or underscores found in content fields")

    # Check 3: Every step bullet must have an Android API token
    # In Architecture Card: all 4 steps are bullet cards
    # In Code Card: steps[2] (Why It Breaks) and steps[3] (The Fix) are bullet cards
    steps_to_check_tokens = range(4) if template == "process_infographic_dark.html.j2" else [2, 3]
    for i in steps_to_check_tokens:
        if i < len(data.get("steps", [])):
            step = data["steps"][i]
            for j, pt in enumerate(step.get("points", [])):
                if not _has_android_token(pt):
                    violations.append(f"MISSING_API_TOKEN: steps[{i}].points[{j}] = '{pt[:60]}' — no real Android/Kotlin API name found")

    # Check 4: Stage snippets must look like real code/state tokens
    for i, stage in enumerate(data.get("stages", [])):
        snippet = stage.get("snippet", "")
        if not snippet or len(snippet) < 3:
            violations.append(f"EMPTY_SNIPPET: stages[{i}].snippet is empty or too short")

    # Check 5 (Phase 4.5): No confusing status 133 with GATT_FAILURE
    if re.search(r'GATT_FAILURE\s*[:=\s]*133|133\s*[:=\s]*GATT_FAILURE', full_text, re.I):
        violations.append("FACTUAL_ERROR: BluetoothGatt.GATT_FAILURE is integer 257. Status 133 is undocumented; do not label status 133 as GATT_FAILURE")

    # Check 6 (Phase 4.5): No attributing ATT serialization to HCI
    if re.search(r'HCI.*(?:one|single|active\s+GATT|serializ)', full_text, re.I):
        violations.append("FACTUAL_ERROR: The one-outstanding-request constraint belongs to ATT (Attribute Protocol), not HCI")

    # Check 7 (Phase 4.6): Bare API Name-Dropping Rule
    # In Architecture Card: all 4 steps are bullet cards — all bullets must be complete clauses
    # In Code Card: steps[2] (Why It Breaks) and steps[3] (The Fix) are bullet cards
    steps_to_check = range(4) if "process_infographic" in template else [2, 3]
    for i in steps_to_check:
        if i < len(data.get("steps", [])):
            step = data["steps"][i]
            for j, pt in enumerate(step.get("points", [])):
                is_bare, reason = _is_bare_api_bullet(pt)
                if is_bare:
                    violations.append(
                        f"BARE_API_BULLET: steps[{i}].points[{j}] = '{pt}' ({reason}). "
                        "Every bullet must be a complete explanatory clause with >= 6 words and an active verb."
                    )

    return violations


def _clean_text(s: str) -> str:
    """Strip stray markdown/comment markers and leading arrows the model sometimes leaks."""
    s = s.strip()
    s = re.sub(r'^(#+|//+)\s*', '', s)
    s = re.sub(r'^[→\-\*•\s]+', '', s)
    s = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', s)
    s = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', s)
    s = s.replace('`', '')
    return s.strip()


def _clean_content(data: dict) -> dict:
    data["title_line1"] = _clean_text(data["title_line1"])
    data["title_line2"] = _clean_text(data["title_line2"])
    data["tagline"] = _clean_text(data["tagline"])
    data["hook"] = _clean_text(data["hook"])
    data["section_label"] = _clean_text(data.get("section_label", "")).upper() or "ANDROID ARCHITECTURE"
    for stage in data["stages"]:
        stage["label"] = _clean_text(stage["label"])
        stage["snippet"] = _clean_text(stage["snippet"])
    for step in data["steps"]:
        step["label"] = _clean_text(step["label"])
        step["points"] = [_clean_text(p) for p in step["points"]]
    data["flow_a_items"] = [_clean_text(i) for i in data["flow_a_items"]]
    data["flow_b_items"] = [_clean_text(i) for i in data["flow_b_items"]]
    return data


def generate_process_content(topic: str, post_text: str, generate_text_fn,
                             template: str = "process_infographic_dark.html.j2") -> dict:
    """
    Call the LLM to produce the content dict for the chosen template type.
    Phase 4: Validates every field against Android API token requirements.
    Retries up to 3 times on lint violations.
    """
    if "code_card" in template:
        prompt = _CODE_CARD_CONTENT_PROMPT.format(topic=topic, post_text=post_text[:2500])
    else:
        prompt = _ARCHITECTURE_CONTENT_PROMPT.format(topic=topic, post_text=post_text[:2500])

    required_keys = ["title_line1", "title_line2", "tagline", "hook",
                     "stages", "steps", "flow_a_items", "flow_b_items"]

    last_violations = []
    for attempt in range(3):
        raw = generate_text_fn(prompt, _SYSTEM)
        raw = raw.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  [infographic] Attempt {attempt + 1}: JSON parse error: {e}")
            continue

        if not (all(k in data for k in required_keys)
                and len(data.get("stages", [])) == 3
                and len(data.get("steps", [])) == 4):
            print(f"  [infographic] Attempt {attempt + 1}: Missing required fields or wrong array lengths")
            continue

        data = _clean_content(data)

        # Phase 4 & 4.6 lint
        violations = _lint_content(data, template=template)
        if violations:
            last_violations = violations
            print(f"  [infographic] Attempt {attempt + 1}: Lint violations:")
            for v in violations:
                print(f"    ✗ {v}")
            # Inject violation feedback into next prompt for targeted regeneration
            violation_summary = "\n".join(f"- {v}" for v in violations[:5])
            prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED THESE CHECKS — fix them:\n{violation_summary}"
            continue

        print(f"  [infographic] Attempt {attempt + 1}: Lint PASSED — content is valid")
        return data

    # If all attempts failed lint, log violations and return best-effort data
    print(f"  [infographic] WARNING: Content lint failed after 3 attempts. Violations: {last_violations}")
    print(f"  [infographic] Returning best-effort content (may have abstract fields).")
    try:
        return _clean_content(json.loads(raw))
    except Exception:
        raise RuntimeError(f"Failed to generate valid infographic JSON after 3 attempts. Last violations: {last_violations}")


def render_infographic(content: dict, out_path: str, template: str = "process_infographic_dark.html.j2") -> str:
    """Render the content dict to a PNG using Playwright. Returns PNG path."""
    import sys
    root = pathlib.Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from renderer.render import render
    return render(content, out_path, template=template)


def upload_to_linkedin(png_path: str, access_token: str, person_id: str) -> str:
    """
    Upload PNG to LinkedIn via the media upload API.
    Returns the asset URN to embed in the ugcPost.
    """
    headers_json = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # Step 1 — register upload
    reg = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers_json,
        json={
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner":   f"urn:li:person:{person_id}",
                "serviceRelationships": [{
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }],
            }
        },
        timeout=20,
    )
    reg.raise_for_status()
    val = reg.json()["value"]
    upload_url = val["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = val["asset"]

    # Step 2 — upload image bytes
    with open(png_path, "rb") as f:
        img_bytes = f.read()

    put = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "image/png"},
        data=img_bytes,
        timeout=60,
    )
    put.raise_for_status()

    print(f"  [infographic] Uploaded → {asset_urn}")
    return asset_urn
