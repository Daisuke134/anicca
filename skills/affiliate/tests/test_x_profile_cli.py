from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "x_profile_cli.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("affiliate_x_profile_cli", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class XProfileCliTests(unittest.TestCase):
    def test_exact_profile_counts_never_expand_abbreviated_values(self):
        self.assertEqual(MODULE.exact_profile_count("1 フォロワー", "followers"), 1)
        self.assertEqual(MODULE.exact_profile_count("1,234 Followers", "followers"), 1234)
        self.assertEqual(MODULE.exact_profile_count("27 フォロー中", "following"), 27)
        self.assertIsNone(MODULE.exact_profile_count("1.2K Followers", "followers"))
        self.assertIsNone(MODULE.exact_profile_count("27 Following", "followers"))

    def test_exact_post_metrics_parse_official_labels_only(self):
        self.assertEqual(MODULE.exact_post_metric("3\n Views", "views"), 3)
        self.assertEqual(MODULE.exact_post_metric("0 Replies. Reply", "replies"), 0)
        self.assertEqual(MODULE.exact_post_metric("1 repost. Repost", "reposts"), 1)
        self.assertEqual(MODULE.exact_post_metric("2 Likes. Like", "likes"), 2)
        self.assertEqual(MODULE.exact_post_metric("0 Bookmarks. Bookmark", "bookmarks"), 0)
        self.assertIsNone(MODULE.exact_post_metric("1.2K Views", "views"))


if __name__ == "__main__":
    unittest.main()
