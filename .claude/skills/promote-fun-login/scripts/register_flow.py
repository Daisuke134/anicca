#!/usr/bin/env python3
"""register_flow.py — end-to-end, ZERO-human-credential promote.fun account registration.

Proven flow (verified live 2026-07-04, account `anicca_clip_promote`):
  1. Launch (or reuse) the dedicated CloakBrowser instance on CDP_PORT (default 9224),
     profile ~/.cloak/profiles/promote-fun — NEVER the Dais daily-driver (:9222).
  2. Navigate to https://www.promote.fun/ , dismiss the onboarding modal if present.
  3. Click "Register" (top-right nav button), fill Username/Email/Password via CSS
     selectors on the placeholder text (NOT Google OAuth — that authenticates as a HUMAN's
     Google identity and can trigger THEIR phone 2FA, which is a zero-human-loop violation.
     Dais 2026-07-04 verbatim: "no using human credential in any way, because that is what
     it means to be no human loop").
  4. Check the Terms-of-Service checkbox, click Register.
  5. Read the 6-digit email verification code from the AI's OWN mailbox (AgentMail API,
     GET /v0/inboxes/<inbox>/messages) — never a human's inbox.
  6. Type the code into the 6 OTP boxes, click "Verify Email".
  7. Confirm login (a wallet balance chip + avatar appear in the top-right nav).

Why NOT click_xy with hardcoded coordinates: the two Google-OAuth attempts that preceded
this design silently no-op'd on raw mouse-event coordinates for some buttons (a passkey
prompt's "Try another way" link). Every click in this script goes through
cdp.click_by_text (JS .click(), reliable) or cdp.click_sel (CSS selector + real center
click) instead — see cdp.py's click_by_text docstring for why.

Usage:
  /opt/homebrew/bin/python3 register_flow.py --username anicca_clip_promote \
      --email anicca-genesis@agentmail.to [--password <pw>] [--cdp-port 9224]

Prints ONE JSON line: {"ok": true/false, "username":..., "email":..., "password":...,
"logged_in": true/false, "step": "<last step reached>"}. Never fabricates success — if any
step fails, reports the exact step and stops (exit 0, the caller decides what to do next).

Requires env AGENTMAIL_API_KEY (for reading the verification code) — sourced from
~/.openclaw/.env by the caller, same pattern as every other skill in this repo.
"""
import argparse
import calendar
import json
import os
import re
import secrets
import string
import sys
import time
import urllib.request

CDP_DIR = os.path.expanduser("~/.claude/skills/ig-account-create/scripts")
sys.path.insert(0, CDP_DIR)


def _random_password(n=20):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _fill_field(cdp, tid, placeholder, value):
    """Click the input matching the placeholder, then insert_text (Input.insertText —
    reliable, no synthetic keydown-per-char loop needed)."""
    sel = f'input[placeholder="{placeholder}"]'
    r = cdp.click_sel(tid, sel)
    if r.get("__error__"):
        return r
    time.sleep(0.2)
    return cdp.insert_text(tid, value)


def _read_verification_code(agentmail_key, inbox, since_ts, timeout_s=30):
    """Poll the AI's OWN AgentMail inbox for a 'is your verification code' message newer
    than since_ts, and extract the 6-digit code. Never reads a human's mailbox."""
    deadline = time.time() + timeout_s
    pattern = re.compile(r"(\d{6})\s+is your")
    while time.time() < deadline:
        req = urllib.request.Request(
            f"https://api.agentmail.to/v0/inboxes/{inbox}/messages?limit=5",
            headers={"Authorization": f"Bearer {agentmail_key}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        for m in data.get("messages", []):
            preview = m.get("preview", "") or ""
            if "verification code" not in preview.lower():
                continue
            # only accept a message strictly newer than since_ts — otherwise a stale code
            # from a PRIOR registration attempt could be picked up by mistake.
            ts_str = m.get("timestamp", "")
            try:
                # AgentMail timestamps are UTC (Z-suffixed) — calendar.timegm interprets the
                # struct_time as UTC, unlike time.mktime which assumes local time (a real bug
                # caught here 2026-07-04: time.mktime silently shifted this by the local UTC
                # offset, which in JST would have accepted mail up to 9h "in the future").
                msg_ts = calendar.timegm(time.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                continue
            if msg_ts < since_ts - 60:  # allow 60s clock-skew slack, still excludes old mail
                continue
            match = pattern.search(preview)
            if match:
                return match.group(1)
        time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", required=True)
    ap.add_argument("--email", default="anicca-genesis@agentmail.to")
    ap.add_argument("--password", default=None)
    ap.add_argument("--cdp-port", type=int, default=9224)
    ap.add_argument("--agentmail-inbox", default="anicca-genesis@agentmail.to")
    args = ap.parse_args()

    os.environ["CDP_PORT"] = str(args.cdp_port)
    import cdp  # noqa: E402  (must import AFTER CDP_PORT is set)

    password = args.password or _random_password()
    result = {"ok": False, "username": args.username, "email": args.email,
              "password": password, "logged_in": False, "step": "start"}

    agentmail_key = os.environ.get("AGENTMAIL_API_KEY")
    if not agentmail_key:
        result["step"] = "no-op: AGENTMAIL_API_KEY not set (credential-not-given, per Dais rule)"
        print(json.dumps(result)); return

    cdp_host = os.environ.get("CDP_HOST", "localhost")
    tabs = json.load(urllib.request.urlopen(f"http://{cdp_host}:{args.cdp_port}/json/list", timeout=5))
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    if not page_tabs:
        result["step"] = "no-tab: launch the dedicated CloakBrowser instance first (launch_promote_browser.py)"
        print(json.dumps(result)); return
    tid = page_tabs[0]["id"]

    cdp.navigate(tid, "https://www.promote.fun/")
    time.sleep(4)
    result["step"] = "navigated"

    # dismiss onboarding modal if present (best-effort, ignore if absent)
    cdp.click_sel(tid, 'button:has(svg)')  # no-op harmlessly if selector matches nothing useful
    since_ts = time.time()

    r = cdp.click_by_text(tid, "Register")
    if not r.get("found"):
        result["step"] = "register-button-not-found"
        print(json.dumps(result)); return
    time.sleep(2)
    result["step"] = "register-tab-open"

    _fill_field(cdp, tid, "Enter your username", args.username)
    _fill_field(cdp, tid, "Enter your email", args.email)
    _fill_field(cdp, tid, "Enter your password", password)
    result["step"] = "form-filled"

    # Terms-of-Service checkbox: the only checkbox on this form. The real <input> is a
    # visually-hidden 1x1px node (a styled custom checkbox sits on top of it) — click_sel's
    # coordinate-center click lands on the wrong spot entirely. A direct JS .click() on the
    # input itself fires correctly regardless of its visual size/position (verified 2026-07-04:
    # click_sel left it unchecked and silently blocked form submission; .click() fixed it).
    cb_js = ('(()=>{const cb=document.querySelector(\'input[type="checkbox"]\');'
             'if(!cb)return{found:false};cb.click();return{found:true,checked:cb.checked};})()')
    cb_result = cdp.evaluate(tid, cb_js)
    if not (cb_result or {}).get("checked"):
        result["step"] = "checkbox-click-failed"
        print(json.dumps(result)); return
    time.sleep(0.3)

    # index=-1: "Register" text matches 3 elements on this page (nav-bar button, modal
    # tab, AND the form's submit button) — index=0 silently re-clicked the nav-bar button
    # (a no-op, modal already open) instead of submitting. The submit button is last in
    # DOM order. Verified 2026-07-04 via a one-off querySelectorAll dump.
    r = cdp.click_by_text(tid, "Register", index=-1)
    if not r.get("found"):
        result["step"] = "submit-register-button-not-found"
        print(json.dumps(result)); return
    time.sleep(3)
    result["step"] = "register-submitted"

    code = _read_verification_code(agentmail_key, args.agentmail_inbox, since_ts)
    if not code:
        result["step"] = "verification-code-not-received"
        print(json.dumps(result)); return
    result["step"] = f"verification-code-received"

    # 6 separate OTP boxes: click the first, then insert_text — most OTP widgets auto-advance
    # focus per character on input event.
    cdp.click_sel(tid, "input")  # first focusable input on the verify screen
    cdp.insert_text(tid, code)
    time.sleep(1)

    r = cdp.click_by_text(tid, "Verify Email")
    if not r.get("found"):
        result["step"] = "verify-button-not-found"
        print(json.dumps(result)); return
    time.sleep(3)
    result["step"] = "verify-submitted"

    # Confirm login: look for a wallet-balance chip ("$" text near top of a logged-in nav).
    page_text = cdp.evaluate(tid, "document.body.innerText") or ""
    logged_in = "$" in page_text[:400] and "Sign up with Google" not in page_text[:2000]
    result["logged_in"] = logged_in
    result["ok"] = logged_in
    result["step"] = "done"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
