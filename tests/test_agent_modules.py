"""
Unit tests for Autonomous LinkedIn Content Agent modules.
"""

import os
import unittest
import tempfile
import sqlite3

from scripts.storage.history_manager import HistoryManager
from scripts.services.topic_analyzer import TopicAnalyzer
from scripts.services.image_decision import ImageDecisionAgent
from scripts.services.telegram_notifier import TelegramNotifier


class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_history.db")
        self.history = HistoryManager(db_path=self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_database_initialization(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("posts", tables)
            self.assertIn("attempted_topics", tables)

    def test_duplicate_detection(self):
        topic = "Jetpack Compose Recomposition Optimization"
        title = "Why Unstable Parameters Kill Compose Performance"
        content = "In real Android apps, recomposition can freeze frames..."
        post_id = "urn:li:ugcPost:123456"

        # Initially, not duplicate
        is_dup, _ = self.history.is_duplicate(topic, title, content)
        self.assertFalse(is_dup)

        # Record post
        self.history.record_post(topic, title, content, post_id, has_image=True)

        # Exact hash duplicate
        is_dup, reason = self.history.is_duplicate("Different Topic", "Different Title", content)
        self.assertTrue(is_dup)
        self.assertIn("content hash", reason)

        # Topic duplicate
        is_dup, reason = self.history.is_duplicate(topic, "A Completely Different Title")
        self.assertTrue(is_dup)
        self.assertIn("already posted", reason)

        # Similar title duplicate
        similar_title = "Why Unstable Parameters Ruin Compose Performance"
        is_dup, reason = self.history.is_duplicate("Brand New Topic", similar_title)
        self.assertTrue(is_dup)
        self.assertIn("too similar", reason)

    def test_has_published_today(self):
        self.assertFalse(self.history.has_published_today())
        self.history.record_post("Topic 1", "Title 1", "Content 1", "id1")
        self.assertTrue(self.history.has_published_today())


class TestTopicAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = TopicAnalyzer(min_score=0.70)

    def test_high_value_topic_score(self):
        title = "Migrating to Kotlin 2.0 and Jetpack Compose Compiler Internals"
        summary = "How K2 compiler improves Android build times and avoids recomposition jank."
        result = self.analyzer.score_heuristic(title, summary, "Kotlin Blog")
        self.assertGreaterEqual(result["overall_score"], 0.70)
        self.assertGreaterEqual(result["relevance"], 0.70)

    def test_hype_topic_penalty(self):
        title = "10x Your Productivity With These Revolutionary ChatGPT Prompts"
        summary = "Unlock the power of AI tools to write code instantly."
        result = self.analyzer.score_heuristic(title, summary, "Tech Site")
        self.assertLess(result["overall_score"], 0.70)


class TestImageDecisionAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ImageDecisionAgent()

    def test_technical_workflow_needs_image(self):
        topic = "Android Process Lifecycle & Binder Transaction Flow"
        text = "When Android terminates your background process, the OS does not notify..."
        needs_image, _ = self.agent.should_generate_image(topic, text)
        self.assertTrue(needs_image)

    def test_opinion_post_skips_image(self):
        topic = "Career Lessons from 8 Years as an Android Developer"
        text = "My observation on software engineering career growth and why mentorship matters..."
        needs_image, _ = self.agent.should_generate_image(topic, text)
        self.assertFalse(needs_image)

    def test_theme_routing_dark_and_light(self):
        topic_arch = "BLE GATT Queueing and Status 133"
        text_arch = "Serialization of BluetoothGatt.writeCharacteristic calls using Mutex."
        needs_img, _, tpl_dark = self.agent.decide(topic_arch, text_arch, theme="dark")
        self.assertTrue(needs_img)
        self.assertEqual(tpl_dark, "process_infographic_dark.html.j2")

        _, _, tpl_light = self.agent.decide(topic_arch, text_arch, theme="light")
        self.assertEqual(tpl_light, "process_infographic_light.html.j2")

        topic_code = "Jetpack Compose Recomposition Loop in ViewModel"
        text_code = "Anti-pattern of passing ViewModel directly into Composable vs state hoisting."
        _, _, code_dark = self.agent.decide(topic_code, text_code, archetype_id="CODE_AUTOPSY_TEARDOWN", theme="dark")
        self.assertEqual(code_dark, "code_card_dark.html.j2")

        _, _, code_light = self.agent.decide(topic_code, text_code, archetype_id="CODE_AUTOPSY_TEARDOWN", theme="light")
        self.assertEqual(code_light, "code_card_light.html.j2")


class TestScheduleRotator(unittest.TestCase):
    def test_all_weekdays_have_unique_rotations(self):
        from scripts.services.schedule_rotator import get_weekday_rotation
        from datetime import datetime

        # Test Monday (2026-09-21 is Monday)
        mon = get_weekday_rotation(datetime(2026, 9, 21))
        self.assertEqual(mon["day_name"], "Monday")
        self.assertEqual(mon["preferred_archetype"], "SCALE_INCIDENT_WAR_STORY")

        # Test Tuesday (2026-09-22 is Tuesday)
        tue = get_weekday_rotation(datetime(2026, 9, 22))
        self.assertEqual(tue["day_name"], "Tuesday")
        self.assertEqual(tue["preferred_archetype"], "CODE_AUTOPSY_TEARDOWN")

        # Test Wednesday (2026-09-23 is Wednesday)
        wed = get_weekday_rotation(datetime(2026, 9, 23))
        self.assertEqual(wed["day_name"], "Wednesday")
        self.assertEqual(wed["theme"], "light")

        # Test Thursday (2026-09-24 is Thursday)
        thu = get_weekday_rotation(datetime(2026, 9, 24))
        self.assertEqual(thu["day_name"], "Thursday")
        self.assertEqual(thu["preferred_archetype"], "CONTRARIAN_ARCHITECTURE_CALLOUT")

        # Test Friday (2026-09-25 is Friday)
        fri = get_weekday_rotation(datetime(2026, 9, 25))
        self.assertEqual(fri["day_name"], "Friday")
        self.assertEqual(fri["preferred_archetype"], "HARDWARE_LOW_LEVEL_DEEP_DIVE")


class TestTopicAnalyzerMobileFocus(unittest.TestCase):
    def test_non_mobile_topic_rejected(self):
        analyzer = TopicAnalyzer(min_score=0.70)
        res = analyzer.score_heuristic("How to trade Bitcoin and Ethereum on Binance", "Cryptocurrency price swings", "crypto_news")
        self.assertLess(res["overall_score"], 0.50)

    def test_broad_mobile_topics_rank_high(self):
        analyzer = TopicAnalyzer(min_score=0.70)
        
        # On-Device AI in Mobile
        res_ai = analyzer.score_heuristic("Gemini Nano On-Device Acceleration on Android AICore", "Optimizing LLM inference on Android devices using MediaPipe", "google_blog")
        self.assertGreaterEqual(res_ai["overall_score"], 0.75)

        # OS Internals
        res_os = analyzer.score_heuristic("Android 16 Kernel Memory Management and ART GC Pause Reductions", "Under the hood analysis of AOSP runtime changes", "android_police")
        self.assertGreaterEqual(res_os["overall_score"], 0.75)

        # Media & Hardware
        res_ble = analyzer.score_heuristic("Tuning Media3 ExoPlayer Buffers to Eliminate Playback Jank", "Optimizing DefaultLoadControl under network drops on mobile", "android_weekly")
        self.assertGreaterEqual(res_ble["overall_score"], 0.75)


if __name__ == "__main__":
    unittest.main()
