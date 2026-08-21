import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "lm-distribution" / "postiz_video.py"
SPEC = importlib.util.spec_from_file_location("postiz_video", MODULE_PATH)
postiz_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(postiz_video)


class PostizVideoTests(unittest.TestCase):
    def test_profile_only_post_falls_back_to_browser_caption_join(self):
        calls = []

        def browser(profile_url, caption, *, posted_after, caption_prefix):
            calls.append((profile_url, caption, posted_after, caption_prefix))
            return "https://www.tiktok.com/@honne_reveal/video/7676388327427149077"

        result = postiz_video.resolve_profile_release_url(
            "https://www.tiktok.com/@honne_reveal",
            "someone tell me\nthis is illegal",
            posted_after=1_777_000_000,
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""),
            browser_resolver=browser,
        )
        self.assertEqual(result, "https://www.tiktok.com/@honne_reveal/video/7676388327427149077")
        self.assertEqual(calls[0][0], "https://www.tiktok.com/@honne_reveal")
        self.assertEqual(calls[0][3], "someone tell me this is")


if __name__ == "__main__":
    unittest.main()
