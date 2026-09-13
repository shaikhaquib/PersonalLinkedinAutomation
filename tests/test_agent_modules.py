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


class TestTelegramNotifier(unittest.TestCase):
    def test_unconfigured_notifier_does_not_crash(self):
        notifier = TelegramNotifier(bot_token="", chat_id="")
        self.assertFalse(notifier.is_configured())
        result = notifier.send_alert("Test Issue", "Reason", "Action")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
