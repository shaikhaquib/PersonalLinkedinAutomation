"""
Telegram Emergency Notifier.
Alerts the user strictly when human intervention is required (e.g. expired tokens, 401/403 errors).
"""

import os
import requests


class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_alert(self, title: str, reason: str, action_required: str):
        """Send high-priority alert to the user."""
        message = (
            f"🚨 *LinkedIn Automation Alert*\n\n"
            f"*Issue:* {title}\n"
            f"*Reason:* {reason}\n\n"
            f"*Action Required:*\n{action_required}"
        )
        print(f"\n[ALERT] {title}: {reason}")
        print(f"[ACTION] {action_required}\n")

        if not self.is_configured():
            print("  (Telegram not configured — alert logged locally only)")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"  [Telegram] Failed to send alert: {e}")
            return False

    def send_daily_report(self, topic: str, post_id: str, timestamp_str: str):
        """Optional daily success notification (only if daily_report is enabled)."""
        if not self.is_configured():
            return False

        message = (
            f"✅ *LinkedIn Post Published*\n\n"
            f"*Topic:* {topic}\n"
            f"*Time:* {timestamp_str}\n"
            f"*Post ID:* `{post_id}`"
        )
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            requests.post(url, json={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
            return True
        except Exception:
            return False
