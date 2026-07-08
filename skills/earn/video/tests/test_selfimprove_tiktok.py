"""test_selfimprove_tiktok.py — REQ-LV-012 (video's TikTok engagement extension via yt-dlp).
_is_tiktok_url() dispatch + measure_tiktok() using an injected fake subprocess runner (mirrors
record_earn.py's onchain_check / record-payout.mjs's sigStatus injection-seam convention) so no
real yt-dlp process is spawned. parse_ytdlp_json itself (REQ-LV-003, frozen) is unit-tested
separately in skills/_shared/__tests__/test_ytdlp_parse.py — untouched here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from selfimprove import _is_tiktok_url, measure_tiktok  # noqa: E402

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


class _FakeProc:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


chk("_is_tiktok_url: tiktok.com URL -> True",
    _is_tiktok_url("https://www.tiktok.com/@user/video/123"), True)
chk("_is_tiktok_url: instagram URL -> False",
    _is_tiktok_url("https://www.instagram.com/reel/ABC/"), False)
chk("_is_tiktok_url: None -> False (never crash)", _is_tiktok_url(None), False)

# successful yt-dlp exit + valid JSON -> real views/likes extracted, ok=True
runner_ok = lambda args, **kw: _FakeProc(0, json.dumps({"view_count": 5000, "like_count": 300}))
m = measure_tiktok("https://www.tiktok.com/@user/video/1", "2026-07-08", runner=runner_ok)
chk("measure_tiktok: successful yt-dlp exit -> views extracted", m["views"], 5000)
chk("measure_tiktok: successful yt-dlp exit -> likes extracted", m["likes"], 300)
chk("measure_tiktok: successful yt-dlp exit -> comments stays None (not fabricated)", m["comments"], None)
chk("measure_tiktok: successful yt-dlp exit -> ok=True", m["ok"], True)
chk("measure_tiktok: measured_date carried through", m["measured_date"], "2026-07-08")
chk("measure_tiktok: url carried through", m["url"], "https://www.tiktok.com/@user/video/1")

# nonzero exit code (video removed/private) -> existence NOT confirmed, never fabricate a number
runner_fail = lambda args, **kw: _FakeProc(1, "")
m2 = measure_tiktok("https://www.tiktok.com/@user/video/2", "2026-07-08", runner=runner_fail)
chk("measure_tiktok: yt-dlp exit!=0 -> ok=False", m2["ok"], False)
chk("measure_tiktok: yt-dlp exit!=0 -> views None (not 0, not fabricated)", m2["views"], None)

# runner raises (timeout/binary missing) -> fail-soft, never crash the caller
runner_raises = lambda args, **kw: (_ for _ in ()).throw(FileNotFoundError("yt-dlp not found"))
m3 = measure_tiktok("https://www.tiktok.com/@user/video/3", "2026-07-08", runner=runner_raises)
chk("measure_tiktok: runner raises -> ok=False, no crash", m3["ok"], False)

# exit 0 but malformed JSON (yt-dlp partial output) -> parse_ytdlp_json's own fail-soft applies
runner_malformed = lambda args, **kw: _FakeProc(0, "{not valid json")
m4 = measure_tiktok("https://www.tiktok.com/@user/video/4", "2026-07-08", runner=runner_malformed)
chk("measure_tiktok: malformed JSON -> ok=False, views None", (m4["ok"], m4["views"]), (False, None))

print(f"=== test_selfimprove_tiktok: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
