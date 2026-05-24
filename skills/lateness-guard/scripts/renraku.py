#!/usr/bin/env python3
"""
renraku — when the user is confirmed late, tell the right people automatically.

OSS-general: NO hardcoded names/addresses. Recipients + signing identity come
from the per-user gitignored profile (identity/profile.json):
  - profile.stakeholder_for(event) -> {channel, to, sender}  (e.g. work->boss {{profile.lateness.stakeholders.channel}})
  - profile.identity_for(event)     -> signing name (comedy={{profile.lateness.stakeholders.senderType}} name, work={{profile.lateness.stakeholders.senderType}})
Delivery order: profile stakeholder ({{profile.lateness.stakeholders.channel}}/slack) -> calendar attendees -> Slack draft.

Tone: humanized JA, polite but not stiff.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

ENV = (Path.home() / ".openclaw" / ".env").read_text()


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def gog_account():
    return env("GOG_ACCOUNT", "") or prof.google_account()


def compose(sender, event, minutes):
    return (f"お疲れさまです、{sender}です。{event}に{minutes}分ほど遅れてしまいそうです。"
            f"申し訳ありません、着き次第すぐ向かいます。")


def send_gmail(to_addr, subject, body):
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "gmail", "send", "--account", gog_account(),
         "--to", to_addr, "--subject", subject, "--body", body],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD")},
    )
    return out.returncode == 0, (out.stderr or out.stdout)[:200]


def slack(text, channel=None):
    try:
        req = urllib.request.Request("https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel or env("SLACK_CHANNEL_ID"), "text": text}).encode(),
            headers={"Content-Type": "application/json; charset=utf-8",
                     "Authorization": f"Bearer {env('SLACK_BOT_TOKEN')}"}, method="POST")
        urllib.request.urlopen(req, timeout=15).read()
        return True
    except Exception as e:
        print(f"[renraku] slack failed: {e}", file=sys.stderr)
        return False


def send_renraku(event, minutes, attendees=None):
    """event: {summary, location, attendees?, description?}. Returns a result dict."""
    summary = event.get("summary", "予定")
    ctx_text = f"{summary} {event.get('location','')} {event.get('description','')}"
    entry = prof.stakeholder_for(ctx_text)
    sender = (entry or {}).get("sender") or prof.identity_for(ctx_text)
    msg = compose(sender, summary, minutes)
    subject = f"【遅刻のご連絡】{summary}"

    # 1) profile stakeholder ({{profile.lateness.stakeholders.channel}} / slack)
    if entry:
        if entry.get("channel") == "{{profile.lateness.stakeholders.channel}}" and entry.get("to"):
            ok, info = send_gmail(entry["to"], subject, msg)
            slack(f"🏃 renraku: {summary} → {{profile.lateness.stakeholders.channel}} {entry['to']} ({'sent' if ok else 'FAILED '+info})\n> {msg}")
            return {"via": "profile-{{profile.lateness.stakeholders.channel}}", "ok": ok}
        if entry.get("channel") == "slack" and entry.get("to"):
            ok = slack(msg, channel=entry["to"])
            slack(f"🏃 renraku: {summary} → slack {entry['to']} ({'sent' if ok else 'FAIL'})\n> {msg}")
            return {"via": "profile-slack", "ok": ok}

    # 2) calendar attendees -> {{profile.lateness.stakeholders.channel}}
    {{profile.lateness.stakeholders.channel}}s = [a.get("{{profile.lateness.stakeholders.channel}}") for a in (attendees or event.get("attendees") or [])
              if a.get("{{profile.lateness.stakeholders.channel}}") and a.get("{{profile.lateness.stakeholders.channel}}") != gog_account()]
    if {{profile.lateness.stakeholders.channel}}s:
        results = [send_gmail(e, subject, msg) for e in {{profile.lateness.stakeholders.channel}}s]
        ok = all(r[0] for r in results)
        slack(f"🏃 renraku: {summary} → {len({{profile.lateness.stakeholders.channel}}s)} attendee(s) ({'sent' if ok else 'partial/FAIL'})\n> {msg}")
        return {"via": "attendees", "ok": ok}

    # 3) no recipient known -> ready draft to Slack for one-tap forward
    slack(f"🏃 *遅刻 renraku 要送信* (送信先未登録)\n予定: *{summary}*\nそのまま送れる文面:\n> {msg}\n"
          f"_この種の予定の連絡先を profile.json stakeholders に入れれば次回から自動送信。_")
    return {"via": "slack-draft", "ok": True}


if __name__ == "__main__":
    ev = {"summary": sys.argv[1] if len(sys.argv) > 1 else "テスト予定"}
    mins = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(json.dumps(send_renraku(ev, mins), ensure_ascii=False))
