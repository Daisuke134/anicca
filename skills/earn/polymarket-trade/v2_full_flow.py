import os, json, base64, datetime
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
load_dotenv("/Users/anicca/.anicca-founder/agents/polymarket-agent/.env")
KEY=os.getenv("POLYGON_WALLET_PRIVATE_KEY"); KEY=KEY if KEY.startswith("0x") else "0x"+KEY
acct=Account.from_key(KEY); ADDR=acct.address
TID="102051736436656560797672629859737891705962543111476656351708851920203673046762"
PUSD="0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
NEG_EXCH="0xe2222d279d744050d28e00520010520000310F59"
NEG_ADAPTER="0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
def mint():
    s=requests.Session(); s.headers.update({"User-Agent":"Mozilla/5.0","Origin":"https://polymarket.com","Referer":"https://polymarket.com/"})
    nonce=s.get("https://gamma-api.polymarket.com/nonce",timeout=20).json()["nonce"]
    iss=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.")+f"{datetime.datetime.now(datetime.timezone.utc).microsecond//1000:03d}Z"
    f={"domain":"polymarket.com","address":ADDR,"statement":"Welcome to Polymarket! Sign to connect.","uri":"https://polymarket.com","version":"1","chainId":137,"nonce":nonce,"issuedAt":iss}
    pt=f"polymarket.com wants you to sign in with your Ethereum account:\n{ADDR}\n\n{f['statement']}\n\nURI: https://polymarket.com\nVersion: 1\nChain ID: 137\nNonce: {nonce}\nIssued At: {iss}"
    sig="0x"+acct.sign_message(encode_defunct(text=pt)).signature.hex()
    b=base64.b64encode((json.dumps(f,separators=(",",":"))+":::"+sig).encode()).decode()
    s.get("https://gamma-api.polymarket.com/login",headers={"Authorization":"Bearer "+b},timeout=20)
    return s.post("https://relayer-v2.polymarket.com/relayer/api/auth",json={},timeout=20).json()["apiKey"]
from polymarket.clients.secure import SecureClient
from polymarket.auth import RelayerApiKey
tmp=SecureClient._create(private_key=KEY,validate_credentials=True); creds=tmp._ctx.credentials; tmp.close()
c=SecureClient.create(private_key=KEY,credentials=creds,api_key=RelayerApiKey(key=mint(),address=ADDR))
for sp in [NEG_EXCH, NEG_ADAPTER]:
    ba=c.get_balance_allowance(asset_type="COLLATERAL")
    if int(ba.allowances.get(sp,0))<1:
        print("approving pUSD ->", sp)
        h=c.approve_erc20(token_address=PUSD, spender_address=sp, amount="max")
        try: h.wait()
        except Exception as e: print("wait:",e)
print("allowances:", c.get_balance_allowance(asset_type="COLLATERAL").allowances)
ob=c.get_order_book(token_id=TID); asks=getattr(ob,'asks',[])
ba=min(float(getattr(a,'price',None) or a['price']) for a in asks) if asks else 0.58
o=c.create_market_order(token_id=TID, side="BUY", amount="1", max_price=str(round(ba+0.03,3)), order_type="FAK")
print("posting REAL order (max_price",round(ba+0.03,3),")...")
resp=c.post_order(o)
print("POST RESULT:", resp)
c.close()
