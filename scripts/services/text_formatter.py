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
    Convert Markdown into LinkedIn-native text (LinkedIn does not render MD):
    1. Triple backtick fences -> content only
    2. **bold** / __bold__ -> Unicode Mathematical Sans-Serif Bold
    3. `inline code` -> plain text (backticks removed)
    4. Markdown headers / links / list markers cleaned
    5. Stray italic *word* / _word_ -> plain
    6. Orphan asterisk / underscore lines removed (common LLM residue)
    """
    if not text:
        return ""

    # 1. Strip triple-backtick code fences
    text = re.sub(r"```[a-zA-Z0-9_-]*\n?(.*?)\n?```", r"\1", text, flags=re.DOTALL)

    # 2. Convert **bold** and __bold__ to Unicode bold (LinkedIn-visible emphasis)
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: to_unicode_bold(m.group(1)), text)
    text = re.sub(r"__(.+?)__", lambda m: to_unicode_bold(m.group(1)), text)

    # 3. Strip backticks around inline code snippets
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 4. Markdown links [label](url) -> label (url) or just label
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # 5. Remove Markdown header markers at the start of a line
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # 6. Clean stray italic markers around single words/phrases
    text = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"\1", text)

    # 7. Drop orphan markdown residue lines (lone *, **, -, ---)
    lines = []
    for line in text.splitlines():
        if re.fullmatch(r"[\*\-_=~`]+", line.strip() or ""):
            continue
        lines.append(line)
    text = "\n".join(lines)

    # 8. Collapse 3+ blank lines; trim trailing whitespace on each line
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
