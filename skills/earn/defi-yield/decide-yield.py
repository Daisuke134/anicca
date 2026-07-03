#!/usr/bin/env python3
"""yield.py — DeFi yield earn slot driver. DEFAULT = DRY_RUN plan (money-safe: reads live DefiLlama pools +
this wallet's USDC balance, picks the pool via pure lib.pick_pool, sizes via lib.size_supply, and PRINTS the
supply plan — it does NOT sign or supply). The real Aave/Spark `supply()` is the gated real-money increment
(EARN_MODE=execute + a wired signer), intentionally not present yet (fail-closed). Usage: python3 yield.py
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145 Safari/537.36"}
USDC_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))


def wallet_usdc(addr):
    """Live Base USDC balance for addr (RPC eth_call balanceOf), or None."""
    try:
        a = addr.lower().replace("0x", "")
        data = "0x70a08231" + "0" * 24 + a
        body = {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                "params": [{"to": USDC_BASE, "data": data}, "latest"]}
        hdrs = {"content-type": "application/json", **UA}
        r = urllib.request.Request("https://mainnet.base.org", data=json.dumps(body).encode(), headers=hdrs)
        hexv = json.load(urllib.request.urlopen(r, timeout=20)).get("result", "0x0")
        return int(hexv, 16) / 1e6
    except Exception:
        return None


def main():
    addr = os.getenv("PM_WALLET", "0x810f6d61f7606deee2657d3083e150a222bc29c5")
    try:
        pools = get("https://yields.llama.fi/pools").get("data", [])
    except Exception:
        print(json.dumps({"slot": "earn/defi-yield", "decision": "no-data", "note": "defillama fetch failed"}))
        return
    base_usdc = [p for p in pools if p.get("chain") == "Base"]
    pick = lib.pick_pool(base_usdc)
    if pick is None:
        print(json.dumps({"slot": "earn/defi-yield", "decision": "no-pool", "note": "no qualifying Base USDC pool"}))
        return
    bal = wallet_usdc(addr)
    if bal is None:
        print(json.dumps({"slot": "earn/defi-yield", "decision": "no-balance", "pool": pick["project"]}))
        return
    supply = lib.size_supply(bal)
    plan = {"slot": "earn/defi-yield", "decision": "plan" if supply > 0 else "skip-too-small",
            "pool": pick["project"], "apy_pct": round(pick.get("apy", 0), 2),
            "tvl_usd": pick.get("tvlUsd"), "pool_id": pick.get("pool"),
            "wallet_usdc": round(bal, 4), "supply_usdc": round(supply, 4),
            "est_daily_usdc": round(supply * (pick.get("apy", 0) / 100.0) / 365.0, 6),
            "mode": "DRY_RUN — no supply signed (real supply is the gated increment)"}
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
