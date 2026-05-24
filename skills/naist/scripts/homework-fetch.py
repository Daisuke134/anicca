#!/usr/bin/env python3
"""homework-fetch.py — Procedure G end-to-end (read-only).

Logs into {{profile.education.institution}} IDP → SSO into edu-portal → opens 期限あり tab on the home
calendar → clicks every homework deadline link → scrapes the 課題提出 detail
page for each one → posts a structured summary to Slack and saves a JSON
snapshot per slug.

This is the READ-ONLY companion to homework-submit.py. It just fetches the
content so the user (or downstream skills) can see what's due, without
submitting anything.

Output:
  ~/.openclaw/workspace/naist/<slug>/homework-<ymd>.json
  Slack post to channel from state/naist/<slug>/slack_channel.txt
  Screenshots in workspace/naist/<slug>/screenshots/<ymd>/homework/*.png

Required env (loaded from secrets.env + ~/.openclaw/.env):
  SLUG                     — per-user slug (e.g. "dais")
  {{profile.education.institution}}_IDP_USERNAME / {{profile.education.institution}}_EDU_USER
  {{profile.education.institution}}_IDP_PASSWORD / {{profile.education.institution}}_EDU_PASSWORD
  {{profile.education.institution}}_TOTP_SECRET
  SLACK_BOT_TOKEN (optional — DRY_RUN if unset)

Exit codes: 0 ok, 1 fatal (login/nav failure)
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
AB = (
    os.environ.get("AGENT_BROWSER_BIN")
    or shutil.which("agent-{{profile.lateness.stakeholders.channel}}")
    or "/opt/homebrew/bin/agent-{{profile.lateness.stakeholders.channel}}"
)

IDP_URL = "https://idp.naist.jp/"
EDU_PORTAL_ENTRY = "https://edu-portal.naist.jp/uprx/up/km/kmh006/Kmh00601.xhtml"
EDU_PORTAL_HOME = "https://edu-portal.naist.jp/uprx/up/pk/pky001/Pky00102.xhtml"


def fail(msg: str, code: int = 1) -> None:
    print(f"homework-fetch[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def ab(args: list[str], timeout: int = 60) -> str:
    r = subprocess.run([AB, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"  ab {' '.join(args)} rc={r.returncode}\n  stderr: {r.stderr[:300]}", file=sys.stderr)
    return r.stdout


def ab_eval(js: str) -> str:
    out = ab(["eval", js])
    s = out.strip()
    if s.startswith('"') and s.endswith('"'):
        s = json.loads(s)
    return s


def slack_post(text: str) -> None:
    if DRY_RUN:
        print(f"[DRY] Slack: {text[:200]}")
        return
    if not SLACK_TOKEN:
        print("warn: SLACK_BOT_TOKEN not set — skipping Slack post", file=sys.stderr)
        print(f"[no-token] Slack: {text[:200]}")
        return
    ch_path = STATE_ROOT / SLUG / "slack_channel.txt"
    if not ch_path.exists():
        print(f"warn: no slack_channel.txt at {ch_path}, skipping post", file=sys.stderr)
        return
    channel = ch_path.read_text().strip()
    import urllib.request
    payload = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_TOKEN}", "Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        if not body.get("ok"):
            print(f"  slack post failed: {body}", file=sys.stderr)


def load_secrets() -> dict[str, str]:
    secrets: dict[str, str] = {}
    for p in [STATE_ROOT / SLUG / "secrets.env", Path.home() / ".openclaw" / ".env"]:
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
        fail("oathtool not installed. brew install oath-toolkit")
    r = subprocess.run(["oathtool", "--totp", "-b", secret], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"oathtool failed: {r.stderr}")
    return r.stdout.strip()


def find_ref_near(snapshot: str, term: str, kind: str) -> str | None:
    lines = snapshot.splitlines()
    for i, line in enumerate(lines):
        if f'term "{term}"' in line:
            for j in range(i + 1, min(i + 8, len(lines))):
                if kind in lines[j]:
                    m = re.search(r"ref=(e\d+)", lines[j])
                    if m:
                        return m.group(1)
    return None


def find_button_ref(snapshot: str, label: str) -> str | None:
    for line in snapshot.splitlines():
        if f'button "{label}"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                return m.group(1)
    return None


def find_link_ref(snapshot: str, label: str) -> str | None:
    for line in snapshot.splitlines():
        if f'link "{label}"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                return m.group(1)
    return None


def screenshot(label: str, ss_dir: Path) -> None:
    ss_dir.mkdir(parents=True, exist_ok=True)
    ab(["screenshot", str(ss_dir / f"{label}.png")])


def procedure_a_login(secrets: dict[str, str], ss_dir: Path) -> None:
    """IDP login: TOTP → password → SSO redirect. Skips if already logged in."""
    user = secrets.get("{{profile.education.institution}}_IDP_USERNAME") or secrets.get("{{profile.education.institution}}_EDU_USER")
    pwd = secrets.get("{{profile.education.institution}}_IDP_PASSWORD") or secrets.get("{{profile.education.institution}}_EDU_PASSWORD")
    totp_secret = secrets.get("{{profile.education.institution}}_TOTP_SECRET")
    if not all([user, pwd, totp_secret]):
        fail("missing {{profile.education.institution}}_IDP_USERNAME / PASSWORD / TOTP_SECRET in secrets")

    ab(["open", IDP_URL])
    time.sleep(2)
    screenshot("01-idp-open", ss_dir)

    # Detect already-logged-in state (IDP redirects to /user/index.php on existing session)
    url = ab_eval("location.href")
    if "/user/index.php" in url:
        # Verify it's the right account before skipping
        body = ab_eval("document.body.innerText")
        expected_user_id = user.split("@")[0] if user else ""
        if expected_user_id and expected_user_id not in body:
            print(f"homework-fetch[{SLUG}]: IDP logged in as someone else; forcing fresh login", file=sys.stderr)
            subprocess.run([AB, "close"], capture_output=True, timeout=10)
            ab(["open", IDP_URL])
            time.sleep(2)
            # fall through to regular login flow below
        else:
            print(f"homework-fetch[{SLUG}]: IDP already logged in as {expected_user_id} ({url}), skipping Procedure A")
            return

    snap = ab(["snapshot"])
    user_ref = find_ref_near(snap, "ユーザー名", "textbox")
    otp_ref = find_ref_near(snap, "ワンタイムパスワード", "spinbutton")
    login_ref = find_button_ref(snap, "ログイン")
    if not user_ref:
        fail(f"username textbox not found:\n{snap[:500]}")
    ab(["fill", f"@{user_ref}", user])
    ab(["fill", f"@{otp_ref}", gen_totp(totp_secret)])
    ab(["click", f"@{login_ref}"])
    time.sleep(3)
    screenshot("02-after-otp", ss_dir)

    snap2 = ab(["snapshot"])
    pwd_ref = find_ref_near(snap2, "パスワード", "textbox")
    login2_ref = find_button_ref(snap2, "ログイン")
    if not pwd_ref:
        fail(f"password textbox not found:\n{snap2[:500]}")
    ab(["fill", f"@{pwd_ref}", pwd])
    ab(["click", f"@{login2_ref}"])
    time.sleep(3)
    screenshot("03-sso-home", ss_dir)
    url = ab_eval("location.href")
    if "/user/index.php" not in url:
        fail(f"IDP login failed; URL={url}")


def procedure_b_sso(ss_dir: Path) -> None:
    """SSO into edu-portal. Skips if already on Pky00102 (post-SSO home)."""
    ab(["open", EDU_PORTAL_ENTRY])
    time.sleep(2)
    url = ab_eval("location.href")
    if "Pky00102.xhtml" in url:
        print(f"homework-fetch[{SLUG}]: edu-portal already SSO'd ({url})")
        screenshot("10-edu-portal-home", ss_dir)
        return
    snap = ab(["snapshot"])
    login_link_ref = None
    for line in snap.splitlines():
        if "ログインはこちら" in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                login_link_ref = m.group(1); break
    if not login_link_ref:
        fail(f"'ログインはこちら' link not found:\n{snap[:500]}")
    ab(["click", f"@{login_link_ref}"])
    time.sleep(5)
    screenshot("10-edu-portal-home", ss_dir)
    url = ab_eval("location.href")
    if "Pky00102.xhtml" not in url:
        fail(f"edu-portal SSO failed; URL={url}")


def list_deadline_homework_refs(ss_dir: Path) -> list[dict]:
    """On the edu-portal home page, click the 期限あり tab and return refs+labels."""
    snap = ab(["snapshot", "-i"])
    # Find the 期限あり tab link ref
    kigen_ref = None
    lines = snap.splitlines()
    for i, line in enumerate(lines):
        if 'tab "期限あり"' in line or 'link "期限あり"' in line:
            for j in range(i, min(i + 3, len(lines))):
                if 'link "期限あり"' in lines[j]:
                    m = re.search(r"ref=(e\d+)", lines[j])
                    if m:
                        kigen_ref = m.group(1)
                        break
            if kigen_ref:
                break
    if not kigen_ref:
        # 期限あり tab missing → likely no current homework / UI change. Warn and return empty.
        print(f"homework-fetch[{SLUG}]: 期限あり tab not found in home snapshot — assuming no homework", file=sys.stderr)
        return []

    ab(["click", f"@{kigen_ref}"])
    time.sleep(2)
    screenshot("20-kigen-ari", ss_dir)

    # Re-snapshot and find any links that appear *inside* the 期限あり tab area.
    # The tab content renders inline; the homework links appear AFTER the tab line
    # and BEFORE the next tab line ("日表示").
    snap2 = ab(["snapshot", "-i"])
    Path(ss_dir.parent / "kigen-ari-snapshot.txt").write_text(snap2)

    homework_refs: list[dict] = []
    in_kigen = False
    idx = 0
    for line in snap2.splitlines():
        if 'tab "期限あり" [expanded=true' in line:
            in_kigen = True
            continue
        if in_kigen and re.match(r'^\s*-?\s*tab "', line) and '期限あり' not in line:
            in_kigen = False
            continue
        if in_kigen:
            m = re.search(r'link "([^"]+)" \[ref=(e\d+)\]', line)
            if m:
                label = m.group(1)
                ref = m.group(2)
                if label in ("期限あり",):
                    continue
                # idx disambiguates duplicate labels (same homework name across subjects)
                homework_refs.append({"label": label, "ref": ref, "idx": idx})
                idx += 1
    return homework_refs


def fetch_homework_detail(ref: str, label: str, idx: int, ss_dir: Path) -> dict:
    """Click a homework link and scrape the detail page."""
    ab(["click", f"@{ref}"])
    time.sleep(3)
    screenshot(f"30-homework-{idx:02d}", ss_dir)

    url = ab_eval("location.href")
    body = ab_eval("document.body.innerText")

    # Parse the detail page text
    detail = {
        "label": label,
        "ref_origin": ref,
        "url": url,
        "raw_body": body,
        "subject": None,
        "subject_code": None,
        "kadai_name": None,
        "kokai_period": None,
        "teishutsu_period": None,
        "kadai_content": None,
        "teishutsu_method": None,
    }

    # Extract subject "{科目名}({CODE})"
    m = re.search(r"([A-Z]{2}\d{4}[a-zA-Z]*)([぀-ヿ一-龯 A-Za-z]+)", body)
    if m:
        detail["subject_code"] = m.group(1)
        # Subject name appears right before code in the breadcrumb area
    # Better extraction by looking for context around "課題名"
    for pattern, key in [
        (r"課題名\s+([^\n]+)", "kadai_name"),
        (r"課題公開期間\s+\n?([^\n]+(?:\n[^\n]+)?)", "kokai_period"),
        (r"課題提出期間\s+\n?([^\n]+(?:\n[^\n]+)?)", "teishutsu_period"),
        (r"課題提出方法\s+([^\n]+)", "teishutsu_method"),
    ]:
        m = re.search(pattern, body)
        if m:
            detail[key] = m.group(1).strip()
    # The body has TWO "課題内容" labels — first is a section header, second
    # is the form field containing the actual assignment text. Anchor on
    # "課題提出期間" (which appears once) and look for the 課題内容 after it.
    # Allow 課題内容 / 課題説明 alternation and several closing anchors so the
    # parser doesn't break if the LMS slightly renames labels or skips the
    # 添付ファイル section.
    m = re.search(
        r"課題提出期間.+?(?:課題内容|課題説明)\s*\n+(.+?)\n+(?:添付ファイル|提出ファイル|課題提出方法|コメント|戻る|\Z)",
        body, re.S,
    )
    if m:
        detail["kadai_content"] = m.group(1).strip()

    # If every parsed field is None, the UI labels probably changed.
    parsed_any = any(detail.get(k) for k in ("kadai_name", "kokai_period", "teishutsu_period", "kadai_content"))
    if not parsed_any:
        detail["parse_warning"] = "no fields parsed — UI may have changed; raw_body dumped"

    # Subject name from breadcrumb-ish line e.g. "ST4093spアルゴリズム設計論"
    # Take the line right before "ui-button" in the header area
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^[A-Z]{2}\d{4}[a-zA-Z]*[぀-ヿ一-龯]", line):
            m = re.match(r"^([A-Z]{2}\d{4}[a-zA-Z]*)(.+)", line)
            if m:
                detail["subject_code"] = m.group(1)
                detail["subject"] = m.group(2).strip()
                break

    return detail


def format_slack(homeworks: list[dict], slug: str) -> str:
    if not homeworks:
        return f":school: *{{profile.education.institution}} 宿題チェック (期限あり)* — `{slug}`\n\n:white_check_mark: 期限ありの課題はありません。"

    lines = [f":school: *{{profile.education.institution}} 宿題チェック (期限あり)* — `{slug}`", ""]
    for hw in homeworks:
        subj = hw.get("subject") or "?"
        code = hw.get("subject_code") or ""
        kadai = hw.get("kadai_name") or hw.get("label")
        lines.append(f"*📝 {subj}* `{code}`")
        lines.append(f"• *課題名*: {kadai}")
        if hw.get("teishutsu_period"):
            lines.append(f"• *提出期間*: {hw['teishutsu_period']}")
        if hw.get("kokai_period"):
            lines.append(f"• *公開期間*: {hw['kokai_period']}")
        if hw.get("teishutsu_method"):
            lines.append(f"• *提出方法*: {hw['teishutsu_method']}")
        if hw.get("kadai_content"):
            content = hw["kadai_content"]
            if len(content) > 600:
                content = content[:600] + "..."
            lines.append(f"• *課題内容*:\n```\n{content}\n```")
        lines.append("")
    lines.append(f"宿題は **{len(homeworks)} 件** (期限あり タブ集計)")
    return "\n".join(lines)


def main() -> int:
    if not SLUG:
        fail("SLUG env required")

    secrets = load_secrets()
    today = date.today().isoformat()
    out_dir = WORKSPACE / SLUG
    out_dir.mkdir(parents=True, exist_ok=True)
    ss_dir = out_dir / "screenshots" / today / "homework"

    homeworks: list[dict] = []
    try:
        procedure_a_login(secrets, ss_dir)
        procedure_b_sso(ss_dir)
        refs = list_deadline_homework_refs(ss_dir)
        print(f"homework-fetch[{SLUG}]: found {len(refs)} homework deadline(s)")

        for run_idx, item in enumerate(refs, 1):
            # Return to home before each click (the home menu changes after a click)
            if run_idx > 1:
                ab(["open", EDU_PORTAL_HOME])
                time.sleep(3)
                # Session-expiry guard: if we got bounced back to IDP, re-login
                url_check = ab_eval("location.href")
                if "edu-portal.naist.jp" not in url_check:
                    print(f"  warn: session expired (URL={url_check}); re-logging in")
                    procedure_a_login(secrets, ss_dir)
                    procedure_b_sso(ss_dir)
                refs2 = list_deadline_homework_refs(ss_dir)
                # Re-match by ordinal index (immune to duplicate labels); fallback to label
                cur = next((r for r in refs2 if r.get("idx") == item.get("idx")), None)
                if not cur:
                    cur = next((r for r in refs2 if r["label"] == item["label"]), None)
                if not cur:
                    print(f"  warn: lost ref for {item['label']!r} (idx={item.get('idx')}); skipping")
                    continue
                item = cur
            detail = fetch_homework_detail(item["ref"], item["label"], run_idx, ss_dir)
            # Sanity: did we actually land on a homework page?
            if "edu-portal.naist.jp" not in (detail.get("url") or ""):
                print(f"  warn: homework click left edu-portal (URL={detail.get('url')}); skipping entry")
                continue
            homeworks.append(detail)

    except SystemExit:
        raise
    except Exception as e:
        slack_post(f":warning: naist:homework-fetch[{SLUG}] failed: {e}")
        raise
    finally:
        subprocess.run([AB, "close"], capture_output=True, timeout=10)

    # Persist
    snapshot = {
        "slug": SLUG,
        "fetched_at": f"{today}T{time.strftime('%H:%M:%SZ', time.gmtime())}",
        "fetched_via": "agent-{{profile.lateness.stakeholders.channel}} 0.27.0 + {{profile.education.institution}} IDP TOTP",
        "homework_count": len(homeworks),
        "homeworks": homeworks,
    }
    out = out_dir / f"homework-{today}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"homework-fetch[{SLUG}]: wrote {out}")

    # Slack
    msg = format_slack(homeworks, SLUG)
    slack_post(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
