#!/usr/bin/env python3
"""course-register.py — Procedure D verified 2026-05-08.

Drives `agent-{{profile.lateness.stakeholders.channel}}` CLI to register courses from
~/.openclaw/state/naist/<slug>/preferences.json into {{profile.education.institution}} UNIPA Kmd004 form.
Submission is real and durable (server-side persisted).

Verified path (matches SKILL.md Procedure D step-by-step):
  1. Procedure A + B (login)
  2. menu 履修登録 (link, not menuitem)
  3. tab 「授業コードを直接入力」
  4. for each code in preferences.json::recommended_courses[].code:
        fill textbox with code → click 追加
  5. click 「9最終確認へ」 (button accessibility name has "9" icon prefix)
  6. click 「9提出」 (id=funcForm:submit)
  7. confirm dialog: click OK (id=yes)
  8. verify body contains "履修登録が完了しました。"

Window-gated by preferences.json::enrollment_window_{start,end}.
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
APPLY = os.environ.get("COURSE_REGISTER_APPLY", "false").lower() == "true"
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"
AB = "/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"


def fail(msg: str) -> None:
    print(f"course-register[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def ab(args: list[str], timeout: int = 60) -> str:
    r = subprocess.run([AB, *args], capture_output=True, text=True, timeout=timeout)
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
    channel = ch_path.read_text().strip() if ch_path.exists() else "{{profile.channels.reportChannel}}"
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
        fail("oathtool not installed (brew install oath-toolkit)")
    r = subprocess.run(["oathtool", "--totp", "-b", secret], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"oathtool failed: {r.stderr}")
    return r.stdout.strip()


def find_ref_re(snap: str, regex: str) -> str | None:
    rx = re.compile(regex)
    for line in snap.splitlines():
        if rx.search(line):
            m = re.search(r"ref=(e\d+)", line)
            if m:
                return m.group(1)
    return None


def screenshot(label: str, ss_dir: Path) -> None:
    ss_dir.mkdir(parents=True, exist_ok=True)
    ab(["screenshot", str(ss_dir / f"{label}.png")])


def login_idp_and_sso(secrets: dict[str, str], ss_dir: Path) -> None:
    user = secrets.get("{{profile.education.institution}}_IDP_USERNAME") or secrets.get("{{profile.education.institution}}_EDU_USER")
    pwd = secrets.get("{{profile.education.institution}}_IDP_PASSWORD") or secrets.get("{{profile.education.institution}}_EDU_PASSWORD")
    totp_secret = secrets.get("{{profile.education.institution}}_TOTP_SECRET")
    if not all([user, pwd, totp_secret]):
        fail("missing {{profile.education.institution}}_IDP_USERNAME / PASSWORD / TOTP_SECRET")

    ab(["open", "https://idp.naist.jp/"])
    time.sleep(2)
    snap = ab(["snapshot"])
    user_ref = find_ref_re(snap, r'textbox')
    otp_ref = find_ref_re(snap, r'spinbutton')
    login_ref = find_ref_re(snap, r'button "ログイン"')
    if not (user_ref and otp_ref and login_ref):
        fail("OTP page elements not found")
    ab(["fill", f"@{user_ref}", user])
    ab(["fill", f"@{otp_ref}", gen_totp(totp_secret)])
    ab(["click", f"@{login_ref}"])
    time.sleep(3)
    screenshot("01-after-otp", ss_dir)

    snap2 = ab(["snapshot"])
    pwd_ref = find_ref_re(snap2, r'textbox')
    login2_ref = find_ref_re(snap2, r'button "ログイン"')
    if not (pwd_ref and login2_ref):
        fail("password page elements not found")
    ab(["fill", f"@{pwd_ref}", pwd])
    ab(["click", f"@{login2_ref}"])
    time.sleep(3)
    screenshot("02-after-pwd", ss_dir)

    url = ab_eval("location.href")
    if "/user/index.php" not in url:
        fail(f"IDP login failed; URL={url}")

    ab(["open", "https://edu-portal.naist.jp/uprx/up/km/kmh006/Kmh00601.xhtml"])
    time.sleep(2)
    snap3 = ab(["snapshot"])
    login3_ref = find_ref_re(snap3, r'link "ログインはこちら"')
    if not login3_ref:
        fail("ログインはこちら link not found")
    ab(["click", f"@{login3_ref}"])
    time.sleep(5)
    screenshot("03-edu-portal-home", ss_dir)


def click_rishu_menu() -> None:
    snap = ab(["snapshot", "-i"])
    ref = find_ref_re(snap, r'link "履修登録"')
    if not ref:
        fail("履修登録 menu link not found")
    ab(["click", f"@{ref}"])
    time.sleep(5)


def click_chokusetsu_input_tab() -> None:
    snap = ab(["snapshot", "-i"])
    ref = find_ref_re(snap, r'tab "授業コードを直接入力"')
    if not ref:
        fail("授業コードを直接入力 tab not found")
    ab(["click", f"@{ref}"])
    time.sleep(2)


def add_one_course(code: str) -> bool:
    snap = ab(["snapshot", "-i"])
    tb_ref = find_ref_re(snap, r'textbox')
    btn_ref = find_ref_re(snap, r'button "追加"')
    if not (tb_ref and btn_ref):
        return False
    ab(["fill", f"@{tb_ref}", code])
    ab(["click", f"@{btn_ref}"])
    time.sleep(3)
    return True


def click_saishuu_kakunin() -> bool:
    snap = ab(["snapshot", "-i"])
    ref = find_ref_re(snap, r'button "9?最終確認へ"')
    if not ref:
        return False
    ab(["click", f"@{ref}"])
    time.sleep(5)
    return True


def click_teishutsu_then_ok() -> bool:
    snap = ab(["snapshot", "-i"])
    submit_ref = find_ref_re(snap, r'button "9?提出"')
    if not submit_ref:
        return False
    ab(["click", f"@{submit_ref}"])
    time.sleep(4)
    snap2 = ab(["snapshot", "-i"])
    ok_ref = find_ref_re(snap2, r'button "OK"')
    if not ok_ref:
        return False
    ab(["click", f"@{ok_ref}"])
    time.sleep(6)
    return True


def verify_completion() -> tuple[bool, str]:
    body = ab_eval("document.body.innerText")
    completed = "履修登録が完了しました" in body
    return completed, body[:1000]


def main() -> int:
    if not SLUG:
        fail("SLUG env required")

    pref_path = STATE_ROOT / SLUG / "preferences.json"
    if not pref_path.exists():
        slack_post(f":warning: course-register[{SLUG}]: preferences.json missing — skip")
        return 0
    prefs = json.loads(pref_path.read_text())

    today = date.today().isoformat()
    win_s = prefs.get("enrollment_window_start", "")
    win_e = prefs.get("enrollment_window_end", "")
    if win_s and today < win_s:
        print(f"course-register[{SLUG}]: outside window (now={today} < start={win_s}) — skip")
        return 0
    if win_e and today > win_e:
        print(f"course-register[{SLUG}]: outside window (now={today} > end={win_e}) — skip")
        return 0

    recs = prefs.get("recommended_courses", [])
    if not recs:
        slack_post(f":warning: course-register[{SLUG}]: recommended_courses empty")
        return 0

    secrets = load_secrets()
    out_dir = WORKSPACE / SLUG
    ss_dir = out_dir / "screenshots" / today / "course-register"
    ss_dir.mkdir(parents=True, exist_ok=True)

    history_path = out_dir / "register-history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []

    try:
        login_idp_and_sso(secrets, ss_dir)
        click_rishu_menu()
        screenshot("10-rishu-form", ss_dir)
        click_chokusetsu_input_tab()
        screenshot("11-chokusetsu-tab", ss_dir)

        added: list[dict] = []
        for r in recs:
            code = r["code"]
            ok = add_one_course(code)
            screenshot(f"12-after-add-{code}", ss_dir)
            added.append({"code": code, "added": ok})
            print(f"  [{code}] added={ok}")

        if not APPLY:
            slack_post(
                f":pencil2: course-register[{SLUG}] DRY (APPLY=false): added {sum(1 for a in added if a['added'])}/{len(recs)} "
                f"to selection — not submitted. Set COURSE_REGISTER_APPLY=true to commit."
            )
            history.append({"date": today, "applied": False, "added": added})
            history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2))
            return 0

        if not click_saishuu_kakunin():
            fail("最終確認へ button click failed")
        screenshot("13-saishuu-kakunin", ss_dir)

        if not click_teishutsu_then_ok():
            fail("提出 / OK click failed")
        screenshot("14-after-ok", ss_dir)

        completed, body = verify_completion()
        history.append({
            "date": today,
            "applied": True,
            "added": added,
            "completed": completed,
            "body_excerpt": body[:600],
        })
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2))

        if completed:
            codes = ", ".join(r["code"] for r in recs)
            slack_post(f":white_check_mark: course-register[{SLUG}]: 履修登録完了 — added {codes}")
        else:
            slack_post(f":warning: course-register[{SLUG}]: completion text missing — see {history_path}")
    finally:
        subprocess.run([AB, "close"], capture_output=True, timeout=10)

    return 0


if __name__ == "__main__":
    sys.exit(main())
