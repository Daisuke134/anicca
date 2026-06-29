"""Live (no-mock) test of onchain.confirm_usdc_inflow against a REAL Base USDC transfer.
Real tx (Base mainnet): 0xce52f06ffb1b09d4189925a261f174b1d642ee7f5dfbdd0c3d14733630e7006c
  → to 0xe9030014f5dae217d0a152f02a043567b16c1abf, amount 0.01333 USDC.
Requires network (read-only Base RPC). Fail-closed behaviour is what we assert."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from onchain import confirm_usdc_inflow

TX = "0xce52f06ffb1b09d4189925a261f174b1d642ee7f5dfbdd0c3d14733630e7006c"
RCV = "0xe9030014f5dae217d0a152f02a043567b16c1abf"
AMT = 0.01333

# real transfer, correct recipient + amount → confirmed
assert confirm_usdc_inflow({"tx_hash": TX, "amount": AMT}, recipient=RCV) is True, "real matching transfer must confirm"
print("ok confirm real USDC transfer (to RCV, 0.01333)")
# correct tx but WRONG recipient (e.g. our founder wallet was not the recipient) → reject
assert confirm_usdc_inflow({"tx_hash": TX, "amount": AMT}, recipient="0x0000000000000000000000000000000000000001") is False, "wrong recipient must reject"
print("ok reject wrong recipient")
# correct tx + recipient but WRONG amount → reject (no amount spoofing)
assert confirm_usdc_inflow({"tx_hash": TX, "amount": 999.0}, recipient=RCV) is False, "wrong amount must reject"
print("ok reject wrong amount")
# garbage tx hash → reject (fail-closed)
assert confirm_usdc_inflow({"tx_hash": "0xdead", "amount": AMT}, recipient=RCV) is False, "bad tx must reject"
print("ok reject bad tx_hash")
# no tx hash → reject
assert confirm_usdc_inflow({"amount": AMT}, recipient=RCV) is False, "missing tx must reject"
print("ok reject missing tx_hash")
print("ALL ONCHAIN TESTS PASSED")
