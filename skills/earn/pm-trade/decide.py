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
    """Return-so-far of the current 5-min BTC candle on Binance: (last - open)/open. Returns None on failure
    (network/parse) — the caller must treat None as 'cannot decide', never as 0 (FIND-006)."""
    try:
        k = get("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=1")
        o = float(k[0][1]); c = float(k[0][4])
        return (c - o) / o if o else 0.0
    except Exception:
        return None


def _iso_ms(s):
    """ISO8601 -> epoch ms, or None."""
    if not s:
        return None
    try:
        import datetime
        s = s.replace("Z", "+00:00")
        return int(datetime.datetime.fromisoformat(s).timestamp() * 1000)
    except Exception:
        return None


def _already_traded_window(ledger, window_end_ms):
    """Idempotency: true if ANY momentum row for this window_end already exists (ONE trade per window,
    regardless of side — a mid-window signal flip must not record both UP and DOWN; FIND-006). A None
    window_end is treated as 'cannot dedup' by the caller, which refuses to record at all (FIND-005)."""
    if not ledger.exists() or window_end_ms is None:
        return False
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("src") == "momentum" and r.get("window_end_ms") == window_end_ms:
            return True
    return False


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
            return {"yes": ay, "no": an, "question": m.get("question"), "token_yes": t[0],
                    "window_start_ms": _iso_ms(m.get("startDate")), "window_end_ms": _iso_ms(m.get("endDate"))}
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
    if wr is None:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "no-data", "note": "binance BTC fetch failed"}))
        return
    mk = find_btc_updown()
    if mk is None:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "no-market",
                          "btc_window_return": round(wr, 6), "note": "no live BTC up/down market found"}))
        return
    yes, no, question, tok = mk["yes"], mk["no"], mk["question"], mk["token_yes"]
    win_start, win_end = mk["window_start_ms"], mk["window_end_ms"]
    side, price, prob = momentum.side_and_prob(wr, yes, no)
    if side is None:
        print(json.dumps({"slot": "earn/pm-trade", "decision": "skip", "btc_window_return": round(wr, 6),
                          "yes": yes, "no": no, "question": question, "note": "no positive-edge side"}))
        return
    # momentum/latency edges are small + frequent (not big directional bets) -> lower min_edge than the
    # Kelly default 0.15; tune from paper results. gas_reserve keeps a buffer.
    MOM_MIN_EDGE = float(os.getenv("PM_MIN_EDGE", "0.03"))
    stake = lib.position_size(prob, price, bankroll, min_edge=MOM_MIN_EDGE, gas_reserve=0.5)
    decision = "paper-trade" if stake > 0 else "skip-below-min-edge"
    out = {"slot": "earn/pm-trade", "decision": decision, "side": side, "price": price,
           "est_prob": round(prob, 4), "edge": round(prob - price, 4), "stake_usdc": round(stake, 4),
           "btc_window_return": round(wr, 6), "bankroll": bankroll, "question": question}
    if stake > 0:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        if win_end is None:
            # cannot resolve a trade with no window end -> never record it (would orphan forever). FIND-005.
            out["recorded"] = False
            out["note"] = "no window_end_ms (unresolvable) -> not recorded"
        elif _already_traded_window(LEDGER, win_end):
            out["recorded"] = False
            out["note"] = "already traded this window (idempotent)"
        else:
            row = {"ts": int(time.time()), "src": "momentum", "mode": "paper", "token_id": tok, "side": side,
                   "size_usdc": round(stake, 4), "entry_price": price, "est_prob": round(prob, 4),
                   "question": question, "window_start_ms": win_start, "window_end_ms": win_end,
                   "status": "open"}
            with open(LEDGER, "a") as f:
                f.write(json.dumps(row) + "\n")
            out["recorded"] = True
    print(json.dumps(out))


if __name__ == "__main__":
    main()
