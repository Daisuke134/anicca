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
FOUNDER = "0x810f6d61f7606deee2657d3083e150a222bc29c5"          # founder/earn wallet (receive address)
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
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


def confirm_usdc_inflow(entry, recipient=FOUNDER, rpc=BASE_RPC):
    """True ONLY if entry['tx_hash'] is a SUCCESSFUL tx containing a USDC Transfer to `recipient` whose amount
    matches entry['amount']. Fail-closed: any RPC error / mismatch / missing log → False (never fabricate)."""
    try:
        txh = entry.get("tx_hash")
        if not txh:
            return False
        rcpt = _rpc("eth_getTransactionReceipt", [txh], rpc)
        if not rcpt or rcpt.get("status") != "0x1":
            return False
        want_units = round(float(entry.get("amount", 0)) * USDC_DECIMALS)
        rcv = recipient.lower()
        for log in rcpt.get("logs", []):
            if (log.get("address", "").lower() == USDC
                    and log.get("topics", [None])[0] == TRANSFER_TOPIC
                    and len(log["topics"]) >= 3
                    and _topic_addr(log["topics"][2]) == rcv):
                got_units = int(log["data"], 16)
                if abs(got_units - want_units) <= 1:      # exact to 1 micro-USDC
                    return True
        return False
    except Exception:
        return False


def scan_inflows(recipient=FOUNDER, from_block=None, rpc=BASE_RPC):
    """Return record_earn-shaped entries for every USDC Transfer to `recipient` in (from_block, latest]."""
    latest = int(_rpc("eth_blockNumber", [], rpc), 16)
    start = (from_block + 1) if isinstance(from_block, int) else max(0, latest - 5000)
    padded = "0x" + "0" * 24 + recipient.lower().replace("0x", "")
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
            out.append({
                "token": "USDC",
                "amount": int(lg["data"], 16) / USDC_DECIMALS,
                "direction": "in",
                "tx_hash": lg["transactionHash"],
                "from": _topic_addr(lg["topics"][1]),
                "block": int(lg["blockNumber"], 16),
                "verified": True,
            })
        b = end + 1
    return out, latest


def _seen(path):
    s = set()
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try: s.add(json.loads(line).get("tx_hash"))
                except Exception: pass
    return s


def detect():
    """Scan Base for new USDC inflows to FOUNDER and append unseen ones to INFLOWS (idempotent)."""
    cur = None
    if os.path.exists(CURSOR):
        try: cur = json.load(open(CURSOR)).get("last_block")
        except Exception: cur = None
    entries, latest = scan_inflows(FOUNDER, cur)
    seen = _seen(INFLOWS)
    n = 0
    os.makedirs(os.path.dirname(INFLOWS), exist_ok=True)
    with open(INFLOWS, "a") as f:
        for e in entries:
            if e["tx_hash"] not in seen:
                f.write(json.dumps(e, ensure_ascii=False) + "\n"); n += 1
    tmp = CURSOR + ".tmp"
    json.dump({"last_block": latest}, open(tmp, "w")); os.replace(tmp, CURSOR)
    print(json.dumps({"new_inflows": n, "scanned_to_block": latest}))


if __name__ == "__main__":
    detect()
