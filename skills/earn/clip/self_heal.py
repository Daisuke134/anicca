#!/usr/bin/env python3
"""REQ-008: self-heal driver for $CLIP_PENDING_VERIFY clips.

Runs ONCE per wake (gated by the caller, e.g. clip-cli.sh, BEFORE new-content posting --
never blocks it regardless of its own outcome). Picks ONE clip -- the pending clip FILE
with the OLDEST (least-recently-attempted) mtime, a self-balancing round-robin: this
clip's mtime is touched on every unresolved attempt, so a permanently-stuck clip becomes
the MOST recently touched and a different clip is tried next wake.

Reuses the EXISTING post_reel.py --verify-only flag (no new subprocess mechanism) via
reel_verify.stabilize_reads, then confirms via reel_verify.select_confirmed_href's exact
substring token match -- never hook/caption prose (HARD RULE 0.18: proven hook text is
deliberately reused verbatim across clips, so prose-matching is structurally unsound here).
"""
import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_verify  # noqa: E402


def _pick_oldest_clip(pending_verify):
    clips = glob.glob(os.path.join(pending_verify, "*.mp4"))
    if not clips:
        return None
    return min(clips, key=os.path.getmtime)


def _read_sidecar(pending_verify, clip_base):
    path = os.path.join(pending_verify, f"{clip_base}.before-hrefs.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            d = json.load(f)
        if "before_hrefs" not in d or "token" not in d:
            return None
        return d
    except Exception:
        return None


def _call_verify_only(poster_path, python_bin, handle, tid, clip_mp4, clip_txt, cdp_port=None):
    env = dict(os.environ)
    if cdp_port:
        env["CDP_PORT"] = str(cdp_port)
    out = subprocess.run(
        [python_bin, poster_path, "--video", clip_mp4, "--caption-file", clip_txt,
         "--handle", handle, "--verify-only", "--tid", tid],
        capture_output=True, text=True, env=env,
    )
    try:
        d = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {}
    except Exception:
        d = {}
    return d.get("reels") if d.get("ok") else None


def run_self_heal(pending_verify, posted, ledger, handle, poster_path, python_bin, tid,
                   read_page_text, cdp_port=None, wake=None):
    """Returns {"status": "empty"|"inconclusive"|"still-pending"|"resolved", "picked": <clip_base or None>}."""
    clip_mp4 = _pick_oldest_clip(pending_verify)
    if clip_mp4 is None:
        return {"status": "empty", "picked": None}
    clip_base = os.path.basename(clip_mp4)[:-len(".mp4")]
    clip_txt = os.path.join(pending_verify, f"{clip_base}.txt")

    sidecar = _read_sidecar(pending_verify, clip_base)
    if sidecar is None:
        # REQ-008 step 3: permanently inconclusive, NO placeholder sidecar, no crash, no delete.
        os.utime(clip_mp4, None)
        return {"status": "inconclusive", "picked": clip_base}

    before_hrefs = sidecar["before_hrefs"]
    token = sidecar["token"]

    def _read_fn():
        return _call_verify_only(poster_path, python_bin, handle, tid, clip_mp4, clip_txt, cdp_port) or []

    stable = reel_verify.stabilize_reads(_read_fn, max_reads=3, settle_s=5)
    if not stable["stable"]:
        os.utime(clip_mp4, None)
        return {"status": "still-pending", "picked": clip_base}

    new_hrefs = [h for h in stable["hrefs"] if h not in set(before_hrefs)]
    if not new_hrefs:
        os.utime(clip_mp4, None)
        return {"status": "still-pending", "picked": clip_base}

    page_texts = {h: read_page_text(tid, h) for h in new_hrefs}
    confirmed = reel_verify.select_confirmed_href(new_hrefs, page_texts, token)
    if confirmed is None:
        os.utime(clip_mp4, None)
        return {"status": "still-pending", "picked": clip_base}

    # resolved: move clip+caption to posted, delete sidecar, append ledger status:posted line
    os.rename(clip_mp4, os.path.join(posted, f"{clip_base}.mp4"))
    if os.path.exists(clip_txt):
        os.rename(clip_txt, os.path.join(posted, f"{clip_base}.txt"))
    sidecar_path = os.path.join(pending_verify, f"{clip_base}.before-hrefs.json")
    if os.path.exists(sidecar_path):
        os.remove(sidecar_path)
    post_url = "https://www.instagram.com" + confirmed
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    line = {"slot": "earn/clip", "source": "ig-clip",
            "task": f"posted reel to @{handle}: {post_url} (confirmed via self-heal)",
            "status": "posted", "earn_usdc": 0, "cost_usdc": 0, "net_usdc": 0,
            "wake": wake, "post_url": post_url}
    with open(ledger, "a") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return {"status": "resolved", "picked": clip_base}


if __name__ == "__main__":
    # thin CLI wrapper for the real wake-time driver (clip-cli.sh calls this)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--tid", required=True)
    ap.add_argument("--wake", default=None)
    a = ap.parse_args()
    clip_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, clip_dir)
    _sfx = f"-{os.environ['ANICCA_INSTANCE']}" if os.environ.get("ANICCA_INSTANCE") else ""
    home = os.path.expanduser("~")
    pending_verify = f"{home}/clips/pending-verify{_sfx}"
    posted = f"{home}/clips/posted{_sfx}"
    ledger = os.environ.get("EARN_LEDGER") or f"{home}/.openclaw/state/clip-earn-ledger{_sfx}.jsonl"
    poster_path = f"{home}/.claude/skills/ig-reels-poster/scripts/post_reel.py"
    cdp_dir = f"{home}/.claude/skills/ig-account-create/scripts"
    sys.path.insert(0, cdp_dir)
    import cdp  # noqa: E402

    def _read_page_text(tid, href):
        cdp.navigate(tid, f"https://www.instagram.com{href}")
        time.sleep(4)
        return cdp.evaluate(tid, "(()=>document.body.innerText)()") or ""

    result = run_self_heal(
        pending_verify=pending_verify, posted=posted, ledger=ledger, handle=a.handle,
        poster_path=poster_path, python_bin=sys.executable, tid=a.tid,
        read_page_text=_read_page_text, wake=a.wake,
    )
    print(json.dumps(result))
