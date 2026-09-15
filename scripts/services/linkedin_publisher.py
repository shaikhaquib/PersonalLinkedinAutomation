"""
LinkedIn Publisher with duplicate-detection pre-check and robust error handling.
"""

import os
import time
import requests

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 15


class LinkedInPublisher:
    def __init__(self, access_token: str, person_id: str, notifier=None):
        self.access_token = access_token
        self.person_id = person_id
        self.notifier = notifier

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def check_recent_post(self, post_text: str) -> str | None:
        """
        Check if the post already exists in the author's recent UGC posts.
        Protects against duplicate creation after network timeouts.
        """
        try:
            author_urn = f"urn:li:person:{self.person_id}"
            encoded_author = requests.utils.quote(f"List({author_urn})", safe="")
            url = f"https://api.linkedin.com/v2/ugcPosts?q=authors&authors={encoded_author}&count=5"

            resp = requests.get(url, headers=self._headers(), timeout=12)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                snippet = post_text[:80].strip()
                for el in elements:
                    content = el.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {})
                    commentary = content.get("shareCommentary", {}).get("text", "")
                    if snippet and snippet in commentary:
                        post_id = el.get("id", "")
                        print(f"  [LinkedIn] Pre-check: Found matching existing post ({post_id})! Skipping duplicate POST.")
                        return post_id
        except Exception as e:
            print(f"  [LinkedIn] Pre-check warning ({e})")

        return None

    def publish(self, post_text: str, image_urn: str = None) -> str:
        """Publish post to LinkedIn personal profile with retry verification."""
        if not self.access_token or not self.person_id:
            msg = "Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_ID."
            if self.notifier:
                self.notifier.send_alert("Missing LinkedIn Credentials", msg, "Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID in .env or GitHub secrets.")
            raise RuntimeError(msg)

        author_urn = f"urn:li:person:{self.person_id}"

        if image_urn:
            share_content = {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": image_urn}],
            }
        else:
            share_content = {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE",
            }

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": share_content,
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        # Step 1: Pre-check if already published before making any request
        existing_id = self.check_recent_post(post_text)
        if existing_id:
            return existing_id

        # Step 2: POST with duplicate-safe retries
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    "https://api.linkedin.com/v2/ugcPosts",
                    headers=self._headers(),
                    json=payload,
                    timeout=20,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                print(f"  [LinkedIn] Network issue on attempt {attempt}: {net_err}")
                # CRITICAL: Before blindly retrying, check if LinkedIn actually processed the post
                time.sleep(5)
                existing_id = self.check_recent_post(post_text)
                if existing_id:
                    return existing_id

                if attempt == MAX_RETRIES:
                    raise RuntimeError("LinkedIn API network timeout; verified post was not created.")
                continue

            if response.status_code == 201:
                post_id = response.headers.get("x-restli-id", "unknown")
                print(f"  [LinkedIn] Published! Post ID: {post_id}")
                return post_id

            if response.status_code == 429:
                wait_sec = RETRY_BASE_SECONDS * attempt
                print(f"  [LinkedIn] 429 Rate limited. Waiting {wait_sec}s...")
                time.sleep(wait_sec)
                continue

            if response.status_code == 401:
                msg = "LinkedIn access token has expired or is invalid."
                if self.notifier:
                    self.notifier.send_alert("LinkedIn 401 Unauthorized", msg, "Run `python scripts/get_linkedin_token.py` to refresh token.")
                raise RuntimeError(msg)

            if response.status_code == 403:
                msg = f"LinkedIn returned 403 Forbidden: {response.text}"
                if self.notifier:
                    self.notifier.send_alert("LinkedIn 403 Forbidden", msg, "Verify permissions and that product is active on LinkedIn developer portal.")
                raise RuntimeError(msg)

            try:
                err = response.json()
            except Exception:
                err = response.text
            raise RuntimeError(f"LinkedIn API error {response.status_code}: {err}")

        raise RuntimeError("LinkedIn API: exhausted retries.")

    def post_first_comment(self, post_id: str, comment_text: str, delay_seconds: int = None):
        if not comment_text:
            return

        if delay_seconds is None:
            try:
                delay_seconds = int(os.getenv("FIRST_COMMENT_DELAY_SECONDS", "180"))
            except ValueError:
                delay_seconds = 180

        if delay_seconds > 0:
            print(f"  [LinkedIn] Waiting {delay_seconds}s before posting first comment (human simulation)...")
            time.sleep(delay_seconds)

        share_urn = post_id if post_id.startswith("urn:") else f"urn:li:ugcPost:{post_id}"
        encoded_urn = requests.utils.quote(share_urn, safe="")

        try:
            resp = requests.post(
                f"https://api.linkedin.com/v2/socialActions/{encoded_urn}/comments",
                headers=self._headers(),
                json={
                    "actor": f"urn:li:person:{self.person_id}",
                    "message": {"text": comment_text},
                },
                timeout=15,
            )
            if resp.status_code in (200, 201):
                print("  [LinkedIn] First comment posted successfully.")
            else:
                print(f"  [LinkedIn] First comment returned status {resp.status_code} (non-fatal)")
        except Exception as e:
            print(f"  [LinkedIn] First comment skipped ({e})")
