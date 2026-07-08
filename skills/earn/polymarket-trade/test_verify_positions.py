"""test_verify_positions.py — REQ-LV-017 daily verification wiring for pm-earner. Tier1-ish: an
injected fake `fetch` callable (no real network call) exercises build_url()/verify_positions()'s
real aggregation logic. positions.py::parse_positions_response itself (frozen, PROP-LV-006) is
unit-tested separately in test_positions.py — untouched here. A live, real-network smoke run
(`python3 verify_positions.py`) was also executed manually this session against the real
data-api.polymarket.com endpoint and returned a real (empty, honest) positions list — see
sprint-2 evidence log.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_positions import build_url, verify_positions  # noqa: E402

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


WALLET = "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74"

chk("build_url: contains data-api host + wallet param",
    "data-api.polymarket.com/positions" in build_url(WALLET) and WALLET in build_url(WALLET), True)

multi = json.dumps([
    {"conditionId": "0xc8a0", "title": "Wimbledon Men's Final", "currentValue": 10.0, "redeemable": True},
    {"conditionId": "0xabc1", "title": "US Election 2028", "currentValue": 2.5, "redeemable": False},
])
r = verify_positions(WALLET, fetch=lambda url, timeout: multi)
chk("verify_positions: real-shaped 2-position response -> positions_count=2", r["positions_count"], 2)
chk("verify_positions: only the redeemable=true row counted -> redeemable_count=1", r["redeemable_count"], 1)
chk("verify_positions: wallet echoed back", r["wallet"], WALLET)
chk("verify_positions: no error key on success", "error" in r, False)

r_empty = verify_positions(WALLET, fetch=lambda url, timeout: "[]")
chk("verify_positions: empty positions -> 0/0, no fabrication", (r_empty["positions_count"], r_empty["redeemable_count"]), (0, 0))

def _raise(url, timeout):
    raise TimeoutError("connection timed out")

r_fail = verify_positions(WALLET, fetch=_raise)
chk("verify_positions: fetch raises -> fail-closed 0/0 with error recorded",
    (r_fail["positions_count"], r_fail["redeemable_count"], "error" in r_fail), (0, 0, True))

print(f"=== test_verify_positions: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
