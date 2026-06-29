#!/usr/bin/env bash
# clip monitor — OBSERVE how the clip accounts are doing + whether they're MAKING MONEY.
# Read-only. Reports: posts in ledger, total recorded USDC, live reel view counts per account,
# and the founder wallet balances. Honest: "earned" counts ONLY real on-chain USDC (record-earn);
# per-view reward USDC is $0 until a payout-check confirms an external inflow (CLIP-E).
set -uo pipefail
HOME_DIR="${HOME}"
LEDGER="${EARN_LEDGER:-$HOME_DIR/.openclaw/state/clip-earn-ledger.jsonl}"
ACCTS="$HOME_DIR/.cloak/clip-accounts.json"
CDP_DIR="$HOME_DIR/.claude/skills/ig-account-create/scripts"
PY=/opt/homebrew/bin/python3
SOL_WALLET="xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H"

echo "===== CLIP MONITOR $(date '+%Y-%m-%d %H:%M %Z') ====="

# 1) ledger: posts + recorded earnings
if [ -f "$LEDGER" ]; then
  "$PY" - "$LEDGER" <<'PYL'
import json,sys
posts=0; earn=0.0; urls=[]
for ln in open(sys.argv[1]):
    ln=ln.strip()
    if not ln: continue
    try: d=json.loads(ln)
    except: continue
    if d.get("post_url"): posts+=1; urls.append(d["post_url"])
    earn+=float(d.get("earn_usdc",0) or 0)
print(f"posts recorded : {posts}")
print(f"USDC earned    : ${earn:.2f}  (real on-chain inflow only; $0 until a campaign payout lands)")
for u in urls[-5:]: print(f"  - {u}")
PYL
else
  echo "posts recorded : 0 (no ledger yet)"
fi

# 2) live reel view counts per ready account (best-effort; needs the isolated browser up+logged-in)
echo "--- live reel views per account ---"
"$PY" - "$ACCTS" <<'PYA' 2>/dev/null | while read -r HANDLE PORT; do
import json,sys
try: a=json.load(open(sys.argv[1]))
except Exception: a=[]
for x in a:
    print(x.get("handle",""), x.get("port",9222))
PYA
  TID=$(curl -sS --max-time 4 "http://localhost:${PORT}/json/list" 2>/dev/null | "$PY" -c 'import json,sys
try: d=json.load(sys.stdin)
except: d=[]
ps=[t for t in d if t.get("type")=="page"]
print(ps[0]["id"] if ps else "")' 2>/dev/null)
  if [ -z "$TID" ]; then echo "  @${HANDLE}: browser not up on :${PORT} (no live view data)"; continue; fi
  CDP_PORT="$PORT" "$PY" - "$TID" "$HANDLE" "$CDP_DIR" <<'PYV' 2>/dev/null
import sys,os,time
sys.path.insert(0,sys.argv[3]); import cdp
tid,handle=sys.argv[1],sys.argv[2]
try:
    cdp.navigate(tid,f"https://www.instagram.com/{handle}/"); time.sleep(5)
    posts=cdp.evaluate(tid,"(()=>{const m=document.body.innerText.match(/(\\d+)\\s*投稿/);return m?m[1]:'?'})()")
    views=cdp.evaluate(tid,"(()=>[...document.querySelectorAll('main a[href*=\"/reel/\"] span,main ul li span')].map(s=>(s.textContent||'').trim()).filter(t=>/^[\\d.,]+[万KMB]?$/.test(t)).slice(0,5))()")
    print(f"  @{handle}: {posts} posts | reel view labels: {views}")
except Exception as e:
    print(f"  @{handle}: read failed ({e!r:.40})")
PYV
done

# 3) founder wallet balances (where campaign USDC would land)
echo "--- founder wallet (where campaign USDC lands) ---"
SOL=$(curl -sS --max-time 8 "https://api.mainnet-beta.solana.com" -X POST -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"getTokenAccountsByOwner\",\"params\":[\"$SOL_WALLET\",{\"mint\":\"EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v\"},{\"encoding\":\"jsonParsed\"}]}" 2>/dev/null | "$PY" -c 'import json,sys
try:
    d=json.load(sys.stdin); accs=d.get("result",{}).get("value",[])
    print(sum(float(a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0) for a in accs) if accs else 0)
except Exception: print("?")' 2>/dev/null)
echo "  Solana USDC ($SOL_WALLET): ${SOL:-?}"
echo "============================================="
