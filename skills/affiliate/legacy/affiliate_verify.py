#!/usr/bin/env python3
"""affiliate_verify.py — REQ-LV-014 existence+engagement verification for an affiliate loop post.

Ground truth (verified by reading run.sh this session): the CURRENT affiliate loop posts a carousel
to INSTAGRAM (existence already confirmed there by run.sh's own profile-tile-diff BEFORE this
script ever runs -- that check is unchanged/kept). REQ-LV-014's own text describes a TikTok
slideshow existence check via `yt-dlp --dump-json --skip-download <url>`'s exit code (HTTP 200
alone does not prove a real post) feeding the SAME frozen parse_ytdlp_json REQ-LV-012 already uses
(no duplicate implementation) -- wired here too, dispatched by URL host, so it activates
automatically the moment this loop (or a future variant) posts a real TikTok URL instead.

Appends ONE row to ~/.cloak/affiliate-metrics.jsonl: {ts, slideshow_url, views, commission_jpy, ok}
(REQ-LV-014's exact shape). `commission_jpy` is always null: measure_commission.py's own docstring
already documents that Amazon's dashboard exposes only an account-wide MONTHLY total with no
per-post breakdown, so attributing a specific post's commission is honestly impossible with this
data source -- never fabricated here either.

CLI: python3 affiliate_verify.py <url> [--out-path PATH]
"""
import argparse
import json
import os
import subprocess
import sys
import time

# in-repo vendored import (REQ-CEO-012 "vendored" fix / REQ-VENDOR-001: ytdlp-parse-shared-lib,
# tracked in skills.lock, materialized under lib/vendor/ by bin/sync-skills.sh). SHARED_LIB_DIR
# override lets a test point this at a different copy instead of the vendored one.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VENDORED_YTDLP_PARSE_DIR = os.path.join(_REPO_ROOT, "lib", "vendor", "ytdlp-parse-shared-lib")
sys.path.insert(0, os.environ.get("SHARED_LIB_DIR") or _VENDORED_YTDLP_PARSE_DIR)
from ytdlp_parse import parse_ytdlp_json  # noqa: E402 (REQ-LV-012/014 shared, frozen)

DEFAULT_OUT = os.path.expanduser("~/.cloak/affiliate-metrics.jsonl")


def _is_tiktok_url(url):
    return "tiktok.com" in (url or "")


def _run_ytdlp(args, **kw):
    return subprocess.run(args, **kw)


def verify_tiktok(url, yt_dlp_bin="yt-dlp", runner=None):
    """REQ-LV-014: existence = the yt-dlp subprocess's own exit code, values from the frozen
    parse_ytdlp_json. Fail-soft, never fabricates a view count."""
    run = runner or _run_ytdlp
    try:
        proc = run([yt_dlp_bin, "--dump-json", "--skip-download", url],
                   capture_output=True, text=True, timeout=60)
        ok_exit = proc.returncode == 0
    except Exception:
        ok_exit = False
        proc = None
    parsed = parse_ytdlp_json(proc.stdout) if (ok_exit and proc is not None) else {"view_count": None, "like_count": None}
    return {"views": parsed["view_count"], "ok": bool(ok_exit and parsed["view_count"] is not None)}


def verify_and_record(url, out_path=DEFAULT_OUT, runner=None):
    """Non-TikTok (current reality: Instagram) posts: existence was already confirmed by run.sh's
    own profile-tile diff before this is called, so a non-empty url IS the existence proof --
    views stay None (REQ-LV-014's yt-dlp method does not apply to Instagram, never fabricated)."""
    if _is_tiktok_url(url):
        v = verify_tiktok(url, runner=runner)
        views, ok = v["views"], v["ok"]
    else:
        views, ok = None, bool(url)

    record = {"ts": int(time.time()), "slideshow_url": url, "views": views, "commission_jpy": None, "ok": ok}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out-path", default=DEFAULT_OUT)
    a = ap.parse_args()
    print(json.dumps(verify_and_record(a.url, a.out_path), ensure_ascii=False))
