"""
Unit tests for LinkedIn text formatter.
"""

import unittest
from scripts.services.text_formatter import format_linkedin_text, to_unicode_bold


class TestTextFormatter(unittest.TestCase):
    def test_unicode_bold_conversion(self):
        text = "Hello World 123!"
        bold = to_unicode_bold(text)
        # Should convert letters and numbers to bold sans-serif
        self.assertEqual(bold, "𝗛𝗲𝗹𝗹𝗼 𝗪𝗼𝗿𝗹𝗱 𝟭𝟮𝟯!")

    def test_format_linkedin_text_bold(self):
        text = "1️⃣ **The Linker Failure Mode**: If an ELF shared object fails..."
        result = format_linkedin_text(text)
        self.assertIn("1️⃣ 𝗧𝗵𝗲 𝗟𝗶𝗻𝗸𝗲𝗿 𝗙𝗮𝗶𝗹𝘂𝗿𝗲 𝗠𝗼𝗱𝗲: If an ELF shared object fails...", result)
        self.assertNotIn("**", result)

    def test_format_linkedin_text_inline_code(self):
        text = "Compile with `-Wl,-z,max-page-size=16384` in your CMake."
        result = format_linkedin_text(text)
        self.assertEqual(result, "Compile with -Wl,-z,max-page-size=16384 in your CMake.")
        self.assertNotIn("`", result)

    def test_format_linkedin_text_complex(self):
        raw = """1️⃣ **The Linker Failure Mode**: If an ELF shared object (.so) in your APK lacks 16KB alignment...

**The Core Fixes / Takeaways:**
• Compile all native C/C++ targets with `-Wl,-z,max-page-size=16384` in your CMake / NDK build configurations.
• Audit native ELF segments locally using readelf: `readelf -l libnative.so | grep -E 'LOAD|ALIGN'`.
"""
        result = format_linkedin_text(raw)
        self.assertNotIn("**", result)
        self.assertNotIn("`", result)
        self.assertIn("1️⃣ 𝗧𝗵𝗲 𝗟𝗶𝗻𝗸𝗲𝗿 𝗙𝗮𝗶𝗹𝘂𝗿𝗲 𝗠𝗼𝗱𝗲:", result)
        self.assertIn("𝗧𝗵𝗲 𝗖𝗼𝗿𝗲 𝗙𝗶𝘅𝗲𝘀 / 𝗧𝗮𝗸𝗲𝗮𝘄𝗮𝘆𝘀:", result)
        self.assertIn("-Wl,-z,max-page-size=16384", result)
        self.assertIn("readelf -l libnative.so | grep -E 'LOAD|ALIGN'", result)


if __name__ == "__main__":
    unittest.main()
