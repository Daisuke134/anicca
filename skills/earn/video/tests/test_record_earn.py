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
# record: real USDC inflow
r = record_earn({"token":"USDC","amount":4.2,"direction":"in","tx_hash":"0xDEAD","verified":True}, L)
assert r[0]=="recorded" and abs(r[1]-4.2)<1e-9, f"valid should record: {r}"; print("ok record real USDC", r)
# idempotent: same tx_hash again → duplicate, not double-counted
r = record_earn({"token":"USDC","amount":4.2,"direction":"in","tx_hash":"0xDEAD","verified":True}, L)
assert r[0]=="duplicate", f"dup should be duplicate: {r}"; print("ok idempotent duplicate")
lines = [l for l in open(L) if l.strip()]
assert len(lines)==1, f"ledger must have exactly 1 entry, got {len(lines)}"; print("ok ledger single entry")
print("ALL RECORD-EARN TESTS PASSED")
