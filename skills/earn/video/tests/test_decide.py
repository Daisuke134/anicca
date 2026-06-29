import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from decide import decide   # RED: decide.py does not exist yet

T = "2026-06-29"
def eq(got, want, label):
    assert got == want, f"FAIL {label}: got {got!r} want {want!r}"
    print(f"ok {label}: {got}")

# S0: no account → create
eq(decide({}, T), "S0_create", "empty->create")
eq(decide({"status": "none"}, T), "S0_create", "none->create")
# S1: warming, day<7, not warmed today → warmup
eq(decide({"status": "warming", "warmup_day": 0}, T), "S1_warmup", "warming0->warmup")
eq(decide({"status": "warming", "warmup_day": 6}, T), "S1_warmup", "warming6->warmup")
# idempotent: already warmed today → noop (bounded, no double action)
eq(decide({"status": "warming", "warmup_day": 3, "last_warmup_date": T}, T), "noop", "warmed-today->noop")
# S2: day>=7 and affiliate not set → set affiliate link IN-LOOP (the deferred step)
eq(decide({"status": "warming", "warmup_day": 7, "affiliate_set": False}, T), "S2_affiliate", "day7-nolink->affiliate")
eq(decide({"status": "warmed", "warmup_day": 9, "affiliate_set": False}, T), "S2_affiliate", "warmed-nolink->affiliate")
# S3: warmed + affiliate set + not posted today → post
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_set": True, "last_post_date": "2026-06-28"}, T), "S3_post", "warmed-notposted->post")
# S4: posted today → record earn (only path left)
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_set": True, "last_post_date": T}, T), "S4_record", "posted-today->record")
eq(decide({"status": "monetized", "warmup_day": 30, "affiliate_set": True, "last_post_date": T}, T), "S4_record", "monetized-posted->record")
# S2 dead-end fix: no link yet → run.sh sets affiliate_pending → machine ADVANCES to post (never stuck on S2)
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_pending": True, "affiliate_set": False, "last_post_date": "2026-06-28"}, T), "S3_post", "pending->post-not-stuck")
eq(decide({"status": "warmed", "warmup_day": 9, "affiliate_pending": True, "affiliate_set": False, "last_post_date": "2026-06-28"}, T), "S3_post", "pending-warmed->post")
# but if a link IS available (not pending, not set) it still fires S2
eq(decide({"status": "warmed", "warmup_day": 7, "affiliate_pending": False, "affiliate_set": False}, T), "S2_affiliate", "available->affiliate")
print("ALL DECIDE TESTS PASSED")
