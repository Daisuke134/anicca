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
# ★ FIND-501: DAILY POST has PRIORITY over affiliate install — not-posted-today ALWAYS goes S3 first,
#   even when a link is available+unset, so posting is NEVER starved by a looping/failing S2. ★
eq(decide({"status": "warming", "warmup_day": 7, "affiliate_set": False, "affiliate_available": True}, T), "S3_post", "day7-link-avail-notposted->POST-first")
eq(decide({"status": "warmed", "warmup_day": 9, "affiliate_set": False, "affiliate_available": True}, T), "S3_post", "warmed-link-avail-notposted->POST-first")
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_available": True, "affiliate_set": False, "last_post_date": "2026-06-28"}, T), "S3_post", "link-avail-old-post->POST-first")
# S2 fires ONLY after today's post is already done (so the link installs/retries without starving posting)
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_available": True, "affiliate_set": False, "last_post_date": T}, T), "S2_affiliate", "posted-today+link-avail->affiliate")
# S3: warmed + affiliate set + not posted today → post
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_set": True, "last_post_date": "2026-06-28"}, T), "S3_post", "warmed-notposted->post")
# S4: posted today + (affiliate set OR no link) → record earn (only path left)
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_set": True, "last_post_date": T}, T), "S4_record", "posted-today-set->record")
eq(decide({"status": "monetized", "warmup_day": 30, "affiliate_set": True, "last_post_date": T}, T), "S4_record", "monetized-posted->record")
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_available": False, "affiliate_set": False, "last_post_date": T}, T), "S4_record", "posted-today-nolink->record")
# ★ D1: NO link available yet → S2 skipped, machine keeps POSTING ★
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_available": False, "affiliate_set": False, "last_post_date": "2026-06-28"}, T), "S3_post", "no-link->post-not-stuck")
eq(decide({"status": "warmed", "warmup_day": 9, "affiliate_set": False, "last_post_date": "2026-06-28"}, T), "S3_post", "no-link-key-absent->post")
# already set → never re-fires S2
eq(decide({"status": "warmed", "warmup_day": 8, "affiliate_available": True, "affiliate_set": True, "last_post_date": T}, T), "S4_record", "already-set-posted->record")
# ★ regression guard: status STILL "warming" at day7 + no link → must POST, not fall to S4 ★
eq(decide({"status": "warming", "warmup_day": 7, "affiliate_set": False}, T), "S3_post", "warming-day7-nolink->post-not-S4")
eq(decide({"status": "warming", "warmup_day": 7, "affiliate_set": False, "last_post_date": T}, T), "S4_record", "warming-day7-posted-today->record")
print("ALL DECIDE TESTS PASSED")
