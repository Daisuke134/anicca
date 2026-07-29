"""test_cadence_evidence.py — Tier2 integration test for cadence-evidence.py (REQ-LV-104 §H,
sprint-2 gap noted in Phase 5 hardening review). cadence.py itself (cadence_met/streak) is pure and
already covered by test_cadence.py's Tier1 suite (23/23 green, untouched here). This file proves
the IMPURE evidence-gathering side (gather_evidence/evidence_by_date_for_streak/status_for_loop)
correctly reads REAL temp fixture files — via the module's own test-only env var override seams
(EARN_LEDGER/AFFILIATE_METRICS_PATH/EARN_VIDEO_METRICS_PATH/GIG_FUNNEL_PATH/BOUNTY_FUNNEL_PATH/
FOUNDER_STATE_MD_PATH/PM_EARNER_LOG_PATH/PM_EARNER_LEDGER_PATH — the same
EARN_LEDGER/FOUNDER_DIR/FOUNDER_TEST pattern this codebase already uses elsewhere) — never touches
production paths (~/.cloak, ~/gig, ~/.anicca-founder, __REPO_ROOT__/skills/earn/...).
"""
import datetime
import importlib.util
import json
import os
import sys
import tempfile
import time
import zoneinfo

_SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SELF_DIR)  # so cadence-evidence.py's own `from cadence import ...` resolves
_spec = importlib.util.spec_from_file_location("cadence_evidence", os.path.join(_SELF_DIR, "cadence-evidence.py"))
CE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CE)

JST = zoneinfo.ZoneInfo("Asia/Tokyo")

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


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


TMP = tempfile.mkdtemp()
TODAY = datetime.datetime.now(tz=JST).date().isoformat()
today_epoch = datetime.datetime.now(tz=JST).timestamp()

# ---------------------------------------------------------------------------
# row-exists loops (clip/affiliate/video/gig): real jsonl row with today's ts -> event_dates
# includes today -> cadence_met via the real cadence.py dispatcher.
# ---------------------------------------------------------------------------
clip_ledger = os.path.join(TMP, "clip-ledger.jsonl")
write_jsonl(clip_ledger, [{"ts": today_epoch, "post_url": "https://example.com/reel1"}])
os.environ["EARN_LEDGER"] = clip_ledger
status = CE.status_for_loop("clip")
chk("clip: real today-ts row -> met=true", status["met"], True)
chk("clip: real today-ts row -> streak>=1", status["streak"] >= 1, True)
del os.environ["EARN_LEDGER"]

aff_metrics = os.path.join(TMP, "affiliate-metrics.jsonl")
write_jsonl(aff_metrics, [{"ts": today_epoch, "views": 100}])
os.environ["AFFILIATE_METRICS_PATH"] = aff_metrics
status = CE.status_for_loop("affiliate")
chk("affiliate: real today-ts row -> met=true", status["met"], True)
del os.environ["AFFILIATE_METRICS_PATH"]

video_metrics = os.path.join(TMP, "video-metrics.jsonl")
write_jsonl(video_metrics, [])  # empty -> no event_dates -> not met
os.environ["EARN_VIDEO_METRICS_PATH"] = video_metrics
os.environ["EARN_VIDEO_STATE_PATH"] = os.path.join(TMP, "video-state-absent.json")  # no file -> status!='warming'
status = CE.status_for_loop("video")
chk("video: empty ledger, not warming -> met=false (honest, never fabricated)", status["met"], False)
del os.environ["EARN_VIDEO_METRICS_PATH"]
del os.environ["EARN_VIDEO_STATE_PATH"]

# video during onboarding warmup (state.status=='warming'): self-heal.md root cause #1 — commit
# ab4a39a4 (a self-fix pass) made ANY S1_warmup audit line satisfy cadence, including "INCOMPLETE
# ... day NOT advanced". Real production data (~/.cloak/earn-video-audit-money_blueprintdaily.jsonl)
# proved this a Goodhart bug: state.warmup_day sat at 4 for 4 straight days (07-08..07-11) while this
# read ✅posted-today (streak=2) the whole time. The GUARDED EXIT-CRITERIA fix (cadence-evidence.py)
# requires the day to have ACTUALLY ADVANCED (a real 'day→N' line), never merely "attempted".
video_state_warming = os.path.join(TMP, "video-state-warming.json")
with open(video_state_warming, "w") as f:
    json.dump({"status": "warming", "warmup_day": 4}, f)

# --- regression-lock: the EXACT real production `did` strings quoted in self-heal.md (2026-07-11
# incident) must classify correctly — this is the fixture a future self-fix pass must not be able
# to quietly flip back to met=true without breaking this test. ---
video_metrics_incomplete = os.path.join(TMP, "video-metrics-incomplete.jsonl")
write_jsonl(video_metrics_incomplete, [])
video_audit_incomplete = os.path.join(TMP, "video-audit-incomplete.jsonl")
write_jsonl(video_audit_incomplete, [
    {"date": TODAY, "handle": "money_blueprintdaily", "transition": "S1_warmup",
     "did": "warmup INCOMPLETE: only 0 real views (<3) — day NOT advanced", "earned_usdc": 0.0},
])
os.environ["EARN_VIDEO_METRICS_PATH"] = video_metrics_incomplete
os.environ["EARN_VIDEO_STATE_PATH"] = video_state_warming
os.environ["EARN_VIDEO_AUDIT_PATH"] = video_audit_incomplete
status = CE.status_for_loop("video")
chk("video: warming + REAL 'day NOT advanced' line (2026-07-11 prod incident) -> met=false "
    "(Goodhart fix — attempt alone no longer satisfies cadence)", status["met"], False)
del os.environ["EARN_VIDEO_METRICS_PATH"]
del os.environ["EARN_VIDEO_STATE_PATH"]
del os.environ["EARN_VIDEO_AUDIT_PATH"]

# video during warmup with a REAL advance (the exact success-path template run.sh writes,
# skills/earn/video/run.sh: DID="warmup day→$(wday) (real reels watched=$WATCHED)") must satisfy
# cadence — the exit-criteria check is "did the day advance", not "was there zero activity".
video_metrics_advanced = os.path.join(TMP, "video-metrics-advanced.jsonl")
write_jsonl(video_metrics_advanced, [])
video_audit_advanced = os.path.join(TMP, "video-audit-advanced.jsonl")
write_jsonl(video_audit_advanced, [
    {"date": TODAY, "handle": "money_blueprintdaily", "transition": "S1_warmup",
     "did": "warmup day→4 (real reels watched=4)", "earned_usdc": 0.0},
])
os.environ["EARN_VIDEO_METRICS_PATH"] = video_metrics_advanced
os.environ["EARN_VIDEO_STATE_PATH"] = video_state_warming
os.environ["EARN_VIDEO_AUDIT_PATH"] = video_audit_advanced
status = CE.status_for_loop("video")
chk("video: warming + real 'day→N' advance line -> met=true (genuine progress still passes)",
    status["met"], True)
del os.environ["EARN_VIDEO_METRICS_PATH"]
del os.environ["EARN_VIDEO_STATE_PATH"]
del os.environ["EARN_VIDEO_AUDIT_PATH"]

# video during warmup with a TRUE stall (no S1_warmup line at all today) must still read as unmet —
# the fix must not paper over a genuinely dead loop (the real 07-02..07-07 / 07-09 stalls).
video_metrics3 = os.path.join(TMP, "video-metrics3.jsonl")
write_jsonl(video_metrics3, [])
video_audit_empty = os.path.join(TMP, "video-audit-empty.jsonl")
write_jsonl(video_audit_empty, [])
os.environ["EARN_VIDEO_METRICS_PATH"] = video_metrics3
os.environ["EARN_VIDEO_STATE_PATH"] = video_state_warming
os.environ["EARN_VIDEO_AUDIT_PATH"] = video_audit_empty
status = CE.status_for_loop("video")
chk("video: warming + zero attempts today -> met=false (a real stall still gets caught)", status["met"], False)
del os.environ["EARN_VIDEO_METRICS_PATH"]
del os.environ["EARN_VIDEO_STATE_PATH"]
del os.environ["EARN_VIDEO_AUDIT_PATH"]

# FIX (pre-existing baseline failure, confirmed present on origin/main before this file's other
# 2026-07-11 edits — see ab4a39a4's own commit message): this assertion used to set GIG_FUNNEL_PATH,
# but cadence-evidence.py's gig evidence source moved to GIG_APPLIED_PATH/GIG_LISTINGS_PATH
# (_gig_row_exists_event_dates, REQ-GFV-022/023 — _gig_funnel_path() itself documents "no longer
# used by the `gig` cadence-evidence path below"). The old fixture therefore always fed an env var
# gather_evidence("gig") never reads, so this always failed regardless of real gig behavior (which
# IS correctly covered end-to-end by test_cadence_evidence_gig_branch.py / test_gig_cadence_real_
# evidence.py, both green). Updated to the CURRENT override seam so this assertion exercises the
# real code path again, needed for the self-heal.md FIND-001 pre-push gate (skills/self/tests/
# test_cadence_evidence.py must genuinely pass end-to-end for that gate to be usable at all).
gig_applied = os.path.join(TMP, "gig-applied.jsonl")
gig_listings = os.path.join(TMP, "gig-listings.jsonl")
write_jsonl(gig_applied, [{"ts": today_epoch, "requestId": "R1", "status": "applied"}])
write_jsonl(gig_listings, [])
os.environ["GIG_APPLIED_PATH"] = gig_applied
os.environ["GIG_LISTINGS_PATH"] = gig_listings
status = CE.status_for_loop("gig")
chk("gig: real today-ts 'applied' row (current GIG_APPLIED_PATH source) -> met=true", status["met"], True)
del os.environ["GIG_APPLIED_PATH"]
del os.environ["GIG_LISTINGS_PATH"]

# ---------------------------------------------------------------------------
# bounty (increment kind): today's checked value must be STRICTLY greater than the prior day's,
# not merely present — proves the real bounty-funnel.jsonl reader feeds cadence.py's increment
# branch correctly (this is the exact "row exists != healthy" bug class the whole feature exists
# to fix, now proven end-to-end through the real file reader, not just the pure dispatcher).
# ---------------------------------------------------------------------------
yesterday = (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=1)).isoformat()
yesterday_epoch = datetime.datetime.combine(
    datetime.date.fromisoformat(yesterday), datetime.time(12, 0), tzinfo=JST
).timestamp()
bounty_funnel = os.path.join(TMP, "bounty-funnel.jsonl")
write_jsonl(bounty_funnel, [
    {"ts": yesterday_epoch, "checked": 10},
    {"ts": today_epoch, "checked": 15},
])
os.environ["BOUNTY_FUNNEL_PATH"] = bounty_funnel
status = CE.status_for_loop("bounty")
chk("bounty: checked increased 10->15 -> met=true", status["met"], True)
del os.environ["BOUNTY_FUNNEL_PATH"]

write_jsonl(bounty_funnel, [
    {"ts": yesterday_epoch, "checked": 10},
    {"ts": today_epoch, "checked": 10},
])
os.environ["BOUNTY_FUNNEL_PATH"] = bounty_funnel
status = CE.status_for_loop("bounty")
chk("bounty: checked flat 10->10 (row exists, no increment) -> met=false", status["met"], False)
del os.environ["BOUNTY_FUNNEL_PATH"]

# ---------------------------------------------------------------------------
# founder-loop (pass-marker kind): STATE.md's real mtime, ledger NOT consulted (proves the "empty
# ledger day is not the same as pass-didn't-run" design decision holds through the real file
# reader too).
# ---------------------------------------------------------------------------
founder_state = os.path.join(TMP, "STATE.md")
os.makedirs(os.path.dirname(founder_state), exist_ok=True)
with open(founder_state, "w") as f:
    f.write("realised_earn_usdc: 0\n")  # zero-earn day; mtime alone must still count as "ran"
os.environ["FOUNDER_STATE_MD_PATH"] = founder_state
status = CE.status_for_loop("founder-loop")
chk("founder-loop: STATE.md written today (even zero-earn) -> met=true", status["met"], True)
del os.environ["FOUNDER_STATE_MD_PATH"]

# ---------------------------------------------------------------------------
# pm-earner (compound: recency AND row-exists): real earner.log mtime (just-touched -> within
# max_age_min) AND a real today-ts redeem row in the ledger -> both sub-conditions true -> met.
# ---------------------------------------------------------------------------
earner_log = os.path.join(TMP, "earner.log")
with open(earner_log, "w") as f:
    f.write("pass ok\n")
os.utime(earner_log, (time.time(), time.time()))  # just-touched, well within the 40min window
pm_ledger = os.path.join(TMP, "pm-earn-ledger.jsonl")
write_jsonl(pm_ledger, [{"ts": today_epoch, "source": "polymarket-redeem", "amount": 1.5}])
os.environ["PM_EARNER_LOG_PATH"] = earner_log
os.environ["PM_EARNER_LEDGER_PATH"] = pm_ledger
status = CE.status_for_loop("pm-earner")
chk("pm-earner: fresh earner.log AND today redeem row -> met=true (compound AND)", status["met"], True)
del os.environ["PM_EARNER_LOG_PATH"]
del os.environ["PM_EARNER_LEDGER_PATH"]

# pm-earner with a STALE earner.log (old mtime) but a real today redeem row -> compound AND must
# still fail (hourly-pass sub-condition false) — this is PROP-LV-040/G1's exact regression,
# end-to-end through the real evidence-gathering path this time.
old_log = os.path.join(TMP, "earner-stale.log")
with open(old_log, "w") as f:
    f.write("pass ok\n")
old_time = time.time() - 3600 * 3  # 3h ago, well past the 40min max_age_min
os.utime(old_log, (old_time, old_time))
os.environ["PM_EARNER_LOG_PATH"] = old_log
os.environ["PM_EARNER_LEDGER_PATH"] = pm_ledger
status = CE.status_for_loop("pm-earner")
chk("pm-earner: STALE earner.log (3h) AND today redeem row -> met=false (AND, not OR — G1 regression, end-to-end)",
    status["met"], False)
del os.environ["PM_EARNER_LOG_PATH"]
del os.environ["PM_EARNER_LEDGER_PATH"]

print(f"=== test_cadence_evidence: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
