import sys, os, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from state_io import load_or_init, update   # RED: state_io.py does not exist yet

d = tempfile.mkdtemp()
P = os.path.join(d, "earn-video-x.json")

# init: no file → fresh day-0
s = load_or_init(P, "x")
assert s["status"] == "warming" and s["warmup_day"] == 0, f"init: {s}"
print("ok init day-0")

# update is atomic + readable
update(P, {"warmup_day": 5, "status": "warming"})
assert json.load(open(P))["warmup_day"] == 5; print("ok update persists")

# a second update creates a .bak of the prior good state
update(P, {"warmup_day": 6})
assert os.path.exists(P + ".bak"), "bak should exist after 2nd write"
assert json.load(open(P + ".bak"))["warmup_day"] == 5, "bak holds prior good state"
print("ok .bak keeps prior good state")

# ★ FIND-702: corrupt primary → load_or_init RESTORES from .bak (NOT a silent day-0 reset) ★
open(P, "w").write('{"handle":"x","status":"war')   # truncated/corrupt
s = load_or_init(P, "x")
assert s["warmup_day"] == 5, f"corrupt should restore from bak (day5), got {s}"
print("ok corrupt-primary restored from .bak (progress preserved)")

# both primary AND bak gone → last-resort day-0 (never crash)
os.remove(P); os.remove(P + ".bak")
s = load_or_init(P, "x")
assert s["warmup_day"] == 0, f"no file+no bak → day-0: {s}"
print("ok last-resort day-0 when nothing recoverable")
print("ALL STATE-IO TESTS PASSED")
