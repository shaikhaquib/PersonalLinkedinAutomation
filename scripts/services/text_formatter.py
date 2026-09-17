"""
Text Formatter for LinkedIn.
LinkedIn does not support Markdown formatting (such as **bold** or `code`).
This module converts Markdown bold to Unicode Bold (Mathematical Sans-Serif)
and cleans code backticks and fences so posts render natively and professionally on LinkedIn feeds.
"""

import re


def to_unicode_bold(text: str) -> str:
    """
    Convert ASCII letters and digits in text to Unicode Mathematical Sans-Serif Bold.
    Punctuation, symbols, emojis, and whitespace are preserved as-is.
    """
    result = []
    for char in text:
        cp = ord(char)
        if 0x41 <= cp <= 0x5A:  # A-Z -> 𝗔-𝗭
            result.append(chr(0x1D5D4 + (cp - 0x41)))
        elif 0x61 <= cp <= 0x7A:  # a-z -> 𝗮-𝘇
            result.append(chr(0x1D5EE + (cp - 0x61)))
        elif 0x30 <= cp <= 0x39:  # 0-9 -> 𝟬-𝟵
            result.append(chr(0x1D7EC + (cp - 0x30)))
        else:
            result.append(char)
    return "".join(result)


def format_linkedin_text(text: str) -> str:
    """
    Convert Markdown formatting into native LinkedIn-friendly Unicode text:
    1. Triple backtick code blocks -> stripped of fences, preserving content.
    2. **bold** and __bold__ -> Unicode Sans-Serif Bold characters.
    3. `inline code` -> clean plain text without backtick noise.
    4. Markdown header markers (### ) -> stripped or bolded.
    5. Stray italics (*word* or _word_) -> plain text.
    """
    if not text:
        return ""

    # 1. Strip triple-backtick code fences
    text = re.sub(r"```[a-zA-Z0-9_-]*\n?(.*?)\n?```", r"\1", text, flags=re.DOTALL)

    # 2. Convert **bold** and __bold__ to Unicode bold
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: to_unicode_bold(m.group(1)), text)
    text = re.sub(r"__(.+?)__", lambda m: to_unicode_bold(m.group(1)), text)

    # 3. Strip backticks around inline code snippets
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 4. Remove Markdown header markers at the start of a line (e.g., "### Header" -> "Header")
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 5. Clean stray italic markers around single words/phrases if any
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"\1", text)

    return text
