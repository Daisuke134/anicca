#!/usr/bin/env python3
"""
Claw Earn agent client — ★ no-human, wallet-native earning ★ (any AI, any model).

Proves Dais's vision: an AI with ONLY a wallet key earns USDC on a real marketplace
with ZERO human/email/captcha/browser. Auth = wallet signature (EIP-191 personal_sign).

Flow (official API, verified 2026-06-29):
  POST /clawAgentSessionChallenge {walletAddress}      -> challengeId + message
  sign message with wallet (eth personal_sign)
  POST /clawAgentSession {walletAddress, challengeId, signature} -> agentSessionToken (24h)
  GET  /claw/tasks (public)                            -> available bounties
  POST /agentStakeAndConfirm {agentSessionToken, taskId, contractAddress, ...}  (needs USDC stake)
  POST /agentSubmitWork {agentSessionToken, taskId, submissionText/Hash/Links, ...}
  POST /agentRateAndClaimStake -> on-chain USDC payout to wallet

Usage:
  python3 claw_agent.py session     # auth only (no capital needed) -> prints token
  python3 claw_agent.py poll        # list available bounties
  python3 claw_agent.py loop        # poll until a bounty appears, then surface it

Requires: eth_account (pip). Wallet key from ~/.openclaw/.env::BLOCKRUN_WALLET_KEY (EVM, Base).
Docs: https://aiagentstore.ai/skills/openclaw/claw-earn/SKILL.md
"""
import os, json, sys, time, urllib.request, urllib.error

BASE = "https://aiagentstore.ai"
ENV = os.path.expanduser("~/.openclaw/.env")

def load_key():
    for l in open(ENV):
        if l.startswith("BLOCKRUN_WALLET_KEY=") and "=" in l:
            k = l.split("=", 1)[1].strip().strip('"')
            return k if k.startswith("0x") else "0x" + k
    raise SystemExit("BLOCKRUN_WALLET_KEY not in ~/.openclaw/.env")

def account():
    from eth_account import Account
    return Account.from_key(load_key())

def _req(method, path, body=None, token=None):
    h = {"Accept": "application/json", "User-Agent": "claw-agent/1.0"}
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"; data = json.dumps(body).encode()
    if token:
        h["X-Agent-Session-Token"] = token
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        return 200, json.loads(urllib.request.urlopen(req, timeout=25).read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {"__raw__": "err"}

def get_session():
    """Wallet-signature session. No human, no capital. Returns agentSessionToken."""
    from eth_account.messages import encode_defunct
    acct = account(); addr = acct.address
    c, ch = _req("POST", "/clawAgentSessionChallenge", {"walletAddress": addr})
    if c != 200 or not ch.get("message"):
        raise SystemExit(f"challenge failed {c}: {ch}")
    sig = acct.sign_message(encode_defunct(text=ch["message"])).signature.hex()
    sig = sig if sig.startswith("0x") else "0x" + sig
    c2, s = _req("POST", "/clawAgentSession",
                 {"walletAddress": addr, "challengeId": ch["challengeId"], "signature": sig})
    if c2 != 200 or not s.get("agentSessionToken"):
        raise SystemExit(f"session failed {c2}: {s}")
    return addr, s["agentSessionToken"], s.get("expiresAtMs")

def poll_tasks(tab=None):
    """Available bounties (public). tab=None -> open; tab='completed' -> history."""
    path = "/claw/tasks" + (f"?tab={tab}" if tab else "")
    c, d = _req("GET", path)
    items = d.get("items", []) if isinstance(d, dict) else []
    counts = d.get("counts", {}) if isinstance(d, dict) else {}
    return counts, items

# ── RECIPE: which gigs to TAKE (the judgment is the model's; this is the heuristic) ──
# The running model decides per task. Guidance (right-altitude, not a hard gate):
#   TAKE  = work that completes with ONLY web/API/compute + returns text/data/code:
#           research, lead-gen, data extraction, competitor analysis, summarization,
#           code, translation, classification. (Claw Earn 'Research' APPROVED example.)
#   SKIP  = needs posting on EXTERNAL sites / accounts / captcha (SEO backlinks, guest
#           posts, business listings) — human-loop + high reject rate.
#   SKIP  = referral/"bring N people" sales — junk, mostly expires/rejects.
TAKE_HINT = ("Take only if completable with web+API+compute alone (research/data/code/"
             "translation/summarize). Skip external-site posting (SEO backlinks/guest posts/"
             "listings), captcha, and referral-sales bounties.")

def assess(items):
    """Return tasks with a cheap suitability PRE-screen. Final take/skip = the model's call.
    Pre-screen only flags the obvious SKIP categories so the model focuses on viable ones."""
    SKIP_CATS = ("link building", "seo", "backlink", "guest post", "listing", "sales", "referral")
    out = []
    for t in items:
        cat = str(t.get("category", "")).lower()
        title = str(t.get("title", "")).lower()
        likely_skip = any(s in cat or s in title for s in SKIP_CATS)
        rw = t.get("reward", t.get("amount", 0))
        try: usd = int(rw) / 1e6
        except Exception: usd = rw
        out.append({
            "taskId": t.get("taskId", t.get("id")), "contractAddress": t.get("contractAddress"),
            "title": t.get("title"), "category": t.get("category"), "rewardUSDC": usd,
            "hasPrivateDetails": t.get("hasPrivateDetails"), "instantStart": t.get("instantStart"),
            "prescreen": "likely_skip" if likely_skip else "candidate",
        })
    return out

def stake(token, task_id, contract, tx_hash=None, note="Starting work."):
    """Worker stake to begin (instantStart). Needs USDC stake capital in wallet.
    Two-step: prepare (no txHash) -> sign/send tx -> confirm (with txHash). See agent API docs."""
    body = {"agentSessionToken": token, "taskId": task_id, "contractAddress": contract, "interestNote": note}
    if tx_hash: body["txHash"] = tx_hash
    return _req("POST", "/agentStakeAndConfirm", body)

def submit(token, task_id, contract, text=None, links=None, sub_hash=None, tx_hash=None):
    """Submit completed work. session-auth (no walletAddress). text/links OR submissionHash."""
    body = {"agentSessionToken": token, "taskId": task_id, "contractAddress": contract}
    if text: body["submissionText"] = text
    if links: body["submissionLinks"] = links
    if sub_hash: body["submissionHash"] = sub_hash
    if tx_hash: body["txHash"] = tx_hash
    return _req("POST", "/agentSubmitWork", body)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "session"
    if cmd == "session":
        addr, token, exp = get_session()
        print(f"wallet: {addr}")
        print(f"agentSessionToken: {token}")
        print(f"expiresAtMs: {exp}")
    elif cmd == "poll":
        counts, items = poll_tasks()
        print("counts:", json.dumps(counts))
        for a in assess(items):
            print(f" [{a['prescreen']:11}] ${a['rewardUSDC']} {str(a['title'])[:48]} | id={a['taskId']}")
        if not items:
            print("(no open bounties right now — poll again later)")
        print("\nTAKE rule:", TAKE_HINT)
    elif cmd == "loop":
        # poll until a bounty appears; surface it (staking gated on USDC capital)
        addr, token, exp = get_session()
        print(f"session ready ({addr}). polling for bounties...")
        while True:
            counts, items = poll_tasks()
            avail = counts.get("available", 0)
            print(f"[{time.strftime('%H:%M:%S')}] available={avail}")
            if items:
                print("BOUNTY APPEARED:", json.dumps(items[0])[:300])
                break
            time.sleep(300)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
