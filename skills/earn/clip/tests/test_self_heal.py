#!/usr/bin/env python3
"""RED-phase unit/integration tests for self_heal.py (VCSDD Phase 2a, REQ-008/PROP-006/009).

self_heal.py does not exist yet -- this test MUST FAIL (ImportError) until Phase 2b.

Isolation: uses ANICCA_INSTANCE so this never touches the real queue/pending-verify/ledger.
Stubs the --verify-only subprocess call (via CLIP_POSTER_OVERRIDE, matching run.sh's existing
test-hook pattern) and monkeypatches self_heal's page-text reader (a small impure function
kept separate specifically so it can be swapped out here without a real browser).
"""
import json
import os
import subprocess
import sys
import time
import unittest

CLIP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLIP_DIR)

import self_heal  # noqa: E402


def _make_stub_poster(tmp_path, responses):
    """Writes a python stub that pops the next dict off `responses` each invocation."""
    stub = os.path.join(tmp_path, "stub_poster.py")
    resp_file = os.path.join(tmp_path, "stub_responses.json")
    with open(resp_file, "w") as f:
        json.dump(responses, f)
    with open(stub, "w") as f:
        f.write(f"""#!/usr/bin/env python3
import json, os, fcntl
resp_file = {resp_file!r}
lock_file = resp_file + ".lock"
with open(lock_file, "w") as lf:
    fcntl.flock(lf, fcntl.LOCK_EX)
    with open(resp_file) as rf:
        items = json.load(rf)
    item = items.pop(0)
    with open(resp_file, "w") as wf:
        json.dump(items, wf)
    fcntl.flock(lf, fcntl.LOCK_UN)
print(json.dumps(item))
""")
    return stub


class TestSelfHeal(unittest.TestCase):
    def setUp(self):
        self.instance = f"vcsdd-selfheal-test-{os.getpid()}-{int(time.time()*1000) % 100000}"
        env = dict(os.environ)
        env["ANICCA_INSTANCE"] = self.instance
        env.pop("EARN_LEDGER", None)
        out = subprocess.run(
            [os.path.join(CLIP_DIR, "_instance_paths_print.sh")] if False else ["bash", "-c",
             f'source "{CLIP_DIR}/_instance_paths.sh"; echo "$CLIP_PENDING_VERIFY|$CLIP_POSTED|$CLIP_LEDGER"'],
            env=env, capture_output=True, text=True,
        )
        self.pending_verify, self.posted, self.ledger = out.stdout.strip().split("|")
        os.makedirs(self.pending_verify, exist_ok=True)
        os.makedirs(self.posted, exist_ok=True)
        os.makedirs(os.path.dirname(self.ledger), exist_ok=True)
        self.tmp_path = self.pending_verify + "-tmp"
        os.makedirs(self.tmp_path, exist_ok=True)

    def tearDown(self):
        import shutil
        for p in (self.pending_verify, self.posted, self.tmp_path):
            shutil.rmtree(p, ignore_errors=True)
        if os.path.exists(self.ledger):
            os.remove(self.ledger)

    def _write_pending_clip(self, name, before_hrefs, token):
        mp4 = os.path.join(self.pending_verify, f"{name}.mp4")
        txt = os.path.join(self.pending_verify, f"{name}.txt")
        sidecar = os.path.join(self.pending_verify, f"{name}.before-hrefs.json")
        with open(mp4, "w") as f: f.write("fake")
        with open(txt, "w") as f: f.write("caption")
        with open(sidecar, "w") as f: json.dump({"before_hrefs": before_hrefs, "token": token}, f)
        return mp4

    def test_resolves_when_token_matches_new_href(self):
        stub = _make_stub_poster(self.tmp_path, [
            {"reels": ["/h/reel/A/"], "ok": True},
            {"reels": ["/h/reel/A/", "/h/reel/NEW/"], "ok": True},
            {"reels": ["/h/reel/A/", "/h/reel/NEW/"], "ok": True},
        ])
        self._write_pending_clip("clip1", ["/h/reel/A/"], "#cabc1234de")
        result = self_heal.run_self_heal(
            pending_verify=self.pending_verify, posted=self.posted, ledger=self.ledger,
            handle="h", poster_path=stub, python_bin=sys.executable, tid="fake-tid",
            read_page_text=lambda tid, href: "some caption text ...#cabc1234de... #hashtags" if href == "/h/reel/NEW/" else "unrelated",
        )
        self.assertEqual(result["status"], "resolved")
        self.assertTrue(os.path.exists(os.path.join(self.posted, "clip1.mp4")))
        self.assertTrue(os.path.exists(os.path.join(self.posted, "clip1.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.pending_verify, "clip1.before-hrefs.json")))
        with open(self.ledger) as f:
            ledger_line = json.loads(f.readline())
        self.assertEqual(ledger_line["status"], "posted")
        self.assertIn("/h/reel/NEW/", ledger_line["post_url"])

    def test_no_new_href_stays_pending_and_touches_mtime(self):
        stub = _make_stub_poster(self.tmp_path, [
            {"reels": ["/h/reel/A/"], "ok": True},
            {"reels": ["/h/reel/A/"], "ok": True},
        ])
        clip_path = self._write_pending_clip("clip2", ["/h/reel/A/"], "#cdef5678ab")
        old_mtime = 1000000000.0
        os.utime(clip_path, (old_mtime, old_mtime))
        result = self_heal.run_self_heal(
            pending_verify=self.pending_verify, posted=self.posted, ledger=self.ledger,
            handle="h", poster_path=stub, python_bin=sys.executable, tid="fake-tid",
            read_page_text=lambda tid, href: "unrelated",
        )
        self.assertEqual(result["status"], "still-pending")
        self.assertTrue(os.path.exists(clip_path))
        self.assertGreater(os.path.getmtime(clip_path), old_mtime, "clip file mtime must be touched")

    def test_missing_sidecar_is_permanently_inconclusive_no_placeholder_no_crash(self):
        mp4 = os.path.join(self.pending_verify, "clip3.mp4")
        with open(mp4, "w") as f: f.write("fake")
        old_mtime = 1000000000.0
        os.utime(mp4, (old_mtime, old_mtime))
        result = self_heal.run_self_heal(
            pending_verify=self.pending_verify, posted=self.posted, ledger=self.ledger,
            handle="h", poster_path="unused", python_bin=sys.executable, tid="fake-tid",
            read_page_text=lambda tid, href: "",
        )
        self.assertEqual(result["status"], "inconclusive")
        self.assertTrue(os.path.exists(mp4), "clip must not be deleted")
        self.assertFalse(os.path.exists(os.path.join(self.pending_verify, "clip3.before-hrefs.json")),
                          "no placeholder sidecar must ever be created")
        self.assertGreater(os.path.getmtime(mp4), old_mtime, "clip file mtime must be touched even for missing sidecar")

    def test_round_robin_picks_oldest_clip_file_mtime(self):
        clip_a = self._write_pending_clip("clipA", ["/h/reel/X/"], "#c1111111111")
        clip_b = self._write_pending_clip("clipB", ["/h/reel/Y/"], "#c2222222222")
        os.utime(clip_a, (2000000000.0, 2000000000.0))  # newer
        os.utime(clip_b, (1000000000.0, 1000000000.0))  # older -- should be picked
        stub = _make_stub_poster(self.tmp_path, [
            {"reels": ["/h/reel/Y/"], "ok": True},
            {"reels": ["/h/reel/Y/"], "ok": True},
        ])
        result = self_heal.run_self_heal(
            pending_verify=self.pending_verify, posted=self.posted, ledger=self.ledger,
            handle="h", poster_path=stub, python_bin=sys.executable, tid="fake-tid",
            read_page_text=lambda tid, href: "unrelated",
        )
        self.assertEqual(result["picked"], "clipB", "must pick the OLDER (least-recently-attempted) clip file")
        # clipA's mtime untouched (not attempted this wake)
        self.assertEqual(os.path.getmtime(clip_a), 2000000000.0)


if __name__ == "__main__":
    unittest.main()
