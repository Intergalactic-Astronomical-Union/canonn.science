"""Offline tests for bounded original-source media candidate recovery."""
import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "origin_probe.py"
SPEC = importlib.util.spec_from_file_location("canonn_origin_probe", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class OriginalMediaTests(unittest.TestCase):
    def test_magic_signatures(self):
        self.assertTrue(module.media_signature(b"\xff\xd8\xffabcd\xff\xd9", "jpeg"))
        self.assertTrue(module.media_signature(b"OggS\x00\x02", "ogg"))
        self.assertTrue(module.media_signature(b"\x89PNG\r\n\x1a\nmore", "png"))
        self.assertFalse(module.media_signature(b"<html>not media</html>", "jpeg"))
        self.assertFalse(module.media_signature(b"<!DOCTYPE html>403", "ogg"))
        self.assertFalse(module.media_signature(b"\xff\xd8\xfftruncated", "jpeg"))

    def test_source_list_bounded_and_approved(self):
        allowed_hosts = {"canonn.science", module.HOST_CDN, "science.canonn.tech"}
        self.assertGreater(len(module.TARGETS), 0)
        self.assertLessEqual(len(module.TARGETS), 5)
        for target in module.TARGETS:
            self.assertTrue(set(target["hosts"]).issubset(allowed_hosts))
            self.assertTrue(target["paths"][0].startswith("/wp-content/uploads/"))
            self.assertTrue(target["filename"].rsplit(".", 1)[-1])
        self.assertLessEqual(module.MAX_ASSET_BYTES, 24 * 1024 * 1024)
        self.assertGreaterEqual(module.REQUEST_DELAY_SECONDS, 3)


if __name__ == "__main__":
    unittest.main()
