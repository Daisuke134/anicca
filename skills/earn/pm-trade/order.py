#!/usr/bin/env python3
"""order.py — the REAL Polymarket CLOB order executor for earn/pm-trade (money-safe). The LOOP invokes this
(I do NOT hand-fire). DEFAULT = DRY_RUN: it initializes the client + derives CLOB creds from the wallet
(read-only, proves the path) and PRINTS the order it WOULD place — it posts NOTHING. A real order posts ONLY
with DRY_RUN=false AND EARN_MODE=execute AND PM_PAPER_PASS=1 (the paper gate) AND funded Polygon USDC.

Prereqs before a real order can fill (documented, not hidden):
  1. USDC on POLYGON (the founder's $ is on Base → needs a Base→Polygon bridge first).
  2. gate.py PASS (≥20 resolved paper trades, ≥55% win) — enforced here.
Base = BlockRunAI/polymarket-agent (create_or_derive_api_creds + create_and_post_order).
Usage: python3 order.py '<token_id>' <price> <size_usdc> <UP|DOWN>
"""
import json
import os
import sys

CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon
RPC_URL = os.getenv("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com")


def _load_key():
    """The AI's OWN Polygon/EVM key (same 0x810f address as Base). Never a human's key."""
    import pathlib
    p = pathlib.Path(os.path.expanduser("~/.anicca-founder/wallet.json"))
    k = json.loads(p.read_text()).get("private_key")
    if not k:
        raise RuntimeError("no private_key in ~/.anicca-founder/wallet.json")
    return k if k.startswith("0x") else "0x" + k


def main():
    if len(sys.argv) < 5:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "bad-args",
                          "usage": "order.py <token_id> <price> <size_usdc> <UP|DOWN>"}))
        return
    token_id, price, size_usdc, side = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4].upper()
    DRY = os.getenv("DRY_RUN", "true") != "false"
    EXEC = os.getenv("EARN_MODE") == "execute"
    GATE = os.getenv("PM_PAPER_PASS") == "1"
    plan = {"slot": "earn/pm-trade", "tool": "clob-order", "token": token_id[:16] + "…",
            "price": price, "size_usdc": size_usdc, "side": side}

    # money-safety: refuse a real order unless ALL gates hold
    if not (not DRY and EXEC and GATE):
        # DRY path — try to init the client + derive creds (read-only) to prove the path works
        try:
            from py_clob_client.client import ClobClient
            acct_key = _load_key()
            client = ClobClient(host=CLOB_HOST, chain_id=CHAIN_ID, key=acct_key)
            creds = client.create_or_derive_api_creds()
            ok = bool(creds)
            print(json.dumps({**plan, "decision": "DRY_RUN-ok" if ok else "DRY_RUN-nocreds",
                              "note": "client+CLOB creds derived (read-only); NO order posted",
                              "gates": {"dry": DRY, "exec": EXEC, "paper_pass": GATE}}))
        except ImportError:
            print(json.dumps({**plan, "decision": "needs-dep", "note": "pip install py-clob-client"}))
        except Exception as e:
            print(json.dumps({**plan, "decision": "DRY_RUN-initfail", "err": str(e)[:140]}))
        return

    # REAL path (all gates passed): place the order
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs
    from py_clob_client.order_builder.constants import BUY
    acct_key = _load_key()
    proxy = os.getenv("POLYMARKET_PROXY_WALLET")
    client = (ClobClient(host=CLOB_HOST, chain_id=CHAIN_ID, key=acct_key, signature_type=2, funder=proxy)
              if proxy else ClobClient(host=CLOB_HOST, chain_id=CHAIN_ID, key=acct_key))
    client.set_api_creds(client.create_or_derive_api_creds())
    shares = round(size_usdc / price, 2)
    resp = client.create_and_post_order(OrderArgs(token_id=token_id, price=price, size=shares, side=BUY))
    oid = (resp or {}).get("orderID") or (resp or {}).get("id")
    import pathlib
    lg = pathlib.Path(os.path.expanduser("~/loops/earn-pm-trade")); lg.mkdir(parents=True, exist_ok=True)
    row = {"src": "pm-trade", "action": "clob-order", "token_id": token_id, "side": side, "price": price,
           "size_usdc": size_usdc, "order_id": oid, "resp_status": (resp or {}).get("status")}
    with open(lg / "orders.jsonl", "a") as f:
        f.write(json.dumps({**row, "ts": int(__import__("time").time())}) + "\n")
    print(json.dumps({**plan, "decision": "ordered", "order_id": oid, "status": (resp or {}).get("status")}))


if __name__ == "__main__":
    main()
