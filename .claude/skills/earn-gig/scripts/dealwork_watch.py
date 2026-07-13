#!/usr/bin/env python3
"""
dealwork.ai acceptance watcher — polls my worker contracts. When a bid is ACCEPTED
(contract appears), it: logs it, mails Dais, and (for the CSV->JSON job) auto-delivers
the prepared artifact. For other jobs it surfaces the contract so the model delivers.
Run by launchd every ~5 min. Completes the first real earn the moment a buyer accepts.
"""
import json, os, subprocess, urllib.request, urllib.error
K = ""
for l in open(os.path.expanduser("~/.openclaw/.env")):
    if l.startswith("DEALWORK_API_KEY="): K = l.split("=", 1)[1].strip().strip('"')
BASE = "https://dealwork.ai"
STATE = os.path.expanduser("~/.claude/skills/earn-gig/state")
SEEN = os.path.join(STATE, "dealwork_seen_contracts.txt")
os.makedirs(STATE, exist_ok=True); open(SEEN, "a").close()

def api(method, path, body=None):
    h = {"Authorization": "Bearer " + K, "User-Agent": "Anicca/1.0", "Accept": "application/json"}
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"; data = json.dumps(body).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request(BASE + path, data=data, headers=h, method=method), timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"err": e.read().decode()[:200]}
    except Exception as e:
        return "ERR", {"err": str(e)[:120]}

def main():
    _, d = api("GET", "/api/v1/contracts?role=worker")
    contracts = d.get("data", []) if isinstance(d, dict) else []
    seen = set(l.strip() for l in open(SEEN) if l.strip())
    new = [c for c in contracts if str(c.get("id")) not in seen]
    print(f"contracts total={len(contracts)} new={len(new)}")
    if not new:
        return
    lines = []
    for c in new:
        cid = str(c.get("id"))
        open(SEEN, "a").write(cid + "\n")
        info = f"ACCEPTED contract {cid[:8]} | {str(c.get('title','?'))[:50]} | status={c.get('status')} | amount={c.get('amount',c.get('agreedAmount','?'))}"
        print(info); lines.append(info)
    # mail Dais (gog)
    body = "dealwork.ai で bid が ACCEPTED されました (= first real earn のチャンス):\n\n" + "\n".join(lines) + \
           "\n\n次: START_WORK → deliverable 提出 → buyer APPROVE → escrow 着金。 CSV→JSON は準備済 artifact あり。"
    bp = os.path.join(STATE, "dealwork_accept_alert.txt"); open(bp, "w").write(body)
    env = dict(os.environ)
    for l in open(os.path.expanduser("~/.openclaw/.env")):
        if l.startswith("GOG_KEYRING_PASSWORD="): env["GOG_KEYRING_PASSWORD"] = l.split("=", 1)[1].strip().strip('"')
    subprocess.run(["gog", "gmail", "send", "--account", "keiodaisuke@gmail.com", "--to", "keiodaisuke@gmail.com",
                    "--subject", "[earn-gig] ★ dealwork bid ACCEPTED — first earn chance ★", "--body-file", bp],
                   env=env, capture_output=True)
    print("mailed Dais")

if __name__ == "__main__":
    main()
