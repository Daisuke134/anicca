#!/usr/bin/env python3
"""dework-discover.py — wallet-native crypto bounty discover for the bounty earn slot.

The GitHub-free well (Dais pivot 2026-07-01): Dework's GraphQL read endpoint needs NO auth and NO
GitHub. We fetch open (TODO) tasks, keep only those paying a real crypto token to a wallet, drop the
obvious MLM/recruitment noise with a COARSE pre-filter, and hand the survivors to the loop's brain —
the MODEL decides which task is genuinely doable + legit + worth doing (no hardcoded judgment; the
pre-filter only removes structural spam so the model isn't drowned). Identity to actually claim =
wallet-connect or Discord (no GitHub). Verified live 2026-07-01: 1045 TODO, 55 crypto-reward.

Usage: python3 dework-discover.py [out.json]   # writes {fetched_at, open_bounties:[...]}; prints count
Only real fetched tasks are emitted. No fakes (HARD 0.24).
"""
import json, sys, time, urllib.request

API = "https://api.deworkxyz.com/graphql"
# NOTE: do NOT request `permalink` in the bulk query — its resolver crashes on tasks with a null
# workspace slug and nulls the whole result (verified 2026-07-01). Fetch id/name/rewards only.
QUERY = ("query($f:GetTasksInput!){ getTasks(input:$f){ id name status "
         "rewards{ amount peggedToUsd token{ symbol address network{ name slug } } } } }")
CRYPTO = {"USDC", "USDT", "ETH", "DAI"}
# Coarse STRUCTURAL spam removal only (not a judgment on doability — that's the model's job).
# These tokens in a title mark MLM/recruitment/influencer noise that is never an agent-doable task.
SPAM_MARKERS = ("referral", "recruit", "investor", "kol ", "ambassador", "affiliate",
                "join our", "growth program", "shill", "airdrop hunter")


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"f": {"statuses": ["TODO"]}}}).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    return (d.get("data") or {}).get("getTasks") or []


def usd(reward):
    # Dework amounts are raw token units; USDC/USDT=6dp, DAI/ETH=18dp. peggedToUsd is the $ value when present.
    # amount is raw token units (USDC/USDT=6dp, DAI/ETH=18dp); convert that. peggedToUsd is often
    # 0/null on Dework, so only trust it when it's a positive number larger than the raw-unit calc.
    tok = (reward.get("token") or {}).get("symbol")
    dec = 6 if tok in ("USDC", "USDT") else 18
    base = None
    try:
        base = int(reward["amount"]) / (10 ** dec)
        # ETH/DAI tokens are not $1-pegged; for ETH approximate via peggedToUsd if present else skip $ basis
        if tok in ("ETH",):
            base = None
    except (TypeError, ValueError, KeyError):
        base = None
    peg = reward.get("peggedToUsd")
    try:
        peg = float(peg) if peg is not None else None
    except (TypeError, ValueError):
        peg = None
    if peg and peg > 0:
        return peg
    return base


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else None
    tasks = fetch()
    cands = []
    for t in tasks:
        rewards = t.get("rewards") or []
        cr = [r for r in rewards if ((r.get("token") or {}).get("symbol") in CRYPTO)]
        if not cr:
            continue
        name = (t.get("name") or "").strip()
        low = name.lower()
        if any(m in low for m in SPAM_MARKERS):
            continue  # structural spam, not a real task
        r = cr[0]
        tok = (r.get("token") or {})
        cands.append({
            "id": t.get("id"),
            "title": name[:120],
            "reward_usd": usd(r),
            "token": tok.get("symbol"),
            "network": (tok.get("network") or {}).get("name"),
            "claim_url": f"https://app.dework.xyz/task/{t.get('id')}",
            "source": "dework",
        })
    # rank by usd desc (None last)
    cands.sort(key=lambda c: (c["reward_usd"] is None, -(c["reward_usd"] or 0)))
    result = {"fetched_at": int(time.time()), "well": "dework", "open_bounties": cands}
    if out_path:
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
    print(f"[dework] crypto-reward agent-candidate tasks (spam-prefiltered): {len(cands)} "
          f"(of {len(tasks)} TODO). model picks the doable+legit one.")
    for c in cands[:8]:
        u = f"${c['reward_usd']:.0f}" if c["reward_usd"] is not None else "$?"
        print(f"  - {u:>6} {c['token']:<5} {c['title'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
