#!/usr/bin/env python3
"""
Polymarket BASE STRATEGY #1 — MARKET MAKING (the swisstony/RN1 copy, no-human).
Post two-sided resting maker limit orders (post_only, fee 0) near the book on a
binary market: BUY YES near bid_yes + BUY NO near bid_no. YES+NO=1, so buying both
cheap = delta-neutral + captures spread; on rewards-enabled markets it also harvests
Polymarket's daily LP reward pool. This is the sustainable no-human alpha.

Earnings accrue over time (fills + daily reward), so a run posts/refreshes quotes;
realized P&L is read later from get_trades + reward payouts. Fail-closed by design.
"""
import os, json, base64, datetime, sys
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
load_dotenv("/Users/operator/.anicca-founder/agents/polymarket-agent/.env")

KEY = os.getenv("POLYGON_WALLET_PRIVATE_KEY"); KEY = KEY if KEY.startswith("0x") else "0x"+KEY
acct = Account.from_key(KEY); ADDR = acct.address
PUSD="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
SPENDERS=["0xE111180000d2663C0091e4f400237545B87B996B","0xe2222d279d744050d28e00520010520000310F59","0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"]

def mint_relayer_key():
    s=requests.Session(); s.headers.update({"User-Agent":"Mozilla/5.0","Origin":"https://polymarket.com","Referer":"https://polymarket.com/"})
    nonce=s.get("https://gamma-api.polymarket.com/nonce",timeout=20).json()["nonce"]
    iss=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")+f"{datetime.datetime.now(datetime.timezone.utc).microsecond//1000:03d}Z"
    f={"domain":"polymarket.com","address":ADDR,"statement":"Welcome to Polymarket! Sign to connect.","uri":"https://polymarket.com","version":"1","chainId":137,"nonce":nonce,"issuedAt":iss}
    pt=f"polymarket.com wants you to sign in with your Ethereum account:\n{ADDR}\n\n{f['statement']}\n\nURI: https://polymarket.com\nVersion: 1\nChain ID: 137\nNonce: {nonce}\nIssued At: {iss}"
    sig="0x"+acct.sign_message(encode_defunct(text=pt)).signature.hex()
    b=base64.b64encode((json.dumps(f,separators=(",",":"))+":::"+sig).encode()).decode()
    s.get("https://gamma-api.polymarket.com/login",headers={"Authorization":"Bearer "+b},timeout=20)
    return s.post("https://relayer-v2.polymarket.com/relayer/api/auth",json={},timeout=20).json()["apiKey"]

def pick_market():
    ms=requests.get("https://gamma-api.polymarket.com/markets?closed=false&active=true&order=volume24hr&ascending=false&limit=40",timeout=20).json()
    for m in ms:
        t=m.get("clobTokenIds")
        if not t or not m.get("enableOrderBook"): continue
        try: toks=json.loads(t) if isinstance(t,str) else t
        except: continue
        bb,ba=m.get("bestBid"),m.get("bestAsk")
        # prefer near-0.5 so BOTH YES-bid and NO-bid are affordable on small capital
        if len(toks)>=2 and bb and ba and 0.40<float(bb)<0.60 and (float(ba)-float(bb))<=0.05:
            return m.get("question","?"), str(toks[0]), str(toks[1]), float(bb), float(ba)
    return None

from polymarket.clients.secure import SecureClient
from polymarket.auth import RelayerApiKey

def main():
    tmp=SecureClient._create(private_key=KEY,validate_credentials=True); creds=tmp._ctx.credentials; tmp.close()
    c=SecureClient.create(private_key=KEY,credentials=creds,api_key=RelayerApiKey(key=mint_relayer_key(),address=ADDR))
    print("deposit wallet:",c._ctx.wallet)
    ba=c.get_balance_allowance(asset_type="COLLATERAL")
    print("pUSD balance:",int(ba.balance)/1e6)
    for sp in SPENDERS:
        if int(ba.allowances.get(sp,0))<1:
            c.approve_erc20(token_address=PUSD,spender_address=sp,amount="max").wait()
    pk=pick_market()
    if not pk: print("no market"); return 1
    q,yes,no,bb,ba_=pk
    print(f"MARKET: {q[:60]} | bid {bb} ask {ba_}")
    # two-sided maker: join the bid on YES, and on NO (=1-ask) — both post_only makers
    book_yes=c.get_order_book(token_id=yes)
    def best_bid(ob):
        bids=getattr(ob,'bids',[]) or []
        return max((float(getattr(b,'price',None) or b['price']) for b in bids), default=bb)
    def best_ask(ob):
        asks=getattr(ob,'asks',[]) or []
        return min((float(getattr(a,'price',None) or a['price']) for a in asks), default=ba_)
    by=round(best_bid(book_yes),3)
    book_no=c.get_order_book(token_id=no)
    bn=round(best_bid(book_no),3)
    try: c.cancel_all(); print("  cancel-and-replace: cleared old quotes")  # avoid stacking each loop pass
    except Exception as e: print("  cancel_all:", str(e)[:60])
    ba=c.get_balance_allowance(asset_type="COLLATERAL")
    MIN_SIZE=5      # Polymarket CLOB minimum order size = 5 shares
    avail=int(ba.balance)/1e6
    orders=[]
    for tid,px,lbl in [(yes,by,"BUY YES@bid"),(no,bn,"BUY NO@bid")]:
        cost=MIN_SIZE*px
        if cost>avail:
            print(f"  {lbl} SKIP: needs ${cost:.2f}, only ${avail:.2f} left (fund the deposit wallet to run BOTH sides + LP-reward size)")
            continue
        size=str(MIN_SIZE); avail-=cost
        try:
            o=c.create_limit_order(token_id=tid, price=str(px), size=size, side="BUY", post_only=True)
            r=c.post_order(o)
            print(f"  {lbl} {size}@{px} -> ok={getattr(r,'ok',None)} id={getattr(r,'order_id','')[:14]} status={getattr(r,'status','')}")
            orders.append(getattr(r,'order_id',None))
        except Exception as e:
            print(f"  {lbl} FAILED: {str(e)[:120]}")
    # verify resting
    for oid in orders:
        if oid:
            try:
                od=c.get_order(order_id=oid)
                print("  RESTING:", oid[:14], "size_matched:", getattr(od,'size_matched',None), "status:", getattr(od,'status',getattr(od,'order_status','?')))
            except Exception as e: print("  verify err:", str(e)[:80])
    c.close(); return 0

if __name__=="__main__":
    sys.exit(main())
