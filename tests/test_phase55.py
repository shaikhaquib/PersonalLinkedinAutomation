"""
Tests for Phase 5.5: Confidence Labeling, Functional Mockups, and Actionable Closing.
"""

import os
import re
import unittest
from jinja2 import Environment, FileSystemLoader

from scripts.infographic import _lint_content, _clean_content


class TestPhase55ContentLinting(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            "title_line1": "BINDER TRANSACTION",
            "title_line2": "BUFFER OVERFLOW",
            "tagline": "How the 1MB shared Binder buffer triggers silent app crashes",
            "section_label": "IPC INTERNALS",
            "stages": [
                {"label": "App Process", "snippet": "Parcel.obtain() writes payload", "confidence": "confirmed"},
                {"label": "Binder Kernel", "snippet": "binder_alloc allocates in 1MB buffer", "confidence": "confirmed"},
                {"label": "System Server", "snippet": "TransactionTooLargeException thrown on limit", "confidence": "confirmed"}
            ],
            "steps": [
                {
                    "label": "Process Memory Limit",
                    "confidence": "confirmed",
                    "points": [
                        "Binder driver allocates a fixed 1MB buffer shared across all ongoing transactions",
                        "Exceeding this threshold throws a fatal TransactionTooLargeException immediately",
                        "Async transactions over IBinder are capped at an even stricter 512KB limit"
                    ]
                },
                {
                    "label": "State Persistence",
                    "confidence": "confirmed",
                    "points": [
                        "SavedStateHandle writes Parcelable data into the Activity restoration bundle",
                        "Heavy bitmaps or large lists silently exhaust the transaction buffer",
                        "System fails during onSaveInstanceState before the process dies"
                    ]
                },
                {
                    "label": "Buffer Allocation",
                    "confidence": "confirmed",
                    "points": [
                        "Memory is allocated from a single shared ashmem region per process",
                        "Concurrent IPC calls compete for the exact same 1MB address space",
                        "Fragmented buffer blocks cause allocation failures even with free space"
                    ]
                },
                {
                    "label": "Architectural Mitigation",
                    "confidence": "analysis",
                    "points": [
                        "Pass database primary keys or content URIs instead of whole data models",
                        "Offload large payloads to Room database with reactive StateFlow observers",
                        "Use Jetpack Paging3 to load items incrementally across the IPC boundary"
                    ]
                }
            ],
            "flow_a_items": ["Parcel.obtain()", "binder_alloc", "TransactionTooLargeException"],
            "flow_b_items": ["Keep Bundles Small", "Store In SQLite", "Pass Keys Only"],
            "hook": "The 1MB Binder buffer is shared across your entire app process, not per transaction.",
            "actionable_closing": {
                "title": "WHAT THIS MEANS FOR YOUR CODEBASE",
                "points": [
                    "Audit every SavedStateHandle and Intent bundle in your navigation graphs for payloads > 100KB.",
                    "Replace serialized entity objects with Room database IDs and reactive Room Flow queries.",
                    "Verify background Worker IPC payloads do not exceed 512KB async binder boundaries."
                ]
            }
        }

    def test_valid_data_passes_all_checks(self):
        violations = _lint_content(self.valid_data)
        self.assertEqual(violations, [], f"Expected zero violations, got: {violations}")

    def test_confidence_validation(self):
        # Invalid confidence string
        bad_data = dict(self.valid_data)
        bad_data["steps"] = [dict(s) for s in self.valid_data["steps"]]
        bad_data["steps"][0]["confidence"] = "unverified_guess"
        violations = _lint_content(bad_data)
        self.assertTrue(any("INVALID_CONFIDENCE" in v for v in violations))

    def test_banned_decorative_icons(self):
        # Stage snippet using generic decorative words
        bad_data = dict(self.valid_data)
        bad_data["stages"] = [dict(s) for s in self.valid_data["stages"]]
        bad_data["stages"][0]["snippet"] = "Bluetooth icon next to service"
        violations = _lint_content(bad_data)
        self.assertTrue(any("DECORATIVE_ICON" in v for v in violations))

    def test_missing_actionable_closing(self):
        bad_data = dict(self.valid_data)
        bad_data.pop("actionable_closing", None)
        violations = _lint_content(bad_data)
        self.assertTrue(any("MISSING_ACTIONABLE_CLOSING" in v for v in violations))

    def test_short_actionable_closing_points(self):
        bad_data = dict(self.valid_data)
        bad_data["actionable_closing"] = {
            "title": "AUDIT",
            "points": ["Fix it now."]
        }
        violations = _lint_content(bad_data)
        self.assertTrue(any("SHORT_ACTIONABLE_POINT" in v for v in violations))

    def test_paraphrased_actionable_closing(self):
        bad_data = dict(self.valid_data)
        # Point repeating exact hook text almost 100%
        bad_data["actionable_closing"] = {
            "title": "WHAT THIS MEANS FOR YOUR CODEBASE",
            "points": ["The 1MB Binder buffer is shared across your entire app process, not per transaction."]
        }
        violations = _lint_content(bad_data)
        self.assertTrue(any("PARAPHRASED_ACTIONABLE_CLOSING" in v for v in violations))

    def test_clean_content_fallbacks(self):
        minimal_data = {
            "title_line1": "TITLE",
            "title_line2": "SUBTITLE",
            "tagline": "A short tagline description",
            "hook": "A technical hook about android internals",
            "steps": [{"label": "Step 1", "points": ["First point about Android StateFlow API"]}],
            "stages": [{"label": "Stage 1", "snippet": "StateFlow.value"}]
        }
        cleaned = _clean_content(minimal_data)
        self.assertIn("confidence", cleaned["steps"][0])
        self.assertIn("actionable_closing", cleaned)
        self.assertGreaterEqual(len(cleaned["actionable_closing"]["points"]), 1)


class TestTemplatePaletteAndPhase55DOM(unittest.TestCase):
    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.tpl_dir = os.path.join(root, "renderer", "templates")
        self.env = Environment(loader=FileSystemLoader(self.tpl_dir))
        self.mock_context = {
            "title_line1": "COROUTINE MUTEX",
            "title_line2": "SERIAL EXECUTION",
            "tagline": "How concurrent BLE commands trigger GATT status 133 errors",
            "section_label": "CONCURRENCY INTERNALS",
            "stages": [
                {"label": "App Thread", "snippet": "gatt.writeCharacteristic()", "confidence": "confirmed"},
                {"label": "ATT Layer", "snippet": "Serial ATT request queue lock", "confidence": "confirmed"},
                {"label": "BLE Stack", "snippet": "Undocumented status 133 on race", "confidence": "confirmed"}
            ],
            "steps": [
                {"label": "Anti-Pattern", "confidence": "confirmed", "points": ["BleManager", "Unsynchronized", "gatt.writeCharacteristic()"]},
                {"label": "Production Fix", "confidence": "confirmed", "points": ["MutexQueue", "() -> Unit", "Mutex.withLock()"]},
                {"label": "Why It Breaks", "confidence": "confirmed", "points": ["Concurrent IPC calls overwrite the pending ATT transaction buffer", "Hardware controller drops packets when queue capacity is exceeded", "GattCallback returns undocumented status 133 instead of queued execution"]},
                {"label": "The Production Fix", "confidence": "analysis", "points": ["Wrap all GATT write and read operations in a Mutex channel queue", "Ensure each operation waits for its matching GattCallback completion", "Yield the coroutine context before dispatching subsequent operations"]}
            ],
            "flow_a_items": ["Mutex.withLock", "gatt.writeCharacteristic", "onCharacteristicWrite"],
            "flow_b_items": ["Serialize", "Await Callback", "Resume"],
            "hook": "The ATT protocol enforces strict single-transaction serialization per connection.",
            "actionable_closing": {
                "title": "WHAT THIS MEANS FOR YOUR CODEBASE",
                "points": [
                    "Audit every BluetoothGatt callback in your BLE module to ensure no concurrent writes are triggered.",
                    "Route all characteristic writes through a single coroutine Mutex queue."
                ]
            }
        }

    def test_all_templates_render_with_phase55_elements(self):
        templates = [
            "process_infographic_dark.html.j2",
            "code_card_dark.html.j2",
            "process_infographic_light.html.j2",
            "code_card_light.html.j2"
        ]

        # Forbidden off-palette colors
        forbidden_colors = ["#4ade80", "#fbbf24", "#f43f5e", "#ef4444", "#f59e0b", "#10b981"]

        for tpl_name in templates:
            tpl = self.env.get_template(tpl_name)
            html = tpl.render(self.mock_context)

            # 1. Hardcoded Eyebrow
            self.assertIn("AQUIB SHAIKH // MOBILE ARCHITECTURE &amp; ANDROID INTERNALS", html,
                          f"{tpl_name} missing hardcoded attribution eyebrow")

            # 2. Hardcoded Footer
            self.assertIn("Aquib Rashid Shaikh", html, f"{tpl_name} missing author footer")
            self.assertIn("Senior Android Developer &amp; Mobile Tech Lead", html, f"{tpl_name} missing handle")

            # 3. Phase 5.5a: Grounding Legend Bar
            self.assertIn("legendBar", html, f"{tpl_name} missing legendBar element")
            self.assertIn("CONFIRMED AOSP SPEC", html, f"{tpl_name} missing CONFIRMED AOSP SPEC pill")
            self.assertIn("ENGINEERING ANALYSIS", html, f"{tpl_name} missing ENGINEERING ANALYSIS pill")

            # 4. Phase 5.5a: Confidence Badges
            self.assertTrue("badge-confirmed" in html or "badge-analysis" in html,
                            f"{tpl_name} missing confidence badge classes")

            # 5. Phase 5.5c: Actionable Closing Block
            self.assertIn("actionableBlock", html, f"{tpl_name} missing actionableBlock element")
            self.assertIn("WHAT THIS MEANS FOR YOUR CODEBASE", html,
                          f"{tpl_name} missing actionable closing title")

            # 6. No banned AI phrases
            self.assertNotIn("AI SYSTEMS", html, f"{tpl_name} contains banned phrase 'AI SYSTEMS'")
            self.assertNotIn("tech behind AI", html, f"{tpl_name} contains banned phrase 'tech behind AI'")

            # 7. No sticky note DOM or styling
            self.assertNotIn("sticky-note", html, f"{tpl_name} contains sticky-note")
            self.assertNotIn("pushpin", html, f"{tpl_name} contains pushpin")

            # 8. Strict 2-accent palette check (no old emerald, amber, or red/pink)
            for color in forbidden_colors:
                self.assertNotIn(color.lower(), html.lower(),
                                 f"{tpl_name} contains forbidden off-palette color {color}")


if __name__ == "__main__":
    unittest.main()
