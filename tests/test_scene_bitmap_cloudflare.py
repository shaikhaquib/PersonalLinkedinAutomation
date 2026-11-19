"""Unit tests for Cloudflare Workers AI scene generation path."""

from __future__ import annotations

import base64
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from scripts.services import scene_bitmap as sb


def _tiny_jpeg_b64() -> str:
    img = Image.new("RGB", (64, 64), (11, 18, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


class TestCloudflareSceneBitmap(unittest.TestCase):
    def test_generate_cloudflare_image_decodes_result(self):
        fake = MagicMock()
        fake.status_code = 200
        fake.headers = {"content-type": "application/json"}
        fake.json.return_value = {"success": True, "result": {"image": _tiny_jpeg_b64()}}
        fake.text = ""

        with patch.dict(
            "os.environ",
            {"CLOUDFLARE_ACCOUNT_ID": "acct", "CLOUDFLARE_API_TOKEN": "tok"},
            clear=False,
        ), patch("requests.post", return_value=fake) as post:
            raw = sb._generate_cloudflare_image("test phone on navy")
            self.assertTrue(raw.startswith(b"\xff\xd8") or len(raw) > 20)
            post.assert_called_once()
            args, kwargs = post.call_args
            # Prefer FLUX.2 klein; may fall through to schnell in live code
            self.assertIn("/ai/run/@cf/black-forest-labs/", args[0])

    def test_generate_scene_png_prefers_cloudflare_when_no_cache(self):
        with patch.object(sb, "_cloudflare_credentials", return_value=("acct", "tok")), \
             patch.object(sb, "_generate_cloudflare_image", return_value=base64.b64decode(_tiny_jpeg_b64())) as cf, \
             patch.object(sb, "_IMAGE_MODELS", []), \
             patch("tempfile.TemporaryDirectory") as _:
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                cache_dir = Path(tmp) / "scenes"
                out = cache_dir / "security.png"
                with patch.object(sb, "CACHE_DIR", cache_dir):
                    path = sb.generate_scene_png("security", out, use_cache=False)
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 100)
                cf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
