"""
Unit tests for Carousel PDF rendering and decision routing.
"""

import os
import unittest
import tempfile
from scripts.services.image_decision import ImageDecisionAgent
from scripts.infographic import generate_carousel_content, render_carousel_pdf


class TestCarousel(unittest.TestCase):
    def test_image_decision_triggers_carousel_for_long_content(self):
        agent = ImageDecisionAgent()
        
        # Short post -> standard blueprint/code card
        short_topic = "Android StateFlow in ViewModel"
        short_post = "StateFlow is a state-holder observable flow."
        needs_img, reason, tpl = agent.decide(short_topic, short_post)
        self.assertNotEqual(tpl, "carousel_card.html.j2")

        # Long post (>= 1150 chars or 4+ bullets) -> carousel
        long_topic = "Android 15 16KB Memory Page Size Migration"
        long_post = (
            "Android 15's 16KB memory page size support will immediately crash unaligned native libraries at process startup.\n\n"
            "Legacy Android devices strictly ran on 4KB memory pages.\n\n"
            "1️⃣ The Linker Failure Mode: If an ELF shared object (.so) lacks 16KB alignment, dynamic linker aborts.\n\n"
            "2️⃣ The Hidden Transitive Risk: Even if first-party code is aligned, legacy closed-source third-party binaries crash.\n\n"
            "The Core Fixes / Takeaways:\n"
            "• Compile all native targets with -Wl,-z,max-page-size=16384 in CMake.\n"
            "• Audit native ELF segments locally using readelf.\n"
            "• Enforce automated CI linting on merged AAR dependencies.\n"
            "• Verify third-party SDK provider compliance before release.\n\n"
            "How does your mobile team audit closed-source native dependencies?\n\n"
            "Scaling high-impact mobile platforms or modernizing your Android stack? DMs are open."
        )
        needs_img, reason, tpl = agent.decide(long_topic, long_post)
        self.assertTrue(needs_img)
        self.assertEqual(tpl, "carousel_card.html.j2")
        self.assertIn("Carousel", reason)

    def test_generate_and_render_carousel_pdf(self):
        topic = "Preparing Native Android Libraries for 16KB Page Sizes"
        post_text = (
            "Android 15 introduces 16KB memory page sizes.\n\n"
            "Legacy devices ran on 4KB pages.\n\n"
            "• Unaligned .so libraries will crash with UnsatisfiedLinkError.\n"
            "• Compile targets with -Wl,-z,max-page-size=16384.\n"
            "• Audit ELF segments locally with readelf."
        )
        
        # Test fallback content generation
        content = generate_carousel_content(topic, post_text, lambda p, s: "INVALID_JSON_FORCING_FALLBACK")
        self.assertIn("slides", content)
        self.assertGreaterEqual(len(content["slides"]), 2)

        # Test Playwright PDF render
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_pdf = os.path.join(tmp_dir, "test_out_carousel.pdf")
            rendered_path = render_carousel_pdf(content, out_pdf, template="carousel_card.html.j2")
            self.assertTrue(os.path.exists(rendered_path))
            self.assertGreater(os.path.getsize(rendered_path), 5000)


if __name__ == "__main__":
    unittest.main()
