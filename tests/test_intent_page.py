import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from mizoki_runtime import create_runtime


SITE_ROOT = Path(__file__).resolve().parents[1]


class IntentPageTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        self.dist_dir = tempfile.TemporaryDirectory()
        dist = Path(self.dist_dir.name)
        (dist / "assets").mkdir()
        (dist / "index.html").write_text(
            '<link rel="canonical" href="https://mizoki3.com/intent">',
            encoding="utf-8",
        )
        (dist / "assets" / "intent.js").write_text("console.log('intent');", encoding="utf-8")
        self.intent_patch = patch("app.INTENT_DIST_DIR", dist)
        self.intent_patch.start()
        runtime = create_runtime(base_dir=SITE_ROOT, data_dir=Path(self.runtime_dir.name))
        app = create_app(runtime=runtime)
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self) -> None:
        self.intent_patch.stop()
        self.dist_dir.cleanup()
        self.runtime_dir.cleanup()

    def test_intent_route_serves_only_the_dedicated_build(self) -> None:
        response = self.client.get("/intent")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"https://mizoki3.com/intent", response.data)
        self.assertEqual("no-cache", response.headers["Cache-Control"])

        asset = self.client.get("/intent/assets/intent.js")
        self.assertEqual(200, asset.status_code)
        self.assertEqual("public, max-age=31536000, immutable", asset.headers["Cache-Control"])

    def test_unrelated_routes_remain_bound_to_existing_handlers(self) -> None:
        self.assertEqual(200, self.client.get("/").status_code)
        self.assertEqual(200, self.client.get("/signal").status_code)
        self.assertEqual(404, self.client.get("/intent/not-generated.txt").status_code)

    def test_sitemap_contains_canonical_intent_route(self) -> None:
        response = self.client.get("/sitemap.xml")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"https://mizoki3.com/intent", response.data)


if __name__ == "__main__":
    unittest.main()
