#!/usr/bin/env python3
"""
Polymarket BASE STRATEGY #1 — MAKER BUNDLE / MARKET MAKING (no-human).
On a binary market YES+NO resolves to exactly $1. If we rest BUY YES @ yes_bid and
BUY NO @ no_bid with yes_bid+no_bid < 1, then IF BOTH fill we locked a risk-free
profit (paid <$1 for a guaranteed $1). We spread quotes across several markets to
raise the odds both legs of at least one bundle fill. cancel-and-replace each pass.
Fee-aware; only quotes bundles with a positive margin. Fail-closed.
"""
import os, json, sys
import requests
from eth_account import Account
from dotenv import load_dotenv
load_dotenv("/Users/anicca/.anicca-founder/agents/polymarket-agent/.env")

KEY=os.getenv("POLYGON_WALLET_PRIVATE_KEY"); KEY=KEY if KEY.startswith("0x") else "0x"+KEY
acct=Account.from_key(KEY); ADDR=acct.address
PUSD="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
SPENDERS=["0xE111180000d2663C0091e4f400237545B87B996B","0xe2222d279d744050d28e00520010520000310F59","0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"]
MIN_SIZE=5           # CLOB min order = 5 shares
MAX_MARKETS=3        # spread across up to 3 markets
MARGIN=0.995         # require yes_bid+no_bid <= 0.995 (locked >=0.5% if both fill)
MAX_PASS_SPEND=float(os.getenv("MAX_PASS_SPEND","2.0"))  # fixed USD ceiling per pass (money-safety, #25 adversary fix)

# ROOT CAUSE FIX (2026-07-07): this used to carry its own mint() that POSTed a brand-new
# relayer key every pass -> hit Polymarket's 100-keys-per-address cap on 2026-07-04 ->
# every pass since crashed with KeyError:'apiKey' (error body has no apiKey field). Now
# reuses the SAME list-before-mint + cached implementation redeem.py already proved live
# (see relayer_auth.py docstring) instead of a second, drifting copy.
from relayer_auth import mint_relayer_api_key
def mint(): return mint_relayer_api_key(acct)

from polymarket.clients.secure import SecureClient
from polymarket.auth import RelayerApiKey

def best_bid(ob):
    bids=getattr(ob,'bids',[]) or []
    if not bids: return None
    return max(float(getattr(b,'price',None) or b['price']) for b in bids)

def main():
    tmp=SecureClient._create(private_key=KEY,validate_credentials=True); creds=tmp._ctx.credentials; tmp.close()
    c=SecureClient.create(private_key=KEY,credentials=creds,api_key=RelayerApiKey(key=mint(),address=ADDR))
    try: c.cancel_all(); print("  cancel-and-replace: cleared old quotes")
    except Exception as e: print("  cancel_all:", str(e)[:60])
    ba=c.get_balance_allowance(asset_type="COLLATERAL"); avail=int(ba.balance)/1e6
    print("deposit wallet pUSD:", avail)
    # BALANCE FLOOR (adversary fix): a two-sided min-size bundle costs ~MIN_SIZE*1.0 pUSD.
    # If we can't afford even one bundle, HOLD this pass instead of spamming failed orders.
    if avail < MIN_SIZE * 1.0:
        print(f"  HOLD: cash ${avail:.2f} < one min bundle (~${MIN_SIZE*1.0:.2f}). "
              f"Not placing (positions will free cash on resolution). No churn.")
        c.close(); return 0
    for sp in SPENDERS:
        if int(ba.allowances.get(sp,0))<1: c.approve_erc20(token_address=PUSD,spender_address=sp,amount="max").wait()

    ms=requests.get("https://gamma-api.polymarket.com/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=50",timeout=25).json()
    picks=[]
    for m in ms:
        t=m.get("clobTokenIds")
        if not t or not m.get("enableOrderBook"): continue
        try: toks=json.loads(t) if isinstance(t,str) else t
        except: continue
        if len(toks)<2: continue
        try:
            by=best_bid(c.get_order_book(token_id=str(toks[0])))
            bn=best_bid(c.get_order_book(token_id=str(toks[1])))
        except Exception: continue
        if by is None or bn is None: continue
        s=by+bn
        if 0.20<by<0.80 and s<=MARGIN:   # profitable bundle if both fill
            picks.append((s, m.get("question","?"), str(toks[0]), str(toks[1]), round(by,3), round(bn,3)))
        if len(picks)>=MAX_MARKETS: break
    if not picks:
        print("no profitable maker-bundle market found this pass."); c.close(); return 0
    # MAX_PASS_SPEND: fixed USD ceiling for the TOTAL quoted across all markets this pass (in
    # addition to the avail*0.9 gate above, take the MIN) — bounds worst-case pass spend to a
    # fixed number regardless of wallet balance (#25 adversary fix).
    total_budget = min(avail*0.9, MAX_PASS_SPEND)
    per_market_budget = total_budget/len(picks)
    placed=0
    for s,q,yes,no,by,bn in picks:
        # size so both legs stay within this market's share of the fixed per-pass budget
        size = int(per_market_budget/(by+bn))
        if size < MIN_SIZE:
            print(f"MKT {q[:42]:42} HOLD: budget ${per_market_budget:.2f} < {MIN_SIZE} sh both legs "
                  f"(needs ${MIN_SIZE*(by+bn):.2f}). Skipping, no order placed.")
            continue
        size = min(size, 200)
        print(f"MKT {q[:42]:42} YES {by}+NO {bn}={s:.3f} lock {(1-s)*100:.1f}% -> {size} sh/leg")
        for tid,px in [(yes,by),(no,bn)]:
            try:
                o=c.create_limit_order(token_id=tid, price=str(px), size=str(size), side="BUY", post_only=True)
                r=c.post_order(o)
                print(f"    {'YES' if tid==yes else 'NO '} {size}@{px} ok={getattr(r,'ok',None)} status={getattr(r,'status','')} id={getattr(r,'order_id','')[:12]}")
                placed+=1
            except Exception as e:
                print(f"    leg FAILED: {str(e)[:90]}")
    print(f"placed {placed} maker legs across {len(picks)} markets. Bundle profit locks when both legs of a market fill.")
    c.close(); return 0

if __name__=="__main__":
    sys.exit(main())
