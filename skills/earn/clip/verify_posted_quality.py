#!/usr/bin/env python3
"""verify_posted_quality.py — audit the quality of the last N POSTED clips against the
producer's own quality floor (1080x1920, >=2.5Mbps video bitrate), independent of the
verify_clip.sh pre-post gate. This catches drift the gate itself might miss (e.g. IG's own
re-encode, or a gate regression) by re-probing the local artifact AND attempting to read
IG's own delivered metadata via yt-dlp.

Read-only against the ledger and posted/ directory; APPEND-only against
~/.local/state/life-manager/state/clip-metrics.jsonl. Never edits or deletes anything. Idempotent: a
post_url already present in clip-metrics.jsonl is skipped on re-run.

Correspondence caveat (read before changing the pairing logic): the ledger's
`status: posted` rows carry a post_url but NO local filename and NO per-row timestamp, so
there is no key-based join available today between a ledger row and a file under
~/clips/posted/. This script pairs the latest N posted-status ledger rows with the latest N
*.mp4 files under ~/clips/posted/ by ORDINAL POSITION after independently sorting both by
their own chronological order (ledger: append order == chronological; posted/: file mtime).
Both the initial post (run.sh) and self_heal.py's resolved path move the clip into posted/
in the SAME code step that appends the matching ledger row, so the two orderings stay in
lockstep in practice. This is a heuristic, not a guaranteed match -- documented here so a
future editor does not assume it is exact.

Usage: python3 verify_posted_quality.py [N]   (default N=5)
"""
import datetime
import glob
import json
import os
import subprocess
import sys

HOME = os.path.expanduser("~")
LEDGER_PATH = os.path.join(HOME, ".openclaw", "state", "clip-earn-ledger.jsonl")
POSTED_DIR = os.path.join(HOME, "clips", "posted")
METRICS_PATH = os.path.join(HOME, ".openclaw", "state", "clip-metrics.jsonl")

WIDTH_FLOOR = 1080
HEIGHT_FLOOR = 1920
BITRATE_FLOOR = 2_500_000


def _load_posted_rows(ledger_path):
    """Read-only. Returns ledger rows with status=='posted' in file (== chronological)
    append order. Malformed lines are skipped, never raised."""
    rows = []
    try:
        with open(ledger_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("status") == "posted" and d.get("post_url"):
                    rows.append(d)
    except FileNotFoundError:
        pass
    return rows


def _already_recorded(metrics_path):
    seen = set()
    try:
        with open(metrics_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("post_url"):
                    seen.add(d["post_url"])
    except FileNotFoundError:
        pass
    return seen


def _ffprobe_local(path):
    """Return (width, height, video_bitrate_bps) for the LOCAL file, each None on
    failure. Prefers the per-stream video bit_rate; falls back to the container-level
    format bit_rate when the stream doesn't carry one."""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height,bit_rate", "-of", "json", path]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        d = json.loads(out.stdout or "{}")
        streams = d.get("streams") or []
        if not streams:
            return None, None, None
        s = streams[0]
        w, h = s.get("width"), s.get("height")
        vbr = s.get("bit_rate")
        if vbr in (None, "N/A"):
            cmd2 = ["ffprobe", "-v", "error", "-show_entries", "format=bit_rate",
                    "-of", "json", path]
            out2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
            d2 = json.loads(out2.stdout or "{}")
            vbr = (d2.get("format") or {}).get("bit_rate")
        return w, h, (int(vbr) if vbr not in (None, "N/A") else None)
    except Exception:
        return None, None, None


def _yt_dlp_ig_metadata(post_url):
    """Best-effort probe of the LIVE IG post via yt-dlp. Returns (width, height, tbr) where
    tbr is either a float (Mbps-ish yt-dlp `tbr` field) or a "none:<reason>" string. IG
    requires an authenticated session for yt-dlp to read reel metadata -- an
    unauthenticated/rate-limited failure is EXPECTED here and must be tolerated, never
    raised, since this script must never block or crash on IG-side auth state."""
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings", "-j", post_url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if out.returncode != 0 or not out.stdout.strip():
            err = (out.stderr or "").lower()
            if "login" in err or "rate" in err or "private" in err:
                return None, None, "none:ig-auth-missing"
            return None, None, "none:probe-failed"
        d = json.loads(out.stdout.strip().splitlines()[-1])
        tbr = d.get("tbr")
        return d.get("width"), d.get("height"), (tbr if tbr is not None else "none:no-tbr-field")
    except Exception:
        return None, None, "none:probe-exception"


def _pair_latest(posted_files, ledger_rows, n):
    """Ordinal pairing of the latest n items from each list (see module docstring)."""
    posted_tail = posted_files[-n:]
    ledger_tail = ledger_rows[-n:]
    k = min(len(posted_tail), len(ledger_tail))
    return list(zip(posted_tail[-k:], ledger_tail[-k:]))


def run(n=5, ledger_path=LEDGER_PATH, posted_dir=POSTED_DIR, metrics_path=METRICS_PATH):
    ledger_rows = _load_posted_rows(ledger_path)
    posted_files = sorted(glob.glob(os.path.join(posted_dir, "*.mp4")), key=os.path.getmtime)
    seen = _already_recorded(metrics_path)

    pairs = _pair_latest(posted_files, ledger_rows, n)
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

    written = []
    skipped = 0
    for local_path, row in pairs:
        post_url = row["post_url"]
        if post_url in seen:
            skipped += 1
            continue
        lw, lh, lvbr = _ffprobe_local(local_path)
        iw, ih, itbr = _yt_dlp_ig_metadata(post_url)
        below_floor = bool(
            lw is not None and lh is not None and lvbr is not None
            and (lw < WIDTH_FLOOR or lh < HEIGHT_FLOOR or lvbr < BITRATE_FLOOR)
        )
        metric_row = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "post_url": post_url,
            "local_file": os.path.basename(local_path),
            "local_w": lw, "local_h": lh, "local_vbitrate": lvbr,
            "ig_w": iw, "ig_h": ih, "ig_tbr": itbr,
            "below_floor": below_floor,
        }
        with open(metrics_path, "a") as f:
            f.write(json.dumps(metric_row, ensure_ascii=False) + "\n")
        written.append(metric_row)
    return {"written": written, "skipped_already_recorded": skipped,
            "posted_files_seen": len(posted_files), "ledger_posted_rows_seen": len(ledger_rows)}


if __name__ == "__main__":
    n_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    result = run(n=n_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))
