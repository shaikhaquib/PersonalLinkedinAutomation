import unittest

from scripts.services.image_decision import ImageDecisionAgent
from scripts.services.topic_analyzer import TopicAnalyzer
from scripts.services.schedule_rotator import (
    get_weekday_rotation,
    is_publish_day,
    is_blocked_topic,
)


class TestImageDecision(unittest.TestCase):
    def setUp(self):
        self.agent = ImageDecisionAgent()

    def test_opinion_post_skips_image(self):
        topic = "Career Lessons from Mentorship and Soft Skills"
        text = "My observation on engineering career growth and why mentorship matters more than titles..."
        needs_image, _ = self.agent.should_generate_image(topic, text)
        self.assertFalse(needs_image)

    def test_code_autopsy_routes_to_code_card(self):
        needs, reason, tpl = self.agent.decide(
            "CancellationException swallowed in ViewModel",
            "fun load() { viewModelScope.launch { try { repo.get() } catch (e: Exception) {} } }",
            archetype_id="CODE_AUTOPSY_TEARDOWN",
        )
        self.assertTrue(needs)
        self.assertIn("code_card", tpl)
        self.assertIn("code", reason.lower())

    def test_biometric_routes_to_aware_bitmap(self):
        needs, reason, tpl = self.agent.decide(
            "Android banking biometric logins can be bypassed",
            "Weak local auth state checks after BiometricPrompt success.",
            archetype_id="CONTRARIAN_ARCHITECTURE_CALLOUT",
        )
        self.assertTrue(needs)
        self.assertEqual(tpl, "aware_graphic_dark.html.j2")
        self.assertIn("bitmap", reason.lower())

    def test_contrarian_without_product_visual_uses_bullet_card(self):
        needs, reason, tpl = self.agent.decide(
            "Clean Architecture tax slows shipping",
            "Too many UseCase classes. Rule: collapse boundaries until a real domain appears.",
            archetype_id="CONTRARIAN_ARCHITECTURE_CALLOUT",
        )
        self.assertTrue(needs)
        self.assertEqual(tpl, "bullet_card_dark.html.j2")


class TestScheduleRotator(unittest.TestCase):
    def test_mwf_publish_days_and_pillars(self):
        from datetime import datetime

        mon = get_weekday_rotation(datetime(2026, 9, 21))  # Monday
        self.assertEqual(mon["day_name"], "Monday")
        self.assertTrue(mon["publishes"])
        self.assertEqual(mon["pillar"], "android")
        self.assertTrue(is_publish_day(datetime(2026, 9, 21)))

        tue = get_weekday_rotation(datetime(2026, 9, 22))
        self.assertEqual(tue["day_name"], "Tuesday")
        self.assertFalse(tue["publishes"])
        self.assertFalse(is_publish_day(datetime(2026, 9, 22)))

        wed = get_weekday_rotation(datetime(2026, 9, 23))
        self.assertEqual(wed["day_name"], "Wednesday")
        self.assertTrue(wed["publishes"])
        self.assertEqual(wed["pillar"], "ai_android")
        self.assertEqual(wed["theme"], "dark")

        thu = get_weekday_rotation(datetime(2026, 9, 24))
        self.assertFalse(thu["publishes"])

        fri = get_weekday_rotation(datetime(2026, 9, 25))
        self.assertEqual(fri["day_name"], "Friday")
        self.assertTrue(fri["publishes"])
        self.assertEqual(fri["pillar"], "tech_news")

    def test_blocked_topics(self):
        self.assertTrue(is_blocked_topic("UPI MDR rate change for Android payments"))
        self.assertTrue(is_blocked_topic("The Fold Was Already Mapped"))
        self.assertFalse(is_blocked_topic("Compose LazyColumn jank after StateFlow emit"))


class TestTopicAnalyzerMobileFocus(unittest.TestCase):
    def test_non_mobile_topic_rejected(self):
        analyzer = TopicAnalyzer(min_score=0.70)
        res = analyzer.score_heuristic(
            "How to trade Bitcoin and Ethereum on Binance",
            "Cryptocurrency price swings",
            "crypto_news",
        )
        self.assertLess(res["overall_score"], 0.50)

    def test_blocked_upi_and_fold_score_near_zero(self):
        analyzer = TopicAnalyzer(min_score=0.65)
        upi = analyzer.score_heuristic(
            "UPI MDR Rate Change: what it means for Android",
            "Merchant discount rate updates for UPI payments",
            "manual",
        )
        self.assertLess(upi["overall_score"], 0.1)
        self.assertTrue(upi.get("blocked"))

        fold = analyzer.score_heuristic(
            "The Fold Was Already Mapped",
            "Apple foldable vs Android foldable journey",
            "manual",
        )
        self.assertTrue(fold.get("blocked"))

    def test_broad_mobile_topics_rank_high(self):
        analyzer = TopicAnalyzer(min_score=0.65)

        res_pain = analyzer.score_heuristic(
            "Checkout freezes and ANRs after Room queries on the main thread",
            "Users see a frozen pay button and leave 1-star reviews after production release",
            "proandroiddev",
            pillar="android",
        )
        self.assertGreaterEqual(res_pain["overall_score"], 0.75)
        self.assertGreaterEqual(res_pain["pain_score"], 0.70)

        res_ai = analyzer.score_heuristic(
            "Gemini Nano On-Device Acceleration on Android AICore",
            "Optimizing LLM inference on Android devices using MediaPipe to cut latency",
            "android_ai",
            pillar="ai_android",
        )
        self.assertGreaterEqual(res_ai["overall_score"], 0.70)

    def test_friday_allows_tech_news_layoffs(self):
        analyzer = TopicAnalyzer(min_score=0.65)
        res = analyzer.score_heuristic(
            "Big tech AI layoffs reshape mobile hiring",
            "Layoffs hit AI teams while Apple Intelligence and Gemini race continues",
            "tech_news",
            pillar="tech_news",
        )
        self.assertGreaterEqual(res["overall_score"], 0.65)


if __name__ == "__main__":
    unittest.main()
