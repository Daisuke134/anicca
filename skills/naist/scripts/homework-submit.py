#!/usr/bin/env python3
"""homework-submit.py — Procedure E end-to-end.

Reads ~/.openclaw/workspace/naist/<slug>/drafts/<class-slug>/<thread-id>.json
draft files. Each draft has:
  {
    "submission_url": "https://edu-portal.naist.jp/.../...",  // OR null if missing
    "thread_id": "...",
    "subject": "...",
    "deadline": "YYYY-MM-DD",
    "submit_at": "YYYY-MM-DD",   // typically deadline - 1 day
    "pdf_path": "/abs/path/to/rendered/homework.pdf",
    "submitted": false
  }

For each draft where submit_at <= today AND submitted == false AND pdf_path
exists:
  1. Procedure A + B login.
  2. agent-browser open submission_url.
  3. find <input type=file> via aria-role search; upload pdf_path.
  4. find a "提出する" / "提出" / "Submit" button by visible text and click.
  5. capture confirmation page text + screenshot.
  6. update draft JSON: submitted=true, submission_id (from page), submitted_at.

Auto-submit per v1.5; no 👍 gate.
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
AB = "/opt/homebrew/bin/agent-browser"


def fail(msg: str) -> None:
    print(f"homework-submit[{SLUG}] FATAL: {msg}", file=sys.stderr)
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
        print(f"[DRY] Slack: {text[:160]}")
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


def load_secrets() -> dict[str, str]:
    secrets: dict[str, str] = {}
    for p in (STATE_ROOT / SLUG / "secrets.env", Path.home() / ".openclaw" / ".env"):
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            secrets.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return secrets


def gen_totp(secret: str) -> str:
    if not shutil.which("oathtool"):
        fail("oathtool not installed")
    r = subprocess.run(["oathtool", "--totp", "-b", secret], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"oathtool failed: {r.stderr}")
    return r.stdout.strip()


def find_button_ref(snap: str, label: str) -> str | None:
    for line in snap.splitlines():
        if f'button "{label}"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                return m.group(1)
    return None


def find_link_ref(snap: str, label: str) -> str | None:
    for line in snap.splitlines():
        if f'link "{label}"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                return m.group(1)
    return None


def find_ref_near(snap: str, term: str, kind: str) -> str | None:
    lines = snap.splitlines()
    for i, line in enumerate(lines):
        if f'term "{term}"' in line:
            for j in range(i + 1, min(i + 8, len(lines))):
                if kind in lines[j]:
                    m = re.search(r"ref=(e\d+)", lines[j])
                    if m:
                        return m.group(1)
    return None


def login_idp_and_sso(secrets: dict[str, str]) -> None:
    user = secrets.get("NAIST_IDP_USERNAME") or secrets.get("NAIST_EDU_USER")
    pwd = secrets.get("NAIST_IDP_PASSWORD") or secrets.get("NAIST_EDU_PASSWORD")
    totp_secret = secrets.get("NAIST_TOTP_SECRET")
    if not all([user, pwd, totp_secret]):
        fail("missing NAIST IDP credentials")
    ab(["open", "https://idp.naist.jp/"])
    time.sleep(2)
    snap = ab(["snapshot"])
    ab(["fill", f"@{find_ref_near(snap,'ユーザー名','textbox')}", user])
    ab(["fill", f"@{find_ref_near(snap,'ワンタイムパスワード','spinbutton')}", gen_totp(totp_secret)])
    ab(["click", f"@{find_button_ref(snap,'ログイン')}"])
    time.sleep(3)
    snap2 = ab(["snapshot"])
    ab(["fill", f"@{find_ref_near(snap2,'パスワード','textbox')}", pwd])
    ab(["click", f"@{find_button_ref(snap2,'ログイン')}"])
    time.sleep(3)


def js_upload_pdf(pdf_path: str) -> str:
    """Upload PDF via JS DataTransfer (PrimeFaces auto-upload triggers on change event).

    agent-browser's `upload` command writes to input.files via CDP but does NOT
    fire the change event that PrimeFaces' fileUpload widget listens for, so the
    auto-upload AJAX never runs and 確定 fails with "添付ファイルを選択してください".
    The reliable path is: read PDF → base64 → JS constructs File + DataTransfer
    → sets input.files → dispatches change event manually. Verified 2026-05-29
    against edu-portal.naist.jp PrimeFaces (NAIST UNIPA) for 3 distinct courses.
    """
    import base64 as b64mod
    b64 = b64mod.b64encode(Path(pdf_path).read_bytes()).decode()
    fname = Path(pdf_path).name
    js = (
        f'(async () => {{'
        f' const b64 = "{b64}";'
        f' const bin = atob(b64);'
        f' const bytes = new Uint8Array(bin.length);'
        f' for (let i=0; i<bin.length; i++) bytes[i] = bin.charCodeAt(i);'
        f' const blob = new Blob([bytes], {{type: "application/pdf"}});'
        f' const file = new File([blob], "{fname}", {{type: "application/pdf"}});'
        f' const dt = new DataTransfer();'
        f' dt.items.add(file);'
        f' const inp = document.querySelector("input[type=file]");'
        f' if (!inp) return "no-file-input";'
        f' inp.files = dt.files;'
        f' inp.dispatchEvent(new Event("change", {{bubbles: true}}));'
        f' return "uploaded-" + inp.files.length;'
        f'}})()'
    )
    return ab_eval(js)


def submit_one_draft(draft_path: Path, ss_dir: Path) -> dict:
    draft = json.loads(draft_path.read_text())
    if draft.get("submitted"):
        return {"draft": str(draft_path), "skipped": True, "reason": "already submitted"}
    pdf = draft.get("pdf_path")
    if not pdf or not Path(pdf).exists():
        return {"draft": str(draft_path), "skipped": True, "reason": "pdf missing"}
    url = draft.get("submission_url")
    if not url:
        return {"draft": str(draft_path), "skipped": True, "reason": "submission_url missing"}

    label = draft_path.stem

    ab(["open", url])
    time.sleep(5)
    landed = ab_eval("location.href")
    if "edu-portal.naist.jp" not in landed:
        return {"draft": str(draft_path), "skipped": True, "reason": f"navigation failed (url={landed})"}
    ab(["screenshot", str(ss_dir / f"01-form-{label}.png")])

    upload_result = js_upload_pdf(pdf)
    if "uploaded" not in upload_result:
        return {"draft": str(draft_path), "skipped": True, "reason": f"upload failed: {upload_result}"}
    time.sleep(6)
    ab(["screenshot", str(ss_dir / f"02-uploaded-{label}.png")])

    body_check = ab_eval(
        'JSON.stringify(document.body.innerText.match(/' + Path(pdf).stem + r'.{0,30}KB/g) || [])'
    )
    if "KB" not in body_check:
        return {"draft": str(draft_path), "skipped": True, "reason": f"file not visible after upload: {body_check}"}

    kakutei_result = ab_eval(
        '(()=>{const b = Array.from(document.querySelectorAll("button"))'
        '.find(x => x.textContent.trim() === "確定" && x.offsetParent !== null);'
        ' return b ? (b.click(), "kakutei-clicked") : "no-kakutei";})()'
    )
    if "no-kakutei" in kakutei_result:
        return {"draft": str(draft_path), "skipped": True, "reason": "確定 button not found"}
    time.sleep(4)

    ok_result = ab_eval(
        '(()=>{const ds = Array.from(document.querySelectorAll(".ui-confirm-dialog"));'
        ' const v = ds.find(d => getComputedStyle(d).display !== "none");'
        ' if (!v) return "no-dialog";'
        ' const ok = v.querySelector("button#yes, button.ui-confirmdialog-yes");'
        ' return ok ? (ok.click(), "OK-fired") : "no-ok";})()'
    )
    if "OK-fired" not in ok_result:
        return {"draft": str(draft_path), "skipped": True, "reason": f"OK dialog not handled: {ok_result}"}
    time.sleep(8)

    ab(["screenshot", str(ss_dir / f"03-submitted-{label}.png")])
    confirm = ab_eval("document.body.innerText.substring(0, 1200)")

    if "提出日時" not in confirm and "更新日時" not in confirm:
        return {"draft": str(draft_path), "skipped": True, "reason": "submission record fields missing after OK"}

    draft["submitted"] = True
    draft["submitted_at"] = date.today().isoformat()
    draft["submission_confirmation"] = confirm
    draft_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2))
    return {"draft": str(draft_path), "submitted": True, "confirmation_excerpt": confirm[:200]}


def main() -> int:
    if not SLUG:
        fail("SLUG env required")
    drafts_root = WORKSPACE / SLUG / "drafts"
    if not drafts_root.exists():
        print(f"homework-submit[{SLUG}]: no drafts dir at {drafts_root} — skip")
        return 0
    today = date.today().isoformat()
    candidates = [
        p for p in drafts_root.glob("**/*.json")
        if (json.loads(p.read_text()).get("submit_at", "") <= today)
        and not json.loads(p.read_text()).get("submitted")
    ]
    if not candidates:
        print(f"homework-submit[{SLUG}]: 0 drafts past submit_at — skip")
        return 0

    secrets = load_secrets()
    ss_dir = WORKSPACE / SLUG / "screenshots" / today / "homework-submit"
    ss_dir.mkdir(parents=True, exist_ok=True)

    try:
        login_idp_and_sso(secrets)
        results = [submit_one_draft(p, ss_dir) for p in candidates]
    finally:
        subprocess.run([AB, "close"], capture_output=True, timeout=10)

    out = WORKSPACE / SLUG / "homework-submit-history.json"
    h = json.loads(out.read_text()) if out.exists() else []
    h.append({"date": today, "results": results})
    out.write_text(json.dumps(h, ensure_ascii=False, indent=2))

    submitted = sum(1 for r in results if r.get("submitted"))
    slack_post(
        f":pencil: homework-submit[{SLUG}]: submitted={submitted}/{len(results)} drafts\n"
        f"history: `{out}`"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
