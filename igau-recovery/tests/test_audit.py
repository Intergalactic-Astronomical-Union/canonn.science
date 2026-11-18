"""Offline tests for IGAU's read-only Canonn recovery audit."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit.py"
SPEC = importlib.util.spec_from_file_location("igau_recovery_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_normalize_image_derivatives(self):
        self.assertEqual(audit.normalize_name("ancient_medium_001-A-300x200.webp"),
                         "ancient_medium_001-a")
        self.assertEqual(audit.normalize_name("ancient_medium_001-A.jpeg"),
                         "ancient_medium_001-a")

    def test_recovery_candidates_are_not_confirmed_recoveries(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            article = repo / "content" / "articles" / "guardian-test"
            media = article / "media"
            media.mkdir(parents=True)
            (media / "existing.webp").write_bytes(b"image content")
            (article / "article.json").write_text(json.dumps({
                "title": "Guardian test", "slug": "guardian-test",
                "section": "codex", "banner": "media/existing.webp"
            }), encoding="utf-8")
            (article / "body.html").write_text(
                '<img src="media/existing.webp">'
                '<img src="media/existing.webp 960w">'
                '<img src="media/not-there.png">'
                '<img src="/assets/media/2026/06/bank-A.jpeg">'
                '<a href="https://imgur.com/a/GWQ4w">Source gallery</a>'
                '<a href="/codex/guardian-structure/">Internal article</a>',
                encoding="utf-8"
            )
            n, rows = audit.audit(repo)
            self.assertEqual(n, 1)
            self.assertEqual(len(rows), 4)
            self.assertEqual(
                {r["classification"] for r in rows},
                {"missing_local_file", "malformed_src_width_descriptor", "legacy_media_url_review", "external_imgur_review"}
            )
            legacy = next(r for r in rows if r["classification"] == "legacy_media_url_review")
            self.assertEqual(legacy["archive_target"],
                             "https://canonn.science/assets/media/2026/06/bank-A.jpeg")
            self.assertTrue(all(r["wayback_status"] == "not_checked" for r in rows))

    def test_path_traversal_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            article = repo / "content" / "articles" / "unsafe-test"
            article.mkdir(parents=True)
            (article / "article.json").write_text(json.dumps({
                "title": "Unsafe", "slug": "unsafe-test", "section": "codex"
            }), encoding="utf-8")
            (article / "body.html").write_text(
                '<img src="media/../../../../private.png">', encoding="utf-8"
            )
            _, rows = audit.audit(repo)
            self.assertEqual(rows[0]["classification"], "unsafe_local_path")


if __name__ == "__main__":
    unittest.main()
