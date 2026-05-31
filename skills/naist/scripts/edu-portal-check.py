#!/usr/bin/env python3
"""edu-portal-check.py — runs Procedure A + B + C from SKILL.md.

Drives agent-browser CLI to log into NAIST IDP via TOTP, SSO into edu-portal,
scrape 学生時間割表 + 成績照会, and write a per-slug JSON snapshot.

This script is intentionally THIN — most logic is in SKILL.md as a procedure
the agent (or a future-you) reads + adapts when UI changes. The bash here
encodes the current procedure into shell so cron can fire it without an LLM.

Output: ~/.openclaw/workspace/naist/<slug>/portal-<ymd>.json + screenshots/
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


def fail(msg: str, code: int = 1) -> None:
    print(f"edu-portal-check[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def ab(args: list[str]) -> str:
    """Run agent-browser, return stdout text."""
    r = subprocess.run([AB, *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"agent-browser {' '.join(args)} → {r.returncode}\nSTDERR: {r.stderr}", file=sys.stderr)
    return r.stdout


def ab_eval(js: str) -> str:
    out = ab(["eval", js])
    # agent-browser eval prints JSON-quoted string; strip outer quotes
    s = out.strip()
    if s.startswith('"') and s.endswith('"'):
        s = json.loads(s)
    return s


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
    with urllib.request.urlopen(req, timeout=15):
        pass


def load_secrets() -> dict[str, str]:
    """Load per-slug secrets.env (chmod 600)."""
    p = STATE_ROOT / SLUG / "secrets.env"
    secrets: dict[str, str] = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            secrets[k.strip()] = v.strip().strip('"').strip("'")
    # fall back to global ~/.openclaw/.env
    g = Path.home() / ".openclaw" / ".env"
    if g.exists():
        for line in g.read_text().splitlines():
            if "=" not in line or line.strip().startswith("#"):
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
    """Find an element ref of `kind` (textbox/spinbutton/button) near a 'term' line."""
    lines = snapshot.splitlines()
    for i, line in enumerate(lines):
        if f'term "{term}"' in line:
            # Search next ~6 lines for an element of `kind`
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


def screenshot(label: str, ss_dir: Path) -> None:
    ss_dir.mkdir(parents=True, exist_ok=True)
    ab(["screenshot", str(ss_dir / f"{label}.png")])


def procedure_a_login(secrets: dict[str, str], ss_dir: Path) -> None:
    """Procedure A — IDP login via TOTP (see SKILL.md)."""
    user = secrets.get("NAIST_IDP_USERNAME") or secrets.get("NAIST_EDU_USER")
    pwd = secrets.get("NAIST_IDP_PASSWORD") or secrets.get("NAIST_EDU_PASSWORD")
    totp_secret = secrets.get("NAIST_TOTP_SECRET")
    if not all([user, pwd, totp_secret]):
        fail("missing NAIST_IDP_USERNAME / PASSWORD / TOTP_SECRET in secrets")

    ab(["open", "https://idp.naist.jp/"])
    time.sleep(2)
    screenshot("01-idp-open", ss_dir)

    snap = ab(["snapshot"])
    user_ref = find_ref_near(snap, "ユーザー名", "textbox")
    otp_ref = find_ref_near(snap, "ワンタイムパスワード", "spinbutton")
    login_ref = find_button_ref(snap, "ログイン")
    if not user_ref:
        fail(f"username textbox not found in OTP page snapshot:\n{snap[:500]}")

    ab(["fill", f"@{user_ref}", user])
    totp = gen_totp(totp_secret)
    ab(["fill", f"@{otp_ref}", totp])
    ab(["click", f"@{login_ref}"])
    time.sleep(3)
    screenshot("02-after-otp", ss_dir)

    # Password page
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
    print(f"edu-portal-check[{SLUG}]: IDP login OK ({url})")


def procedure_b_sso(ss_dir: Path) -> None:
    ab(["open", "https://edu-portal.naist.jp/uprx/up/km/kmh006/Kmh00601.xhtml"])
    time.sleep(2)
    screenshot("10-edu-portal-entry", ss_dir)

    snap = ab(["snapshot"])
    # The link is "ログインはこちら"
    login_ref = None
    for line in snap.splitlines():
        if "ログインはこちら" in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                login_ref = m.group(1); break
    if not login_ref:
        fail(f"'ログインはこちら' link not found:\n{snap[:500]}")
    ab(["click", f"@{login_ref}"])
    time.sleep(5)
    screenshot("11-edu-portal-home", ss_dir)
    url = ab_eval("location.href")
    if "Pky00102.xhtml" not in url:
        fail(f"edu-portal SSO failed; URL={url}")
    print(f"edu-portal-check[{SLUG}]: edu-portal SSO OK ({url})")


def procedure_c_scrape(ss_dir: Path) -> dict:
    # 学生時間割表
    snap = ab(["snapshot", "-i"])
    jika_ref = None
    for line in snap.splitlines():
        if 'link "学生時間割表"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                jika_ref = m.group(1); break
    if not jika_ref:
        fail("学生時間割表 link not found")
    ab(["click", f"@{jika_ref}"])
    time.sleep(4)
    screenshot("20-jikanwari", ss_dir)
    jikanwari_text = ab_eval("document.body.innerText")

    # 成績照会
    snap2 = ab(["snapshot", "-i"])
    seiseki_ref = None
    for line in snap2.splitlines():
        if 'link "成績照会"' in line:
            m = re.search(r"ref=(e\d+)", line)
            if m:
                seiseki_ref = m.group(1); break
    if not seiseki_ref:
        fail("成績照会 link not found")
    ab(["click", f"@{seiseki_ref}"])
    time.sleep(4)
    screenshot("21-seiseki", ss_dir)
    seiseki_text = ab_eval("document.body.innerText")

    return {"jikanwari_raw": jikanwari_text, "seiseki_raw": seiseki_text}


def parse_courses_from_jikanwari(text: str) -> list[dict]:
    courses = []
    for line in text.splitlines():
        m = re.match(r"^([A-Z]{2}\d{4}\w*)\s+(.+?)$", line.strip())
        if m:
            courses.append({"code_full": m.group(1), "name_raw": m.group(2)})
    return courses


def parse_gpa_from_jikanwari(text: str) -> dict:
    gpa: dict = {}
    for m in re.finditer(r"(\d{4})年度\s+(春|秋)学期\s+([\d.]+)", text):
        gpa[f"{m.group(1)}_{'spring' if m.group(2)=='春' else 'fall'}"] = float(m.group(3))
    cum = re.search(r"通算\s+([\d.]+)", text)
    if cum:
        gpa["cumulative"] = float(cum.group(1))
    return gpa


def parse_failures_from_seiseki(text: str) -> list[str]:
    failures = []
    for m in re.finditer(r"\t([^\t\n]+?)\t\S*\t不可\t", text):
        failures.append(m.group(1).strip())
    return list(dict.fromkeys(failures))


def main() -> int:
    if not SLUG:
        fail("SLUG env required")

    secrets = load_secrets()
    today = date.today().isoformat()
    out_dir = WORKSPACE / SLUG
    out_dir.mkdir(parents=True, exist_ok=True)
    ss_dir = out_dir / "screenshots" / today

    try:
        procedure_a_login(secrets, ss_dir)
        procedure_b_sso(ss_dir)
        scraped = procedure_c_scrape(ss_dir)
    except SystemExit:
        raise
    except Exception as e:
        slack_post(f":warning: naist:edu-portal-check[{SLUG}] failed at agent-browser step: {e}")
        raise
    finally:
        subprocess.run([AB, "close"], capture_output=True, timeout=10)

    courses = parse_courses_from_jikanwari(scraped["jikanwari_raw"])
    gpa = parse_gpa_from_jikanwari(scraped["jikanwari_raw"])
    failures = parse_failures_from_seiseki(scraped["seiseki_raw"])

    snapshot = {
        "slug": SLUG,
        "scraped_at": f"{today}T{time.strftime('%H:%M:%SZ', time.gmtime())}",
        "scraped_via": "agent-browser 0.26.0 + NAIST IDP TOTP",
        "current_courses": courses,
        "gpa": gpa,
        "failures_needing_retake": failures,
        "raw_jikanwari": scraped["jikanwari_raw"][:5000],
        "raw_seiseki": scraped["seiseki_raw"][:8000],
    }
    out = out_dir / f"portal-{today}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"edu-portal-check[{SLUG}]: wrote {out}")

    msg_lines = [f":school: *NAIST edu-portal weekly* ({SLUG})"]
    msg_lines.append(f"履修中: {len(courses)} 科目  /  GPA 通算: {gpa.get('cumulative', 'n/a')}")
    if failures:
        msg_lines.append(f":warning: 不可 ({len(failures)}): {', '.join(failures[:6])}")
    msg_lines.append(f"`{out}`")
    slack_post("\n".join(msg_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
