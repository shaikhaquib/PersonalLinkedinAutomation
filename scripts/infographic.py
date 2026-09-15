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
# Architecture Blueprint Card v2 — editorial 3-node flow diagram
# ─────────────────────────────────────────────────────────────────────────────
_ARCHITECTURE_CONTENT_PROMPT = """
Generate content for a clean editorial Architecture Blueprint card for a Senior Android Developer LinkedIn post.
The card shows a 3-step mechanism flow (INPUT → PROCESS → OUTPUT) with 3 takeaways.

Topic: {topic}

The LinkedIn post this card accompanies:
{post_text}

STRICT REQUIREMENTS:
- "category": 2-4 words ALL CAPS (e.g. "OS INTERNALS", "BLE GATT FLOW")
- "headline": 2-4 words punchy hook
- "subhead": 2-5 words naming the Android mechanism
- "tagline": one line under 14 words explaining the production risk
- "flow_nodes": exactly 3 objects with:
  * "label": 2-4 words Title Case (stage name)
  * "detail": real API token, exception, or system call (max 35 chars)
  * "highlight": true for the middle (root-cause) node only, false otherwise
- "takeaways": exactly 3 imperative bullets, 6-14 words each, naming real APIs

Pick the best 3-step arc:
- Mechanism: INPUT → PROCESS → OUTPUT
- Problem: PROBLEM → ROOT CAUSE → FIX
- OS internals: USER SPACE → KERNEL → OBSERVED EFFECT

BANNED: generic adjectives (seamless, robust, game changer), markdown, emoji.
Every node detail and takeaway must reference real Android/Kotlin APIs or exceptions.

Return ONLY valid JSON — no markdown:
{{
  "category": "OS INTERNALS",
  "headline": "16KB Page Size",
  "subhead": "Native Library Alignment",
  "tagline": "Unaligned ELF .so files crash at process startup on Android 15",
  "flow_nodes": [
    {{"label": "App Startup", "detail": "System.loadLibrary()", "highlight": false}},
    {{"label": "Dynamic Linker", "detail": "readelf ALIGN 0x4000", "highlight": true}},
    {{"label": "Fatal Crash", "detail": "UnsatisfiedLinkError", "highlight": false}}
  ],
  "takeaways": [
    "Compile NDK libs with -Wl,-z,max-page-size=16384",
    "Audit LOAD segment alignment via readelf on every .so",
    "Verify third-party SDKs ship 16KB-compatible native builds"
  ]
}}
""".strip()

# ─────────────────────────────────────────────────────────────────────────────
# Code Card v2 — editorial before/after layout with real Kotlin snippets
# ─────────────────────────────────────────────────────────────────────────────
_CODE_CARD_CONTENT_PROMPT = """
Generate content for a clean editorial Code Autopsy card for a Senior Android Developer LinkedIn post.
The card shows a real BEFORE (anti-pattern) vs AFTER (production fix) Kotlin code comparison.

Topic: {topic}

The LinkedIn post this card accompanies:
{post_text}

STRICT REQUIREMENTS:
- "category": 2-4 words ALL CAPS (e.g. "COROUTINE AUTOPSY", "COMPOSE TEARDOWN")
- "headline": 2-4 words, punchy hook (e.g. "Stop Swallowing")
- "subhead": 2-5 words naming the mechanism (e.g. "CancellationException")
- "tagline": one line under 14 words explaining the production risk
- "before_label": Kotlin filename for anti-pattern (e.g. "AntiPattern.kt")
- "after_label": Kotlin filename for fix (e.g. "ProfileViewModel.kt")
- "before_code": 6-14 lines of realistic Kotlin showing the anti-pattern. Must compile visually.
  Use viewModelScope, repository calls, or Compose APIs as appropriate. Include the bad catch block.
- "after_code": 6-16 lines of realistic Kotlin showing the production fix for the SAME scenario.
  Must include proper CancellationException handling when relevant.
- "takeaways": exactly 3 imperative bullets, 6-14 words each, naming real APIs or patterns

BANNED: generic adjectives (seamless, robust, game changer), markdown fences, emoji.
Every takeaway must name a real Android/Kotlin API, class, or exception.

Return ONLY valid JSON — no markdown:
{{
  "category": "COROUTINE AUTOPSY",
  "headline": "Stop Swallowing",
  "subhead": "CancellationException",
  "tagline": "Orphaned jobs survive after viewModelScope clears",
  "before_label": "AntiPattern.kt",
  "after_label": "ProfileViewModel.kt",
  "before_code": "viewModelScope.launch {{\\n    try {{\\n        repository.loadUserProfile()\\n    }} catch (e: Exception) {{\\n        Log.e(TAG, \\"Failed\\", e)\\n    }}\\n}}",
  "after_code": "viewModelScope.launch {{\\n    try {{\\n        repository.loadUserProfile()\\n    }} catch (e: CancellationException) {{\\n        throw e\\n    }} catch (e: Exception) {{\\n        _uiState.update {{ it.copy(error = e.toUserMessage()) }}\\n    }}\\n}}",
  "takeaways": [
    "Rethrow CancellationException before handling domain failures",
    "Map repository errors with sealed Result at the data boundary",
    "Inspect runCatching failures before exposing UI error states"
  ]
}}
""".strip()

_KOTLIN_KEYWORDS = {
    "fun", "val", "var", "try", "catch", "throw", "if", "else", "return", "class",
    "object", "interface", "when", "is", "as", "by", "in", "for", "while", "do",
    "suspend", "override", "private", "public", "internal", "protected", "open",
    "abstract", "sealed", "data", "enum", "import", "package", "true", "false",
    "null", "this", "super", "lazy", "init", "companion", "get", "set",
}

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
    Evaluates whether a bullet is a bare API symbol/token rather than a punchy explanatory clause.
    Requires word count >= 4 AND contains a verb, preposition, or causal/functional relationship.
    Returns (is_bare: bool, reason: str).
    """
    cleaned = text.strip()
    cleaned = re.sub(r'^[→\-\*•\s]+', '', cleaned).strip()
    words = cleaned.split()
    if len(words) < 4:
        return True, f"word count {len(words)} < 4 (must have an active verb and context)"
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

    # Check 8 (Phase 5.5a): Confidence Labeling
    valid_conf = {"confirmed", "analysis"}
    has_confirmed = False
    for i, step in enumerate(data.get("steps", [])):
        conf = str(step.get("confidence", "")).lower().strip()
        if conf and conf not in valid_conf:
            violations.append(f"INVALID_CONFIDENCE: steps[{i}].confidence is '{conf}' (must be 'confirmed' or 'analysis')")
        if conf == "confirmed":
            has_confirmed = True

    for i, stage in enumerate(data.get("stages", [])):
        conf = str(stage.get("confidence", "")).lower().strip()
        if conf and conf not in valid_conf:
            violations.append(f"INVALID_CONFIDENCE: stages[{i}].confidence is '{conf}' (must be 'confirmed' or 'analysis')")
        if conf == "confirmed":
            has_confirmed = True

    # Check 9 (Phase 5.5b): Functional diagrams only, no generic decorative icon descriptions
    banned_decor_icons = re.compile(r'\b(icon|logo|clipart|illustration|graphic|symbol)\b', re.I)
    for i, stage in enumerate(data.get("stages", [])):
        snip = stage.get("snippet", "")
        lbl = stage.get("label", "")
        if banned_decor_icons.search(snip) or banned_decor_icons.search(lbl):
            violations.append(
                f"DECORATIVE_ICON: stages[{i}] uses generic icon term ('{lbl}'/'{snip}'). "
                "Stage snippets must be real functional tokens, memory layouts, or mechanism states."
            )

    # Check 10 (Phase 5.5c): Actionable Closing Block
    ac = data.get("actionable_closing")
    if not ac or not isinstance(ac, dict):
        violations.append("MISSING_ACTIONABLE_CLOSING: 'actionable_closing' object with 'title' and 'points' is required")
    else:
        pts = ac.get("points", [])
        if not pts or len(pts) < 1:
            violations.append("EMPTY_ACTIONABLE_POINTS: 'actionable_closing.points' must contain 1-3 concrete audit steps")
        else:
            for idx, pt in enumerate(pts):
                words = pt.strip().split()
                if len(words) < 6:
                    violations.append(
                        f"SHORT_ACTIONABLE_POINT: actionable_closing.points[{idx}] has {len(words)} words "
                        "(must be >= 6 words with active verb and real API)"
                    )

            # Check for excessive paraphrasing between hook and actionable closing
            hook_text = data.get("hook", "").lower()
            ac_combined = " ".join(pts).lower()
            stops = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "it", "this", "that", "from", "your"}
            h_words = set(re.findall(r'\b[a-z]{4,}\b', hook_text)) - stops
            ac_words = set(re.findall(r'\b[a-z]{4,}\b', ac_combined)) - stops
            if h_words and ac_words:
                overlap = len(h_words & ac_words) / min(len(h_words), len(ac_words))
                if overlap > 0.75:
                    violations.append(
                        "PARAPHRASED_ACTIONABLE_CLOSING: Actionable closing points appear to just repeat the Key Insight summary. "
                        "Provide distinct, practical codebase audit steps."
                    )

    return violations


def _highlight_kotlin(code: str, highlight_substr: str = "", highlight_class: str = "") -> str:
    """Lightweight Kotlin syntax highlighter for card rendering."""
    import html as html_mod

    def _stash_segments(escaped: str, pattern: str, wrapper: str) -> tuple[str, list[str]]:
        tokens = []

        def _repl(match):
            tokens.append(wrapper.format(match.group(0)))
            return f"\x00T{len(tokens) - 1}\x00"

        escaped = re.sub(pattern, _repl, escaped)
        return escaped, tokens

    def _restore_segments(escaped: str, tokens: list[str]) -> str:
        for idx, token in enumerate(tokens):
            escaped = escaped.replace(f"\x00T{idx}\x00", token)
        return escaped

    def _apply_syntax(escaped: str) -> str:
        escaped = re.sub(r'(@[A-Za-z_][A-Za-z0-9_]*)', r'<span class="an">\1</span>', escaped)

        kw_pattern = "|".join(sorted(_KOTLIN_KEYWORDS, key=len, reverse=True))
        escaped = re.sub(
            rf'\b({kw_pattern})\b',
            r'<span class="kw">\1</span>',
            escaped,
        )

        escaped = re.sub(r'(:\s*)([A-Z][A-Za-z0-9_]*)', r'\1<span class="ty">\2</span>', escaped)
        escaped = re.sub(
            r'\bcatch\s*\(\s*e:\s*([A-Z][A-Za-z0-9_]*)',
            r'catch (e: <span class="ty">\1</span>',
            escaped,
        )
        escaped = re.sub(
            r'\b([a-z_][A-Za-z0-9_]*)\s*\(',
            r'<span class="fn">\1</span>(',
            escaped,
        )
        return escaped

    def _colorize_plain_line(line: str) -> str:
        escaped = html_mod.escape(line)

        if "//" in escaped:
            idx = escaped.index("//")
            comment = f'<span class="cm">{escaped[idx:]}</span>'
            escaped = escaped[:idx]
            escaped, tokens = _stash_segments(escaped, r'&quot;.*?&quot;', '<span class="str">{}</span>')
            escaped = _apply_syntax(escaped)
            escaped = _restore_segments(escaped, tokens)
            return escaped + comment

        escaped, tokens = _stash_segments(escaped, r'&quot;.*?&quot;', '<span class="str">{}</span>')
        escaped = _apply_syntax(escaped)
        return _restore_segments(escaped, tokens)

    lines = code.replace("\r\n", "\n").split("\n")
    out_lines = []
    for line in lines:
        colored = _colorize_plain_line(line)
        if highlight_substr and highlight_class and highlight_substr in line:
            colored = f'<span class="{highlight_class}">{colored}</span>'
        out_lines.append(colored)
    return "\n".join(out_lines)


def _clean_code_card_content(data: dict) -> dict:
    data["category"] = _clean_text(data.get("category", "")).upper() or "CODE AUTOPSY"
    data["headline"] = _clean_text(data.get("headline", ""))
    data["subhead"] = _clean_text(data.get("subhead", ""))
    data["tagline"] = _clean_text(data.get("tagline", ""))
    data["before_label"] = _clean_text(data.get("before_label", "")) or "AntiPattern.kt"
    data["after_label"] = _clean_text(data.get("after_label", "")) or "ProductionFix.kt"
    data["before_code"] = data.get("before_code", "").strip()
    data["after_code"] = data.get("after_code", "").strip()
    takeaways = [_clean_text(t) for t in data.get("takeaways", []) if _clean_text(t)]
    if len(takeaways) < 3:
        takeaways.extend([
            "Audit ViewModel coroutines for swallowed CancellationException paths",
            "Handle domain failures at the repository boundary with sealed Result",
            "Never map cancellation signals into UI error states",
        ])
    data["takeaways"] = takeaways[:3]
    return data


def _lint_code_card_content(data: dict) -> list[str]:
    violations = []
    required = [
        "category", "headline", "subhead", "tagline",
        "before_label", "after_label", "before_code", "after_code", "takeaways",
    ]
    for key in required:
        if not data.get(key):
            violations.append(f"MISSING_FIELD: '{key}' is required for code cards")

    full_text = " ".join([
        data.get("headline", ""),
        data.get("subhead", ""),
        data.get("tagline", ""),
        data.get("before_code", ""),
        data.get("after_code", ""),
        " ".join(data.get("takeaways", [])),
    ])
    banned_match = _BANNED_ABSTRACT.search(full_text)
    if banned_match:
        violations.append(f"BANNED_PHRASE: '{banned_match.group(0)}' found in content")

    if len(data.get("before_code", "").splitlines()) < 4:
        violations.append("SHORT_BEFORE_CODE: before_code must be at least 4 lines")
    if len(data.get("after_code", "").splitlines()) < 4:
        violations.append("SHORT_AFTER_CODE: after_code must be at least 4 lines")

    for i, tip in enumerate(data.get("takeaways", [])):
        if len(tip.split()) < 5:
            violations.append(f"SHORT_TAKEAWAY: takeaways[{i}] must be at least 5 words")
        if not _has_android_token(tip):
            violations.append(f"MISSING_API_TOKEN: takeaways[{i}] needs a real Android/Kotlin API reference")

    return violations


def _clean_architecture_content(data: dict) -> dict:
    data["category"] = _clean_text(data.get("category", "")).upper() or "ANDROID ARCHITECTURE"
    data["headline"] = _clean_text(data.get("headline", ""))
    data["subhead"] = _clean_text(data.get("subhead", ""))
    data["tagline"] = _clean_text(data.get("tagline", ""))

    nodes = []
    for node in data.get("flow_nodes", [])[:3]:
        nodes.append({
            "label": _clean_text(node.get("label", "")),
            "detail": _clean_text(node.get("detail", "")),
            "highlight": bool(node.get("highlight", False)),
        })
    while len(nodes) < 3:
        nodes.append({"label": "Stage", "detail": "Android API call", "highlight": False})
    if not any(n["highlight"] for n in nodes):
        nodes[1]["highlight"] = True
    data["flow_nodes"] = nodes

    takeaways = [_clean_text(t) for t in data.get("takeaways", []) if _clean_text(t)]
    if len(takeaways) < 3:
        takeaways.extend([
            "Audit critical Android execution paths for this failure mode",
            "Validate native dependencies against current AOSP linker requirements",
            "Refactor module boundaries before shipping production hotfixes",
        ])
    data["takeaways"] = takeaways[:3]
    return data


def _lint_architecture_content(data: dict) -> list[str]:
    violations = []
    required = ["category", "headline", "subhead", "tagline", "flow_nodes", "takeaways"]
    for key in required:
        if not data.get(key):
            violations.append(f"MISSING_FIELD: '{key}' is required for architecture cards")

    if len(data.get("flow_nodes", [])) != 3:
        violations.append("FLOW_NODE_COUNT: flow_nodes must contain exactly 3 items")

    full_text = " ".join([
        data.get("headline", ""),
        data.get("subhead", ""),
        data.get("tagline", ""),
        " ".join(n.get("detail", "") for n in data.get("flow_nodes", [])),
        " ".join(data.get("takeaways", [])),
    ])
    banned_match = _BANNED_ABSTRACT.search(full_text)
    if banned_match:
        violations.append(f"BANNED_PHRASE: '{banned_match.group(0)}' found in content")

    for i, node in enumerate(data.get("flow_nodes", [])):
        if len(node.get("detail", "")) < 3:
            violations.append(f"EMPTY_NODE_DETAIL: flow_nodes[{i}].detail is too short")
        if not _has_android_token(node.get("detail", "")):
            violations.append(f"MISSING_API_TOKEN: flow_nodes[{i}].detail needs a real Android/Kotlin API reference")

    for i, tip in enumerate(data.get("takeaways", [])):
        if len(tip.split()) < 5:
            violations.append(f"SHORT_TAKEAWAY: takeaways[{i}] must be at least 5 words")
        if not _has_android_token(tip):
            violations.append(f"MISSING_API_TOKEN: takeaways[{i}] needs a real Android/Kotlin API reference")

    return violations


def _prepare_code_card_for_render(data: dict) -> dict:
    data = _clean_code_card_content(data)
    data["before_code_html"] = _highlight_kotlin(
        data["before_code"], "catch (e: Exception)", "hl-bad"
    )
    data["after_code_html"] = _highlight_kotlin(
        data["after_code"], "CancellationException", "hl-good"
    )
    return data


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
    data["title_line1"] = _clean_text(data.get("title_line1", ""))
    data["title_line2"] = _clean_text(data.get("title_line2", ""))
    data["tagline"] = _clean_text(data.get("tagline", ""))
    data["hook"] = _clean_text(data.get("hook", ""))
    data["section_label"] = _clean_text(data.get("section_label", "")).upper() or "ANDROID ARCHITECTURE"

    # Phase 5.5a: Confidence sanitization
    for stage in data.get("stages", []):
        stage["label"] = _clean_text(stage.get("label", ""))
        stage["snippet"] = _clean_text(stage.get("snippet", ""))
        conf = str(stage.get("confidence", "confirmed")).lower().strip()
        stage["confidence"] = conf if conf in ("confirmed", "analysis") else "confirmed"

    for i, step in enumerate(data.get("steps", [])):
        step["label"] = _clean_text(step.get("label", ""))
        step["points"] = [_clean_text(p) for p in step.get("points", [])]
        conf = str(step.get("confidence", "")).lower().strip()
        if conf not in ("confirmed", "analysis"):
            conf = "analysis" if i == len(data.get("steps", [])) - 1 else "confirmed"
        step["confidence"] = conf

    data["flow_a_items"] = [_clean_text(i) for i in data.get("flow_a_items", [])]
    data["flow_b_items"] = [_clean_text(i) for i in data.get("flow_b_items", [])]

    # Phase 5.5c: Actionable closing block sanitization
    ac = data.get("actionable_closing", {})
    if isinstance(ac, dict):
        ac_title = _clean_text(ac.get("title", "")) or "WHAT THIS MEANS FOR YOUR CODEBASE"
        ac_pts = [_clean_text(p) for p in ac.get("points", []) if _clean_text(p)]
        if not ac_pts:
            ac_pts = [
                "Audit your codebase for this pattern across critical UI and background paths.",
                "Enforce strict boundary separation between data mapping and presentation logic."
            ]
        data["actionable_closing"] = {"title": ac_title, "points": ac_pts}
    elif isinstance(ac, list):
        data["actionable_closing"] = {
            "title": "WHAT THIS MEANS FOR YOUR CODEBASE",
            "points": [_clean_text(p) for p in ac if _clean_text(p)]
        }
    else:
        data["actionable_closing"] = {
            "title": "WHAT THIS MEANS FOR YOUR CODEBASE",
            "points": [
                "Audit your codebase for this pattern across critical UI and background paths.",
                "Enforce strict boundary separation between data mapping and presentation logic."
            ]
        }

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
        required_keys = [
            "category", "headline", "subhead", "tagline",
            "before_label", "after_label", "before_code", "after_code", "takeaways",
        ]
        lint_fn = _lint_code_card_content
        clean_fn = _clean_code_card_content
    else:
        prompt = _ARCHITECTURE_CONTENT_PROMPT.format(topic=topic, post_text=post_text[:2500])
        required_keys = ["category", "headline", "subhead", "tagline", "flow_nodes", "takeaways"]
        lint_fn = _lint_architecture_content
        clean_fn = _clean_architecture_content

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

        if "code_card" in template:
            if not all(k in data for k in required_keys):
                print(f"  [infographic] Attempt {attempt + 1}: Missing required code card fields")
                continue
            if len(data.get("takeaways", [])) < 3:
                print(f"  [infographic] Attempt {attempt + 1}: takeaways must contain 3 items")
                continue
        elif not all(k in data for k in required_keys):
            print(f"  [infographic] Attempt {attempt + 1}: Missing required architecture card fields")
            continue
        elif len(data.get("flow_nodes", [])) != 3:
            print(f"  [infographic] Attempt {attempt + 1}: flow_nodes must contain 3 items")
            continue
        elif len(data.get("takeaways", [])) < 3:
            print(f"  [infographic] Attempt {attempt + 1}: takeaways must contain 3 items")
            continue

        data = clean_fn(data)

        violations = lint_fn(data)
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
        return clean_fn(json.loads(raw))
    except Exception:
        raise RuntimeError(f"Failed to generate valid infographic JSON after 3 attempts. Last violations: {last_violations}")


def render_infographic(content: dict, out_path: str, template: str = "process_infographic_dark.html.j2") -> str:
    """Render the content dict to a PNG using Playwright. Returns PNG path."""
    import sys
    root = pathlib.Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from renderer.render import render
    if "code_card" in template:
        content = _prepare_code_card_for_render(content)
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
