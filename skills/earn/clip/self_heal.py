#!/usr/bin/env python3
"""REQ-008: self-heal driver for $CLIP_PENDING_VERIFY clips.

Runs ONCE per wake (gated by the caller, e.g. clip-cli.sh, BEFORE new-content posting --
never blocks it regardless of its own outcome). Picks ONE clip -- the pending clip FILE
with the OLDEST (least-recently-attempted) mtime, a self-balancing round-robin: this
clip's mtime is touched on every unresolved attempt, so a permanently-stuck clip becomes
the MOST recently touched and a different clip is tried next wake.

Calls poster.py's --verify-only flag (SHARED-1 INV-4; replaces the retired
post_reel.py web-composer --verify-only mode with the same {"ok","reels"} contract) via
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
    # SHARED-1 (INV-4): poster_path now points at poster.py, which reads reels via the
    # instagrapi API (no browser DOM, no --video/--caption-file/--tid needed) -- tid/clip_mp4/
    # clip_txt are kept as params for call-site/test-stub compatibility but unused here.
    env = dict(os.environ)
    if cdp_port:
        env["CDP_PORT"] = str(cdp_port)
    out = subprocess.run(
        [python_bin, poster_path, "--handle", handle, "--verify-only"]
        + (["--port", str(cdp_port)] if cdp_port else []),
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
    # ★ FIXED after Phase 3 FIND-103 (structural_integrity): this wrapper used to independently
    # re-derive the ANICCA_INSTANCE path-suffix convention in Python, duplicating the SINGLE
    # canonical source (_instance_paths.sh) with no mechanism to keep the two in sync. run.sh has
    # ALREADY resolved $CLIP_PENDING_VERIFY/$CLIP_POSTED/$CLIP_LEDGER via `source
    # _instance_paths.sh` moments earlier in the SAME script — it now passes them here as explicit
    # CLI args instead of this wrapper re-deriving them. NO duplicate/drifting path logic remains. ★
    ap.add_argument("--pending-verify", required=True)
    ap.add_argument("--posted", required=True)
    ap.add_argument("--ledger", required=True)
    a = ap.parse_args()
    clip_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, clip_dir)
    home = os.path.expanduser("~")
    pending_verify = a.pending_verify
    posted = a.posted
    ledger = a.ledger
    # SHARED-1 (INV-4): poster.py replaces the retired post_reel.py web-composer poster.
    # It needs the instagrapi package, so it runs under the SAME dedicated venv the clip poster
    # uses (run.sh self-heals this venv before invoking self_heal.py) -- never the bare $PY used
    # to run this wrapper itself.
    poster_path = f"{os.path.dirname(clip_dir)}/marketing-engine/poster.py"
    insta_py = f"{home}/.cache/instagrapi-venv/bin/python"
    python_bin = insta_py if os.path.exists(insta_py) else sys.executable
    cdp_dir = f"{home}/.claude/skills/ig-account-create/scripts"
    sys.path.insert(0, cdp_dir)
    import cdp  # noqa: E402

    def _read_page_text(tid, href):
        cdp.navigate(tid, f"https://www.instagram.com{href}")
        time.sleep(4)
        return cdp.evaluate(tid, "(()=>document.body.innerText)()") or ""

    result = run_self_heal(
        pending_verify=pending_verify, posted=posted, ledger=ledger, handle=a.handle,
        poster_path=poster_path, python_bin=python_bin, tid=a.tid,
        read_page_text=_read_page_text, cdp_port=os.environ.get("CDP_PORT"), wake=a.wake,
    )
    print(json.dumps(result))
