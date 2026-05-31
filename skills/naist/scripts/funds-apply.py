#!/usr/bin/env python3
"""funds-apply.py — Procedure F end-to-end.

For each funder in ~/.openclaw/skills/naist/funders.json:
  - Skip unless `<creds_env_user>` and `<creds_env_password>` are both set in
    secrets.env / ~/.openclaw/.env.
  - Skip unless research-profile.json has all of {topic, method,
    preliminary_results} populated (i.e. no "TBD").
  - agent-browser open login URL, fill creds, click Login button.
  - Click "新規応募" / "Apply" link.
  - Fill text fields from research-profile.
  - Upload Quarto-rendered proposal.pdf.
  - Click "提出する" / "Submit".
  - Capture confirmation text + screenshot.
  - Append to fund-applications-history.json.

Phase 0 testbed: typically only `naist-internal` will have credentials at
first; the others (JSPS / JST / OpenPhil / FLI) need user-supplied creds.

If no funder is application-ready, exit 0 with a Slack note listing the
blocking conditions per funder, so the user can fill what's missing.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

SLUG = os.environ.get("SLUG", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "naist"
AB = "/opt/homebrew/bin/agent-browser"


def fail(msg: str) -> None:
    print(f"funds-apply[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def ab(args: list[str]) -> str:
    r = subprocess.run([AB, *args], capture_output=True, text=True, timeout=60)
    return r.stdout


def ab_eval(js: str) -> str:
    out = ab(["eval", js]).strip()
    if out.startswith('"') and out.endswith('"'):
        out = json.loads(out)
    return out


def slack_post(text: str) -> None:
    if DRY_RUN or not SLACK_TOKEN:
        print(f"[DRY] Slack: {text[:200]}")
        return
    ch_path = STATE_ROOT / SLUG / "slack_channel.txt"
    channel = ch_path.read_text().strip() if ch_path.exists() else os.environ.get("SLACK_FALLBACK_CHANNEL", "")
    import urllib.request
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception as e:
        print(f"slack_post error: {e}", file=sys.stderr)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for p in (Path.home() / ".openclaw" / ".env", STATE_ROOT / SLUG / "secrets.env"):
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def has_research_profile(slug: str) -> tuple[bool, list[str]]:
    p = STATE_ROOT / slug / "research-profile.json"
    if not p.exists():
        return False, ["research-profile.json missing"]
    try:
        prof = json.loads(p.read_text())
    except Exception as e:
        return False, [f"research-profile.json invalid: {e}"]
    missing = []
    for k in ("topic", "method", "preliminary_results"):
        v = prof.get(k, "")
        if not v or "TBD" in str(v).upper():
            missing.append(k)
    return (not missing), missing


def get_proposal_pdf(slug: str) -> Path | None:
    pdfs = sorted((WORKSPACE / slug / "proposals").rglob("proposal.pdf"))
    return pdfs[-1] if pdfs else None


def click_text(label: str) -> bool:
    js = f"""(function(){{
  const all = Array.from(document.querySelectorAll('a, button, input[type="submit"], input[type="button"]'));
  const target = all.find(el => (el.innerText || el.value || '').trim() === {json.dumps(label)});
  if (!target) return false;
  target.click();
  return true;
}})()"""
    out = ab_eval(js)
    return out in ("true", True)


def fill_selector(selector: str, value: str) -> bool:
    js = f"""(function(){{
  const el = document.querySelector({json.dumps(selector)});
  if (!el) return false;
  el.focus();
  el.value = {json.dumps(value)};
  el.dispatchEvent(new Event('input', {{bubbles: true}}));
  el.dispatchEvent(new Event('change', {{bubbles: true}}));
  return true;
}})()"""
    out = ab_eval(js)
    return out in ("true", True)


def submit_one(funder: dict, env: dict[str, str], profile: dict, pdf_path: Path, ss_dir: Path) -> dict:
    fid = funder["id"]
    sel = funder.get("selectors", {})
    user_env = funder.get("credentials_env", {}).get("user")
    pass_env = funder.get("credentials_env", {}).get("password")
    user = env.get(user_env or "")
    pwd = env.get(pass_env or "")
    if not (user and pwd):
        return {"funder": fid, "status": "skip", "reason": f"creds missing: {user_env}/{pass_env}"}

    ab(["open", funder["login_url"]])
    time.sleep(4)
    ab(["screenshot", str(ss_dir / f"01-{fid}-login.png")])

    if sel.get("username_input"):
        fill_selector(sel["username_input"], user)
    if sel.get("password_input"):
        fill_selector(sel["password_input"], pwd)
    label = sel.get("login_button_text", "ログイン")
    if not click_text(label):
        return {"funder": fid, "status": "skip", "reason": f"login button {label!r} not found"}
    time.sleep(5)
    ab(["screenshot", str(ss_dir / f"02-{fid}-after-login.png")])

    new_label = sel.get("new_application_link_text", "新規応募")
    if not click_text(new_label):
        return {"funder": fid, "status": "skip", "reason": f"{new_label!r} not found"}
    time.sleep(5)

    if sel.get("topic_textarea"):
        fill_selector(sel["topic_textarea"], profile.get("topic", ""))
    if sel.get("abstract_textarea"):
        fill_selector(sel["abstract_textarea"], profile.get("preliminary_results", ""))
    if sel.get("method_textarea"):
        fill_selector(sel["method_textarea"], profile.get("method", ""))

    if sel.get("file_upload_selector"):
        ab(["upload", sel["file_upload_selector"], str(pdf_path)])
        time.sleep(2)
    ab(["screenshot", str(ss_dir / f"03-{fid}-form-filled.png")])

    submit_label = sel.get("submit_button_text", "提出する")
    if not click_text(submit_label):
        return {"funder": fid, "status": "skip", "reason": f"submit button {submit_label!r} not found"}
    time.sleep(8)
    ab(["screenshot", str(ss_dir / f"04-{fid}-submitted.png")])

    confirm = ab_eval("document.body.innerText.substring(0, 800)")
    return {"funder": fid, "status": "submitted", "confirmation_excerpt": confirm[:600]}


def main() -> int:
    if not SLUG:
        fail("SLUG env required")
    today = date.today().isoformat()
    out_dir = WORKSPACE / SLUG
    ss_dir = out_dir / "screenshots" / today / "funds-apply"
    ss_dir.mkdir(parents=True, exist_ok=True)

    env = load_env()
    funders = json.loads((SKILL_DIR / "funders.json").read_text())["funders"]

    profile_ready, missing = has_research_profile(SLUG)
    if not profile_ready:
        slack_post(
            f":warning: funds-apply[{SLUG}] blocked — research-profile.json fields missing: {', '.join(missing)}"
        )
        return 0

    profile = json.loads((STATE_ROOT / SLUG / "research-profile.json").read_text())
    pdf = get_proposal_pdf(SLUG)
    if not pdf:
        slack_post(
            f":warning: funds-apply[{SLUG}] blocked — proposal.pdf missing. "
            f"Run `MODE=research-proposal-gen bash ~/.openclaw/skills/naist/scripts/run.sh` first."
        )
        return 0

    eligible = []
    blocked = []
    for f in funders:
        u = f.get("credentials_env", {}).get("user")
        p_ = f.get("credentials_env", {}).get("password")
        if env.get(u or "") and env.get(p_ or ""):
            eligible.append(f)
        else:
            blocked.append((f["id"], f"{u}/{p_}"))

    results: list[dict] = []
    if eligible:
        try:
            for f in eligible:
                results.append(submit_one(f, env, profile, pdf, ss_dir))
        finally:
            subprocess.run([AB, "close"], capture_output=True, timeout=10)
    else:
        results = [{"status": "skip", "reason": "no funder credentials in env"}]

    history = out_dir / "fund-applications-history.json"
    h = json.loads(history.read_text()) if history.exists() else []
    h.append({"date": today, "eligible": [f["id"] for f in eligible], "blocked": blocked, "results": results})
    history.write_text(json.dumps(h, ensure_ascii=False, indent=2))

    submitted = sum(1 for r in results if r.get("status") == "submitted")
    msg = (
        f":moneybag: funds-apply[{SLUG}]: eligible={len(eligible)} submitted={submitted} "
        f"blocked={len(blocked)} ({', '.join(b[0] for b in blocked) or 'none'})"
    )
    slack_post(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
