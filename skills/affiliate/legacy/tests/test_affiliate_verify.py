"""test_affiliate_verify.py — REQ-LV-014 wiring test. SHARED_LIB_DIR env var (set below, before
importing affiliate_verify) points the cross-repo ytdlp_parse import at the anicca worktree that
carries this feature's changes, so this test is portable regardless of which anicca checkout is on
disk. Injected `runner` (mirrors record_earn.py's onchain_check convention) means no real yt-dlp
process is spawned for the TikTok branch.
"""
import json
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
os.environ.setdefault("SHARED_LIB_DIR", os.path.join(_REPO_ROOT, "lib", "vendor", "ytdlp-parse-shared-lib"))
sys.path.insert(0, _HERE)
from affiliate_verify import _is_tiktok_url, verify_and_record  # noqa: E402

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


chk("_is_tiktok_url: tiktok URL -> True", _is_tiktok_url("https://www.tiktok.com/@x/video/1"), True)
chk("_is_tiktok_url: instagram URL -> False", _is_tiktok_url("https://www.instagram.com/p/ABC/"), False)

TMP = tempfile.mkdtemp()
out_path = os.path.join(TMP, "affiliate-metrics.jsonl")

# current reality: instagram post, existence already confirmed by run.sh's own tile-diff before
# this is called -> a non-empty url alone is the existence proof, views/commission honestly None
r = verify_and_record("https://www.instagram.com/p/ABC123/", out_path=out_path)
chk("instagram post: ok=True (existence proven by caller's tile-diff)", r["ok"], True)
chk("instagram post: views=None (yt-dlp method does not apply, never fabricated)", r["views"], None)
chk("instagram post: commission_jpy=None (per-post attribution genuinely impossible)", r["commission_jpy"], None)
chk("instagram post: slideshow_url carried through", r["slideshow_url"], "https://www.instagram.com/p/ABC123/")

# forward-compat: a real TikTok URL dispatches to the yt-dlp path (injected fake runner)
class _FakeProc:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout

runner_ok = lambda args, **kw: _FakeProc(0, json.dumps({"view_count": 4200, "like_count": 90}))
r2 = verify_and_record("https://www.tiktok.com/@x/video/2", out_path=out_path, runner=runner_ok)
chk("tiktok post: views extracted via yt-dlp+parse_ytdlp_json", r2["views"], 4200)
chk("tiktok post: ok=True", r2["ok"], True)

runner_fail = lambda args, **kw: _FakeProc(1, "")
r3 = verify_and_record("https://www.tiktok.com/@x/video/3", out_path=out_path, runner=runner_fail)
chk("tiktok post: yt-dlp exit!=0 -> ok=False, views None (never fabricated)", (r3["ok"], r3["views"]), (False, None))

with open(out_path) as f:
    lines = [json.loads(l) for l in f if l.strip()]
chk("all 3 rows appended to the metrics ledger", len(lines), 3)

print(f"=== test_affiliate_verify: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
