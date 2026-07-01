#!/usr/bin/env python3
"""pm-paper.py — Polymarket CLOB PAPER-trade battle-test (read-only, NO key, NO real money).

Proves the trading loop's MECHANICS on live Polymarket data before any real stake (HARD 0.31 + the
paper-first mandate in the trading-polymarket spec). The MODEL decides which market/side/size (passed
in as args) — this tool is pure mechanics: read the live book, simulate a fill at the touch, record a
paper position, and mark it to market. No hardcoded strategy (build-agents rule).

Data (no auth, browser UA required):
  Gamma  https://gamma-api.polymarket.com/markets   — active markets, prices, clobTokenIds
  CLOB   https://clob.polymarket.com/book?token_id= — live order book (bids/asks)

Actions:
  discover [N]                 — list N contested (0.2–0.8) high-liquidity markets + their touch
  paper-buy <token_id> <usdc>  — simulate a BUY fill at best ask, record a paper position
  mark                         — mark all open paper positions to the current mid, print unrealized PnL

Paper ledger: ~/loops/earn-pm-trade/paper-positions.jsonl (append-only). Real side-effects = none.
"""
import json, sys, time, urllib.request, os, pathlib

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145 Safari/537.36"}
GAMMA = "https://gamma-api.polymarket.com/markets"
CLOB = "https://clob.polymarket.com/book?token_id="
LEDGER = pathlib.Path(os.path.expanduser("~/loops/earn-pm-trade/paper-positions.jsonl"))


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25))


def book(token_id):
    b = get(CLOB + token_id)
    bids, asks = b.get("bids") or [], b.get("asks") or []
    best_bid = float(bids[-1]["price"]) if bids else None
    best_ask = float(asks[-1]["price"]) if asks else None
    mid = (best_bid + best_ask) / 2 if (best_bid and best_ask) else None
    return {"best_bid": best_bid, "best_ask": best_ask, "mid": mid,
            "bid_depth": len(bids), "ask_depth": len(asks)}


def markets(limit=60):
    return get(f"{GAMMA}?active=true&closed=false&order=volume24hr&ascending=false&limit={limit}")


def discover(n=5):
    out = []
    for m in markets():
        try:
            px = json.loads(m.get("outcomePrices") or "[]")
            toks = json.loads(m.get("clobTokenIds") or "[]")
        except (ValueError, TypeError):
            continue
        if not (px and toks):
            continue
        if 0.2 <= float(px[0]) <= 0.8:   # contested = a real forecasting edge is possible
            out.append({"question": m.get("question"), "token_id": toks[0],
                        "gamma_price": float(px[0]), "vol24h": m.get("volume24hr")})
        if len(out) >= n:
            break
    print(f"[pm-paper] {len(out)} contested markets (0.2–0.8, high vol). The model picks + forms an edge:")
    for o in out:
        bk = book(o["token_id"])
        print(f"  • {o['question'][:58]:<58} px={o['gamma_price']:.3f} "
              f"mid={bk['mid']} spr={round((bk['best_ask'] or 0)-(bk['best_bid'] or 0),4)} "
              f"vol24h=${int(o['vol24h'] or 0):,} tok={o['token_id'][:10]}…")
    return out


def paper_buy(token_id, usdc):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    bk = book(token_id)
    if not bk["best_ask"]:
        print("no ask — cannot fill"); return 1
    entry = bk["best_ask"]                 # a taker BUY fills at best ask
    shares = usdc / entry                   # CTF outcome shares held
    row = {"ts": int(time.time()), "mode": "paper", "token_id": token_id, "side": "BUY",
           "size_usdc": usdc, "entry_price": entry, "shares_held": round(shares, 4),
           "mid_at_entry": bk["mid"], "status": "open"}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[pm-paper] PAPER BUY {usdc} USDC @ {entry} → {shares:.2f} shares "
          f"(mid {bk['mid']}, cost basis ${usdc}); recorded to {LEDGER}")
    return 0


def mark():
    if not LEDGER.exists():
        print("no paper positions"); return 0
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    opens = [r for r in rows if r.get("status") == "open"]
    print(f"[pm-paper] marking {len(opens)} open paper positions to live mid:")
    tot = 0.0
    for r in opens:
        bk = book(r["token_id"])
        mtm = bk["mid"] or bk["best_bid"]
        if mtm is None:
            print(f"  • {r['token_id'][:10]}… no quote"); continue
        # value now = shares × current mid; cost = size_usdc; unrealized = value − cost
        val = r["shares_held"] * mtm
        pnl = val - r["size_usdc"]
        tot += pnl
        print(f"  • {r['token_id'][:10]}… entry={r['entry_price']} now={mtm:.4f} "
              f"shares={r['shares_held']} value=${val:.2f} cost=${r['size_usdc']} "
              f"unrealized={'+' if pnl>=0 else ''}{pnl:.4f} USDC")
    print(f"[pm-paper] total unrealized paper PnL: {'+' if tot>=0 else ''}{tot:.4f} USDC")
    return 0


def main():
    a = sys.argv[1:]
    if not a or a[0] == "discover":
        discover(int(a[1]) if len(a) > 1 else 5)
    elif a[0] == "paper-buy":
        return paper_buy(a[1], float(a[2]))
    elif a[0] == "mark":
        return mark()
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
