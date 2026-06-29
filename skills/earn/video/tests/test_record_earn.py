import sys, os, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from record_earn import record_earn   # RED: record_earn.py does not exist yet

def fresh(): 
    fd, p = tempfile.mkstemp(suffix=".jsonl"); os.close(fd); open(p,"w").close(); return p

L = fresh()
# reject: non-USDC
r = record_earn({"token":"JPY","amount":1000,"direction":"in","tx_hash":"0xabc","verified":True}, L)
assert r[0]=="rejected", f"JPY should reject: {r}"; print("ok reject non-USDC")
# reject: zero amount
r = record_earn({"token":"USDC","amount":0,"direction":"in","tx_hash":"0x1","verified":True}, L)
assert r[0]=="rejected", f"zero should reject: {r}"; print("ok reject zero")
# reject: no tx_hash (e.g. "I posted" with no on-chain proof = NOT earned)
r = record_earn({"token":"USDC","amount":5,"direction":"in","verified":True}, L)
assert r[0]=="rejected", f"no-tx should reject: {r}"; print("ok reject no-tx (posted!=earned)")
# reject: not verified
r = record_earn({"token":"USDC","amount":5,"direction":"in","tx_hash":"0x2","verified":False}, L)
assert r[0]=="rejected", f"unverified should reject: {r}"; print("ok reject unverified")
# reject: bool amount (True == 1 in python — must NOT slip through as $1 earned)
r = record_earn({"token":"USDC","amount":True,"direction":"in","tx_hash":"0x9","verified":True}, L)
assert r[0]=="rejected", f"bool amount should reject: {r}"; print("ok reject bool amount")
# reject: outbound (direction != in) must not count as earned
r = record_earn({"token":"USDC","amount":5,"direction":"out","tx_hash":"0x8","verified":True}, L)
assert r[0]=="rejected", f"outbound should reject: {r}"; print("ok reject outbound")
# ★ FIND-503: verified:true flag ALONE (no on-chain confirmation) must be REJECTED (fail-closed, not spoofable) ★
r = record_earn({"token":"USDC","amount":4.2,"direction":"in","tx_hash":"0xDEAD","verified":True}, L)
assert r[0]=="rejected", f"verified-flag-alone should reject without on-chain check: {r}"; print("ok reject verified-flag-alone (fail-closed)")
# a CONFIRMED tx (on-chain check passes) records — simulate the detector's confirmation via injected stub
CONFIRMED = lambda e: True
r = record_earn({"token":"USDC","amount":4.2,"direction":"in","tx_hash":"0xDEAD","verified":True}, L, onchain_check=CONFIRMED)
assert r[0]=="recorded" and abs(r[1]-4.2)<1e-9, f"confirmed should record: {r}"; print("ok record on-chain-confirmed USDC", r)
# idempotent: same tx_hash again → duplicate, not double-counted
r = record_earn({"token":"USDC","amount":4.2,"direction":"in","tx_hash":"0xDEAD","verified":True}, L, onchain_check=CONFIRMED)
assert r[0]=="duplicate", f"dup should be duplicate: {r}"; print("ok idempotent duplicate")
lines = [l for l in open(L) if l.strip()]
assert len(lines)==1, f"ledger must have exactly 1 entry, got {len(lines)}"; print("ok ledger single entry")
print("ALL RECORD-EARN TESTS PASSED")
