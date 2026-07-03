#!/usr/bin/env python3
"""PROP-004(c) regression test for Phase-3 FIND-100: post_reel.py must print its JSON result dict
EXACTLY ONCE per invocation (Ground Truth: "returns ONE json dict via print(json.dumps(res, ...))"),
and verify-only/DRY-ok paths must NEVER carry an added "outcome" key (Ground Truth: "verify-only-mode
return and DRY-ok are NOT failure paths... out of scope for the outcome vocabulary").

A prior revision's shared `finally:` block fired on EVERY early return (Python semantics: finally
always runs on any exit from try, including an explicit return) while EACH early-return site ALSO
printed -- causing every path to print twice, and injecting an unwanted outcome:"failed" key into
the verify-only/DRY-ok shapes specifically. Fixed by making every early-return site a bare `return`
(no print) and the finally block the SOLE print point, with verify-only/DRY-ok exempted from the
outcome-fallback.

Mocks post_reel's `cdp`/`ev`/`load_video_via_filechooser` dependencies (no real browser) to drive
each of the early-return code paths directly and capture stdout.
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

POST_REEL_PATH = os.path.expanduser("~/.claude/skills/ig-reels-poster/scripts")
sys.path.insert(0, POST_REEL_PATH)


def _run_post_reel(argv, ev_side_effect, verify_only_reels=None):
    """Imports post_reel fresh each time (module-level state), mocks its cdp dependency, runs
    main() with the given argv, and returns (stdout_lines, parsed_json_list)."""
    import importlib
    if "post_reel" in sys.modules:
        del sys.modules["post_reel"]
    with mock.patch.dict(os.environ, {"CDP_PORT": "9999"}):
        import post_reel  # noqa

    post_reel.cdp = mock.MagicMock()
    post_reel.cdp.new_tab.return_value = "fake-tid"
    post_reel.cdp.page_ws.return_value = "ws://fake"
    post_reel.ev = mock.MagicMock(side_effect=ev_side_effect)

    buf = io.StringIO()
    old_argv = sys.argv
    sys.argv = ["post_reel.py"] + argv
    try:
        with redirect_stdout(buf):
            post_reel.main()
    finally:
        sys.argv = old_argv

    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    parsed = []
    for ln in lines:
        try:
            parsed.append(json.loads(ln))
        except Exception:
            pass
    return lines, parsed


class TestSinglePrint(unittest.TestCase):
    def _mktemp_files(self):
        import tempfile
        video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        video.write(b"fake")
        video.close()
        cap = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False)
        cap.write("caption text")
        cap.close()
        return video.name, cap.name

    def test_not_logged_in_prints_exactly_once(self):
        video, cap = self._mktemp_files()
        # ev() call sequence: 1st call = "not logged in?" check -> True (not logged in)
        lines, parsed = _run_post_reel(
            ["--video", video, "--caption-file", cap, "--handle", "h", "--tid", "fake"],
            ev_side_effect=[True],
        )
        self.assertEqual(len(parsed), 1, f"expected exactly 1 JSON line, got {len(parsed)}: {lines}")
        self.assertEqual(parsed[0]["outcome"], "failed")
        self.assertEqual(parsed[0]["error"], "not logged in")

    def test_verify_only_prints_exactly_once_and_has_no_outcome_key(self):
        video, cap = self._mktemp_files()
        # ev() sequence: not-logged-in->False; dismiss-interstitial loop (breaks on label[0]
        # returning truthy, so only 1 call, not 5); account-guard active-handle->"h";
        # verify-only's reels read -> ["/h/reel/A/"]
        lines, parsed = _run_post_reel(
            ["--video", video, "--caption-file", cap, "--handle", "h", "--tid", "fake", "--verify-only"],
            ev_side_effect=[False, {"x": 1, "y": 1}, "h", ["/h/reel/A/"]],
        )
        self.assertEqual(len(parsed), 1, f"expected exactly 1 JSON line, got {len(parsed)}: {lines}")
        self.assertNotIn("outcome", parsed[0], "verify-only is out of scope for the outcome vocabulary (Ground Truth line 40)")
        self.assertEqual(parsed[0]["reached"], "verify-only")
        self.assertTrue(parsed[0]["ok"])

    def test_dry_ok_prints_exactly_once_and_has_no_outcome_key(self):
        video, cap = self._mktemp_files()
        with mock.patch.dict(sys.modules, clear=False):
            import importlib
            if "post_reel" in sys.modules:
                del sys.modules["post_reel"]
            import post_reel  # noqa
            post_reel.cdp = mock.MagicMock()
            post_reel.cdp.new_tab.return_value = "fake-tid"
            # ev() call sequence, in the EXACT order post_reel.py's main() invokes it for the
            # dry-mode (not --live) path -- traced by hand against the real file:
            #  1. not-logged-in check -> False
            #  2. dismiss-interstitial loop (up to 5 labels; a truthy 1st result breaks the loop
            #     immediately, so only 1 ev() call from this loop, not 5)
            #  3. account-guard active-handle check -> "h"
            #  4. create-post-button rect
            #  5. "投稿"/"Post" confirm-button rect (None -> skipped, harmless)
            #  6. video-loaded poll (`for _ in range(12)`, True on 1st iteration -> breaks)
            #  7. share-advance loop (`for i in range(7)`, share-button-visible check True on 1st
            #     iteration -> breaks immediately, before ever calling the OK-modal/next-button rects)
            #  8. caption textarea rect (None -> typing skipped, harmless for this test)
            #  9. share button rect
            # 10. (dry-mode only) discard-button rect (None -> click skipped, harmless)
            post_reel.ev = mock.MagicMock(side_effect=[
                False,                # 1
                {"x": 1, "y": 1},     # 2 (dismiss loop, breaks on label[0])
                "h",                  # 3
                {"x": 1, "y": 1},     # 4 (create button)
                None,                 # 5 (post confirm button, not found -> skipped)
                True,                 # 6 (video-loaded poll)
                True,                 # 7 (share-advance loop breaks immediately)
                None,                 # 8 (caption textarea not found -> typing skipped)
                {"x": 1, "y": 1},     # 9 (share button)
                None,                 # 10 (discard button not found -> click skipped)
            ])
            post_reel.load_video_via_filechooser = mock.MagicMock(return_value=True)
            post_reel.shot = mock.MagicMock(return_value="/tmp/fake.png")
            # PROP-004(c): dry mode (no --live) must trigger ZERO new REQ-001/002 behavior --
            # explicit call-count assertion, not merely inferred from the ev() mock not
            # exhausting early (which the sequence above already implicitly guarantees, but this
            # makes the "no stabilize_reads call in dry mode" claim directly, unambiguously provable).
            with mock.patch.object(post_reel.reel_verify, "stabilize_reads") as mock_stabilize:
                buf = io.StringIO()
                old_argv = sys.argv
                sys.argv = ["post_reel.py", "--video", video, "--caption-file", cap, "--handle", "h", "--tid", "fake"]
                try:
                    with redirect_stdout(buf):
                        post_reel.main()
                finally:
                    sys.argv = old_argv
                mock_stabilize.assert_not_called()
            lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
            parsed = [json.loads(ln) for ln in lines]
        self.assertEqual(len(parsed), 1, f"expected exactly 1 JSON line, got {len(parsed)}: {lines}")
        self.assertNotIn("outcome", parsed[0], "DRY-ok is out of scope for the outcome vocabulary (Ground Truth line 40)")
        self.assertEqual(parsed[0]["reached"], "DRY-ok")


if __name__ == "__main__":
    unittest.main()
