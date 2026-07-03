#!/usr/bin/env python3
"""decide.py — the WIRING (fixes adversary FIND-001/002): reads live Binance BTC + the Polymarket BTC
up/down market, calls momentum.side_and_prob for the edge and lib.position_size for the stake, and emits a
one-line decision JSON. Effectful SHELL only (network); all judgment is in the pure momentum.py/lib.py.
In paper mode it records a paper position; it NEVER signs or places a real order (that lives in the gated
real executor, not here). Usage: python3 decide.py [bankroll_usdc]
"""
import json
import os
import sys
import time
import urllib.request
import pathlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
import momentum

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/145 Safari/537.36"}
LEDGER = pathlib.Path(os.path.expanduser("~/loops/earn-pm-trade/paper-positions.jsonl"))


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))


def btc_window_return():
    """Return-so-far of the current 5-min BTC candle on Binance: (last - open)/open."""
    k = get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=1")
    o = float(k[0][1]); c = float(k[0][4])
    return (c - o) / o if o else 0.0


def find_btc_updown():
    """Find an active Polymarket BTC up/down market; return (yes_ask, no_ask, question, token_yes) or None."""
    # The 5-min BTC up/down series has low individual volume → find it by NEWEST (startDate desc),
    # not by volume (verified 2026-07-04: e.g. "Bitcoin Up or Down - July 4, 12:25PM-12:30PM ET").
    for _ in range(1):
        try:
            ms = get("https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=100&order=startDate&ascending=false")
        except Exception:
            continue
        for m in ms:
            ql = (m.get("question") or m.get("slug") or "").lower()
            if "bitcoin" not in ql and "btc" not in ql:
                continue
            if "up or down" not in ql:
                continue
            t = m.get("clobTokenIds")
            if isinstance(t, str):
                try:
                    t = json.loads(t)
                except Exception:
                    continue
            if not t or len(t) < 2:
                continue
            ay = _best_ask(t[0]); an = _best_ask(t[1])
            if ay is None or an is None:
                continue
            return (ay, an, m.get("question"), t[0])
    return None


def _best_ask(tok):
    try:
        b = get("https://clob.polymarket.com/book?token_id=" + str(tok))
        a = b.get("asks") or []
        return min(float(x["price"]) for x in a) if a else None
    except Exception:
        return None


def main():
    bankroll = float(sys.argv[1]) if len(sys.argv) > 1 else float(os.getenv("PM_BANKROLL", "8"))
    wr = btc_window_return()
    mk = find_btc_updown()
    if mk is None:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "no-market",
                          "btc_window_return": round(wr, 6), "note": "no live BTC up/down market found"}))
        return
    yes, no, question, tok = mk
    side, price, prob = momentum.side_and_prob(wr, yes, no)
    if side is None:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "skip", "btc_window_return": round(wr, 6),
                          "yes": yes, "no": no, "question": question, "note": "no positive-edge side"}))
        return
    stake = lib.position_size(prob, price, bankroll)
    out = {"slot": "earn/pm-trade", "decision": "paper-trade", "side": side, "price": price,
           "est_prob": round(prob, 4), "edge": round(prob - price, 4), "stake_usdc": round(stake, 4),
           "btc_window_return": round(wr, 6), "bankroll": bankroll, "question": question}
    if stake > 0:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": int(time.time()), "mode": "paper", "token_id": tok, "side": side,
               "size_usdc": round(stake, 4), "entry_price": price, "est_prob": round(prob, 4),
               "question": question, "status": "open"}
        with open(LEDGER, "a") as f:
            f.write(json.dumps(row) + "\n")
        out["recorded"] = True
    print(json.dumps(out))


if __name__ == "__main__":
    main()
