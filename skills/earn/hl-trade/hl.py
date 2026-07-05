#!/usr/bin/env python3
"""hl.py — thin Hyperliquid perp TOOL (primitives only; NO decision logic).

Per HARD RULE #0: a skill gives the TOOL, never the decision. THIS FILE DECIDES NOTHING — it does not
pick a direction, a coin, a size, or a strategy. The MODEL (the Anicca running the loop, or Claude)
reads SKILL.md, looks at `account` + `market`, decides with its own judgment, and calls `open`/`close`
with the side/size IT chose. Do not add momentum/trend/"what worked" logic here.

Verified: a real risk-managed ETH long realized +$0.15 on this exact primitive (2026-06-20).
Works local AND cloud (pure hyperliquid-python-sdk over HTTPS). Funding: the wallet must already have
a Hyperliquid account funded with USDC (deposit via Arbitrum bridge — a separate one-time step).

Usage (the MODEL chooses every argument):
  python hl.py account
  python hl.py market ETH [hours]
  python hl.py open  ETH long  12   [--lev 2 --sl 3 --tp 6]     # side/size/risk = the model's call
  python hl.py open  ETH short 12   [--lev 2 --sl 3 --tp 6]
  python hl.py close ETH

Env: PKVAR / BLOCKRUN_WALLET_KEY / ~/.automaton/wallet.json (signing key).
"""
import argparse
import json
import os
import subprocess
import sys
import time

try:
    import eth_account
    from hyperliquid.info import Info
    from hyperliquid.exchange import Exchange
    from hyperliquid.utils import constants
except Exception as e:
    print(json.dumps({"error": "needs hyperliquid-python-sdk + eth_account: " + str(e)[:120]}))
    sys.exit(1)


def _key():
    # PKVAR names the env var that HOLDS the key (e.g. "BLOCKRUN_WALLET_KEY") — resolve it INDIRECTLY.
    # os.environ.get("PKVAR") would return the var NAME string, not the key → "Non-hexadecimal digit".
    pkvar = os.environ.get("PKVAR")
    k = (os.environ.get(pkvar) if pkvar else None) or os.environ.get("BLOCKRUN_WALLET_KEY")
    if not k:
        # #28: GATED per-instance resolution via the shared resolver CLI (EFFECTIVE_HOME first, legacy
        # only for the rightful owner, foreign spawn -> empty). NEVER read the shared $HOME wallet
        # directly — that let a foreign spawn sign HL trades with another instance's money key.
        ri = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "resolve-identity.mjs")
        try:
            k = subprocess.run(["node", ri, "evm"], capture_output=True, text=True, timeout=10).stdout.strip() or None
        except Exception:
            k = None
    if not k:
        sys.stderr.write("hl-trade: no per-instance EVM key resolvable (env / $ANICCA_HOME / owner-legacy) — refusing to sign\n")
        sys.exit(2)
    return k if k.startswith("0x") else "0x" + k


def _clients():
    w = eth_account.Account.from_key(_key())
    return w, Info(constants.MAINNET_API_URL, skip_ws=True), Exchange(w, constants.MAINNET_API_URL)


def cmd_account(args):
    w, info, _ = _clients()
    st = info.user_state(w.address)
    positions = [{"coin": p["position"]["coin"], "szi": p["position"]["szi"],
                  "entry": p["position"]["entryPx"], "uPnL": p["position"]["unrealizedPnl"]}
                 for p in st.get("assetPositions", []) if float(p["position"].get("szi", 0)) != 0]
    print(json.dumps({"address": w.address,
                      "account_value_usd": round(float(st["marginSummary"]["accountValue"]), 4),
                      "withdrawable_usd": round(float(st.get("withdrawable", 0)), 4),
                      "open_positions": positions}, indent=2))


def cmd_market(args):
    _, info, _ = _clients()
    coin = args.coin
    px = float(info.all_mids().get(coin, 0))
    end = int(time.time() * 1000)
    closes = []
    try:
        c = info.candles_snapshot(coin, "1h", end - args.hours * 3600 * 1000, end)
        closes = [round(float(x["c"]), 2) for x in c][-args.hours:]
    except Exception:
        pass
    meta = info.meta()
    a = next((m for m in meta["universe"] if m["name"] == coin), {})
    # raw data only — the MODEL interprets it and decides. No buy/sell recommendation here.
    print(json.dumps({"coin": coin, "price": px, "max_leverage": a.get("maxLeverage"),
                      "closes_hourly": closes,
                      "change_pct_window": (round((closes[-1] - closes[0]) / closes[0] * 100, 2)
                                            if len(closes) >= 2 else None)}, indent=2))


def cmd_open(args):
    w, info, ex = _clients()
    coin, side = args.coin, args.side.lower()
    if side not in ("long", "short"):
        print(json.dumps({"error": "side must be long|short"})); return
    is_buy = side == "long"
    st = info.user_state(w.address)
    for p in st.get("assetPositions", []):
        if p["position"]["coin"] == coin and float(p["position"].get("szi", 0)) != 0:
            print(json.dumps({"skipped": "position already open on " + coin, "szi": p["position"]["szi"]})); return
    px = float(info.all_mids().get(coin, 0))
    sz = round(max(10.5, args.notional) / px, 4)
    try:
        ex.update_leverage(int(args.lev), coin)
    except Exception:
        pass
    r = ex.market_open(coin, is_buy, sz, None, 0.01)
    fills = [s["filled"] for s in r.get("response", {}).get("data", {}).get("statuses", []) if "filled" in s]
    if not fills:
        print(json.dumps({"error": "open not filled", "raw": str(r)[:200]})); return
    entry = float(fills[0]["avgPx"])
    sl = round(entry * (1 - args.sl / 100) if is_buy else entry * (1 + args.sl / 100), 1)
    tp = round(entry * (1 + args.tp / 100) if is_buy else entry * (1 - args.tp / 100), 1)
    for px_t, tag in ((sl, "sl"), (tp, "tp")):
        try:
            ex.order(coin, not is_buy, sz, px_t, {"trigger": {"triggerPx": px_t, "isMarket": True, "tpsl": tag}}, reduce_only=True)
        except Exception:
            pass
    print(json.dumps({"opened": side, "coin": coin, "entry": entry, "size": sz,
                      "leverage": args.lev, "stop_loss": sl, "take_profit": tp}, indent=2))


def cmd_close(args):
    w, info, ex = _clients()
    # capture the position's unrealised PnL BEFORE closing — that becomes the realised PnL.
    pnl = 0.0
    try:
        pre = info.user_state(w.address)
        for ap in pre.get("assetPositions", []):
            p = ap.get("position", {})
            if p.get("coin") == args.coin:
                pnl = round(float(p.get("unrealizedPnl", 0) or 0), 4)
    except Exception:
        pass
    # No open position on this coin → market_close returns None/empty. Report cleanly instead of
    # crashing on r.get(...) (the AI often re-picks "close ETH" after it is already flat).
    r = ex.market_close(args.coin)
    time.sleep(2)
    st = info.user_state(w.address)
    status = r.get("status") if isinstance(r, dict) else "no_position"
    print(json.dumps({"closed": args.coin, "result": status,
                      "closed_pnl_usd": pnl,
                      "account_value_usd": round(float(st["marginSummary"]["accountValue"]), 4)}, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("account").set_defaults(fn=cmd_account)
    m = sub.add_parser("market"); m.add_argument("coin"); m.add_argument("hours", nargs="?", type=int, default=12); m.set_defaults(fn=cmd_market)
    o = sub.add_parser("open"); o.add_argument("coin"); o.add_argument("side"); o.add_argument("notional", type=float)
    o.add_argument("--lev", type=int, default=2); o.add_argument("--sl", type=float, default=4); o.add_argument("--tp", type=float, default=8); o.set_defaults(fn=cmd_open)
    c = sub.add_parser("close"); c.add_argument("coin"); c.set_defaults(fn=cmd_close)
    a = p.parse_args()
    a.fn(a)
