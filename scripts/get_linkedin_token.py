#!/usr/bin/env python3
"""
One-time LinkedIn OAuth token generator.

Run this once to get your access token + person ID, then store them
as GitHub secrets: LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID.

Usage:
    python scripts/get_linkedin_token.py

Requirements:
    LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in .env
"""

import os
import sys
import re
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

CLIENT_ID     = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI  = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8080/callback")
SCOPES        = os.environ.get("LINKEDIN_SCOPES", "openid profile w_member_social")

if not CLIENT_ID or not CLIENT_SECRET:
    sys.exit(
        "ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set in your .env file.\n"
        "  Find them at: https://developer.linkedin.com → your app → Auth tab"
    )

# ── Step 1: build the auth URL ────────────────────────────────────────────────

state = secrets.token_urlsafe(16)

auth_url = (
    "https://www.linkedin.com/oauth/v2/authorization?"
    + urllib.parse.urlencode({
        "response_type": "code",
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPES,
        "state":         state,
    })
)

# ── Step 2: local callback server ─────────────────────────────────────────────

_auth_code = None
_got_state = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code, _got_state
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.endswith("favicon.ico"):
            self.send_response(204)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        incoming_code = params.get("code", [None])[0]
        incoming_state = params.get("state", [None])[0]

        if incoming_state == state and incoming_code:
            _auth_code = incoming_code
            _got_state = incoming_state
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful! You can close this tab and return to the terminal.</h2>")
        else:
            # Stale request or mismatched state
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Ignoring stale or invalid authorization session. Please use the newly opened tab.</h2>")

    def log_message(self, *args):
        pass  # silence request logs

# ── Step 3: open browser + wait for callback ──────────────────────────────────

print("\n" + "="*60)
print("  LinkedIn OAuth — one-time token setup")
print("="*60)
print("\n  Opening your browser for LinkedIn authorization...")
print("  (If it does not open automatically, paste this URL:)")
print(f"\n  {auth_url}\n")

webbrowser.open(auth_url)

is_manual = "--manual" in sys.argv

parsed_redirect = urllib.parse.urlparse(REDIRECT_URI)
listen_port = parsed_redirect.port or 8080

if is_manual:
    print("  [Manual Mode] Paste the redirected URL or code below:")
    try:
        manual_input = input("  URL or Code: ").strip()
        if "code=" in manual_input:
            parsed = urllib.parse.urlparse(manual_input)
            qs = urllib.parse.parse_qs(parsed.query)
            _auth_code = qs.get("code", [None])[0]
        else:
            _auth_code = manual_input
    except Exception as e:
        sys.exit(f"ERROR: {e}")
else:
    print(f"  Callback listener started on port {listen_port}.")
    print("  Waiting for authorization redirect from your browser...")
    server = HTTPServer(("0.0.0.0", listen_port), CallbackHandler)
    while not _auth_code:
        server.handle_request()

if not _auth_code:
    sys.exit("ERROR: No authorization code received. Did you approve the app?")

print("  Authorization code received!\n")

# ── Step 4: exchange code for access token ────────────────────────────────────

resp = requests.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type":    "authorization_code",
        "code":          _auth_code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    },
    timeout=15,
)
resp.raise_for_status()
token_resp = resp.json()

access_token = token_resp.get("access_token")
expires_in   = token_resp.get("expires_in", 0)
expires_days = round(expires_in / 86400)

if not access_token:
    sys.exit(f"ERROR: Token exchange failed: {token_resp}")

# Auto-save access token to .env immediately
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()
    if "LINKEDIN_ACCESS_TOKEN=" in env_content:
        env_content = re.sub(r"LINKEDIN_ACCESS_TOKEN=.*", f"LINKEDIN_ACCESS_TOKEN={access_token}", env_content)
    else:
        env_content += f"\nLINKEDIN_ACCESS_TOKEN={access_token}"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"  [Success] Saved LINKEDIN_ACCESS_TOKEN to .env")

# ── Step 5: fetch person ID from userinfo or me ───────────────────────────────

person_id = None
person_name = "Authenticated Member"

try:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if resp.status_code == 200:
        userinfo = resp.json()
        person_id = userinfo.get("sub")
        person_name = userinfo.get("name", person_name)
except Exception:
    pass

if not person_id:
    try:
        resp = requests.get(
            "https://api.linkedin.com/v2/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if resp.status_code == 200:
            me_json = resp.json()
            person_id = me_json.get("id")
            fn = me_json.get("localizedFirstName", "")
            ln = me_json.get("localizedLastName", "")
            if fn or ln:
                person_name = f"{fn} {ln}".strip()
    except Exception:
        pass

if person_id and os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        env_content = f.read()
    if "LINKEDIN_PERSON_ID=" in env_content:
        env_content = re.sub(r"LINKEDIN_PERSON_ID=.*", f"LINKEDIN_PERSON_ID={person_id}", env_content)
    else:
        env_content += f"\nLINKEDIN_PERSON_ID={person_id}"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"  [Success] Saved LINKEDIN_PERSON_ID ({person_id}) to .env")

print("\n" + "="*60)
print(f"  LINKEDIN AUTHENTICATION SUCCESSFUL")
print("="*60)
print(f"  Authenticated User : {person_name}")
print(f"  Access Token (60d) : {access_token[:20]}... [Saved in .env]")
if person_id:
    print(f"  Person ID          : {person_id} [Saved in .env]")
else:
    print("  Person ID          : Auto-detect requires 'Sign In with OpenID Connect' product")
    print("                       OR find your member ID on your profile URL.")
print("="*60 + "\n")
print("="*60)
print()
print("  Copy these two values into your GitHub secrets")
print("  (Settings → Secrets and variables → Actions → New secret):")
print()
print(f"  Secret name : LINKEDIN_ACCESS_TOKEN")
print(f"  Secret value: {access_token}")
print()
print(f"  Secret name : LINKEDIN_PERSON_ID")
print(f"  Secret value: {person_id}")
print()
print("  Also add them to your local .env:")
print(f"  LINKEDIN_ACCESS_TOKEN={access_token}")
print(f"  LINKEDIN_PERSON_ID={person_id}")
print()
print(f"  Token expires in ~{expires_days} days. Re-run this script to refresh.")
print("="*60 + "\n")
