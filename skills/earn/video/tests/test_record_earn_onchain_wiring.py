"""test_record_earn_onchain_wiring.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-008 / REQ-LV-080 (P0-4) — record_earn.py's `verify_onchain(entry)` MUST stop being the
hardcoded-False stub and be wired to a real Base RPC log-filter check equivalent to
onchain.py::confirm_usdc_inflow (already implemented + already tested, tests/test_onchain.py) /
record-earn.mjs's parseRawLogs+sumExternal pattern: only a log from the correct USDC contract, the
correct Transfer topic0, and the correct `to`-topic is treated as a real inflow; other contracts'
logs are ignored; amount mismatches are rejected.

This test proves the WIRING, not the RPC logic itself (that purity is already covered by
tests/test_onchain.py, unchanged/reused). Today `record_earn.verify_onchain` unconditionally
returns False for ANY entry — this test uses the exact same real Base-mainnet tx that
tests/test_onchain.py already proves onchain.confirm_usdc_inflow accepts, and asserts
record_earn.verify_onchain must ALSO accept it once wired (currently: hardcoded False -> FAILS,
RED). ★ PROP-LV-009 (existing stub-injection regression, tests/test_record_earn.py) is UNCHANGED
by this wiring — that test is not touched or duplicated here. ★
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import record_earn  # existing module; verify_onchain is currently a hardcoded-False stub

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


# same real Base mainnet tx tests/test_onchain.py already proves confirm_usdc_inflow accepts
TX = "0xce52f06ffb1b09d4189925a261f174b1d642ee7f5dfbdd0c3d14733630e7006c"
RCV = "0xe9030014f5dae217d0a152f02a043567b16c1abf"
AMT = 0.01333

entry_matching = {"tx_hash": TX, "amount": AMT, "token": "USDC", "direction": "in", "verified": True}
os.environ["EARN_VIDEO_RECIPIENT"] = RCV
chk("verify_onchain: real matching Base USDC transfer -> True (wired, not the old hardcoded stub)",
    record_earn.verify_onchain(entry_matching), True)

entry_wrong_amount = {"tx_hash": TX, "amount": 999.0, "token": "USDC", "direction": "in", "verified": True}
chk("verify_onchain: correct tx but wrong amount -> False (amount mismatch rejected)",
    record_earn.verify_onchain(entry_wrong_amount), False)

entry_bad_tx = {"tx_hash": "0xdeadbeef", "amount": AMT, "token": "USDC", "direction": "in", "verified": True}
chk("verify_onchain: garbage tx_hash -> False (fail-closed, no crash)",
    record_earn.verify_onchain(entry_bad_tx), False)

entry_no_tx = {"amount": AMT, "token": "USDC", "direction": "in", "verified": True}
chk("verify_onchain: missing tx_hash -> False",
    record_earn.verify_onchain(entry_no_tx), False)

print(f"=== test_record_earn_onchain_wiring: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
