#!/usr/bin/env python3
"""onchain.py — REAL Base-mainnet USDC verification for the earn/video slot (the thing that makes record_earn
count actual money). Read-only JSON-RPC, NO private key, NO Coinbase/CDP — just confirm inflows on-chain.

Two jobs:
  1. confirm_usdc_inflow(entry, recipient, rpc) — the production on-chain check injected into record_earn:
     fetch the tx receipt, find a USDC Transfer log whose `to` == recipient AND whose raw amount matches
     entry['amount'] (within 1 unit of 1e-6). Returns True ONLY for a real, successful, matching transfer.
  2. scan_inflows(recipient, from_block, rpc) — list USDC Transfers TO recipient since from_block, as
     record_earn-shaped entries. The CLI `detect` appends new ones to ~/.cloak/earn-video-inflows.jsonl
     (idempotent on tx_hash) so S4's record_earn can record real ChangeNOW affiliate-commission withdrawals.

Constants are Base mainnet. FOUNDER = the wallet ChangeNOW pays out to (set as the affiliate payout address).
"""
import json, os, sys, urllib.request

BASE_RPC = os.environ.get("BASE_RPC", "https://mainnet.base.org")
USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"            # USDC on Base (lowercase)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _recipient():
    """The DEDICATED earn/video affiliate receive address — ONLY ChangeNOW commission withdrawals land here, so
    every inflow is genuinely affiliate revenue (clean per-slot attribution). NOT the shared multi-purpose earn
    wallet 0x810f… (which also gets x402/gig/funding USDC and would be misattributed). Env override for tests."""
    env = os.environ.get("EARN_VIDEO_RECIPIENT")
    if env:
        return env.lower()
    try:
        return json.load(open(os.path.expanduser("~/.cloak/earn-video-wallet.json")))["address"].lower()
    except Exception:
        return "0x0000000000000000000000000000000000000000"   # fail-closed: no recipient ⇒ nothing matches


RECIPIENT = _recipient()
INFLOWS = os.path.expanduser("~/.cloak/earn-video-inflows.jsonl")
CURSOR = os.path.expanduser("~/.cloak/earn-video-onchain-cursor.json")
USDC_DECIMALS = 10 ** 6


def _rpc(method, params, rpc=BASE_RPC, timeout=15):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc, data=body, headers={
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",  # public RPC 403s the default python UA
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r).get("result")


def _topic_addr(topic):
    return "0x" + topic[-40:].lower()


def confirm_usdc_inflow(entry, recipient=None, rpc=BASE_RPC):
    """True ONLY if entry['tx_hash'] is a SUCCESSFUL tx containing a USDC Transfer to `recipient` whose amount
    matches entry['amount'] AND whose sender is NOT the recipient itself (reject self-transfers / self-funding).
    Fail-closed: any RPC error / mismatch / missing log → False (never fabricate)."""
    try:
        recipient = (recipient or RECIPIENT).lower()
        txh = entry.get("tx_hash")
        if not txh:
            return False
        rcpt = _rpc("eth_getTransactionReceipt", [txh], rpc)
        if not rcpt or rcpt.get("status") != "0x1":
            return False
        want_units = round(float(entry.get("amount", 0)) * USDC_DECIMALS)
        for log in rcpt.get("logs", []):
            if (log.get("address", "").lower() == USDC
                    and log.get("topics", [None])[0] == TRANSFER_TOPIC
                    and len(log["topics"]) >= 3
                    and _topic_addr(log["topics"][2]) == recipient
                    and _topic_addr(log["topics"][1]) != recipient):   # ★ reject self-transfer (from==to) ★
                got_units = int(log["data"], 16)
                if abs(got_units - want_units) <= 1:      # exact to 1 micro-USDC
                    return True
        return False
    except Exception:
        return False


def scan_inflows(recipient=None, from_block=None, rpc=BASE_RPC):
    """Return record_earn-shaped entries for every USDC Transfer to `recipient` (excluding self-transfers) in
    (from_block, latest]. Each entry carries log_index for precise dedup of multi-Transfer txs."""
    recipient = (recipient or RECIPIENT).lower()
    blk = _rpc("eth_blockNumber", [], rpc)
    if not blk:
        raise RuntimeError("eth_blockNumber returned no result")
    latest = int(blk, 16)
    start = (from_block + 1) if isinstance(from_block, int) else max(0, latest - 5000)
    padded = "0x" + "0" * 24 + recipient.replace("0x", "")
    out = []
    step = 2000
    b = start
    while b <= latest:
        end = min(b + step - 1, latest)
        logs = _rpc("eth_getLogs", [{
            "address": USDC, "fromBlock": hex(b), "toBlock": hex(end),
            "topics": [TRANSFER_TOPIC, None, padded],
        }], rpc) or []
        for lg in logs:
            if _topic_addr(lg["topics"][1]) == recipient:     # ★ skip self-transfer / self-funding ★
                continue
            out.append({
                "token": "USDC",
                "amount": int(lg["data"], 16) / USDC_DECIMALS,
                "direction": "in",
                "tx_hash": lg["transactionHash"],
                "log_index": int(lg.get("logIndex", "0x0"), 16),
                "from": _topic_addr(lg["topics"][1]),
                "block": int(lg["blockNumber"], 16),
                "verified": True,
            })
        b = end + 1
    return out, latest


def _key(e):
    return (e.get("tx_hash"), e.get("log_index"))


def _seen(path):
    s = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try: s.add(_key(json.loads(line)))
                except Exception: pass
    return s


def detect():
    """Scan Base for new USDC inflows to the DEDICATED earn/video receive address and append unseen ones to
    INFLOWS (idempotent on (tx_hash, log_index), so multi-Transfer txs aren't dropped or duplicated)."""
    cur = None
    if os.path.exists(CURSOR):
        try: cur = json.load(open(CURSOR)).get("last_block")
        except Exception: cur = None
    entries, latest = scan_inflows(RECIPIENT, cur)
    seen = _seen(INFLOWS)
    n = 0
    os.makedirs(os.path.dirname(INFLOWS), exist_ok=True)
    with open(INFLOWS, "a") as f:
        for e in entries:
            if _key(e) not in seen:
                f.write(json.dumps(e, ensure_ascii=False) + "\n"); seen.add(_key(e)); n += 1
    tmp = CURSOR + ".tmp"
    json.dump({"last_block": latest}, open(tmp, "w")); os.replace(tmp, CURSOR)
    print(json.dumps({"new_inflows": n, "scanned_to_block": latest, "recipient": RECIPIENT}))


if __name__ == "__main__":
    detect()
