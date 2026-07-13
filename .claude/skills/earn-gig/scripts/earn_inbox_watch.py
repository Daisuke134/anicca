#!/usr/bin/env python3
"""
earn-inbox watcher — ONE always-on detector across every gig platform.
Polls Gmail (gog) for platform notifications that need the agent to ACT:
  - Coconala: トークルーム新着 / 仮払い / 採用 / 評価依頼
  - LaborX: new message / hired / milestone / review
  - dealwork.ai: bid accepted (also covered by dealwork_watch.py API)
Writes actionable items to state/earn_action_queue.jsonl + mails Dais a summary.
The AGENT (this Claude /loop, or an Anicca heartbeat) reads the queue and acts
(reply in talk room, deliver work, request review). Detection is deterministic
(no browser, no model); the JUDGMENT/creation stays with the agent.
Run by launchd every ~10 min.
"""
import json, os, re, subprocess, time

STATE = os.path.expanduser("~/.claude/skills/earn-gig/state")
QUEUE = os.path.join(STATE, "earn_action_queue.jsonl")
SEEN = os.path.join(STATE, "earn_inbox_seen.txt")
os.makedirs(STATE, exist_ok=True); open(SEEN, "a").close()
ACCT = "keiodaisuke@gmail.com"

# platform -> (gmail search, action hint). Natural-language signals, not brittle.
SIGNALS = [
    ("coconala", 'from:coconala.com newer_than:1d', "ココナラ: トーク/仮払い/採用/評価 を確認し対応"),
    ("laborx",   'from:laborx.com OR from:mail.laborx.com newer_than:1d', "LaborX: message/hired/milestone を確認し対応"),
    ("dealwork", 'from:dealwork.ai newer_than:1d', "dealwork: bid accepted を確認し納品"),
]

def env():
    e = dict(os.environ)
    for l in open(os.path.expanduser("~/.openclaw/.env")):
        if l.startswith("GOG_KEYRING_PASSWORD="): e["GOG_KEYRING_PASSWORD"] = l.split("=", 1)[1].strip().strip('"')
        if l.startswith("GOG_ACCOUNT="): e["GOG_ACCOUNT"] = l.split("=", 1)[1].strip().strip('"')
    return e

def search(q):
    r = subprocess.run(["gog", "gmail", "search", "--account", ACCT, "--json", "--limit", "10", q],
                       capture_output=True, text=True, env=env())
    try:
        d = json.loads(r.stdout or "{}"); return d.get("threads", d.get("messages", []))
    except Exception:
        return []

def main():
    seen = set(l.strip() for l in open(SEEN) if l.strip())
    new_items = []
    for platform, q, hint in SIGNALS:
        for t in search(q):
            tid = str(t.get("id", ""))
            if not tid or tid in seen:
                continue
            seen_line = tid
            open(SEEN, "a").write(seen_line + "\n")
            item = {"ts": None, "platform": platform, "thread": tid,
                    "subject": str(t.get("subject", t.get("snippet", "")))[:90], "action": hint}
            new_items.append(item)
            open(QUEUE, "a").write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"new actionable items: {len(new_items)}")
    if not new_items:
        return
    body = "gig-work: 要対応の通知が来ました (= 採用/メッセージ/仮払い/評価)。 agent loop が対応します:\n\n" + \
        "\n".join(f"[{x['platform']}] {x['subject']} → {x['action']}" for x in new_items)
    bp = os.path.join(STATE, "earn_inbox_alert.txt"); open(bp, "w").write(body)
    subprocess.run(["gog", "gmail", "send", "--account", ACCT, "--to", ACCT,
                    "--subject", f"[earn-gig] ★ 要対応 {len(new_items)} 件 (gig 通知) ★",
                    "--body-file", bp], env=env(), capture_output=True)
    for x in new_items:
        print(f"  [{x['platform']}] {x['subject']}")

if __name__ == "__main__":
    main()
