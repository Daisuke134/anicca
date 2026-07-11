"""test_gig_ts_parser.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-029 / REQ-GFV-021 (rewritten, spec-review iteration-2 BLOCKING-1 fix) — a pure, gig-specific
timestamp parser in `cadence-evidence.py` that converts a `~/gig/applied.jsonl`/`~/gig/listings.jsonl`
row's `ts` field to a JST calendar-date string, tolerating BOTH a numeric UNIX epoch (matching the
EXISTING `_epoch_to_jst_date` convention used by clip/affiliate/video) AND an ISO-8601 string (with
`Z` suffix or an explicit `+HH:MM`/`-HH:MM` offset) — measured this session: 258/269 real
`applied.jsonl` rows carry `ts` as an ISO-8601 string. Design contract this test locks in:
    cadence_evidence._gig_ts_to_jst_date(ts) -> str | None
Never crashes on null/missing/unparseable input -> returns None (skipped, same tolerant-parse
convention as every other ledger reader in this codebase).

This test does NOT modify the EXISTING shared `_epoch_to_jst_date`/`_event_dates_from_ts_rows`
functions (clip/affiliate/video, numeric-epoch-only) — loaded here only to prove they stay
byte-identical in behavior (regression pin), never touched by this new gig-specific function.

`cadence-evidence.py` does not export `_gig_ts_to_jst_date` yet -> AttributeError -> RED.
"""
import datetime
import importlib.util
import os
import sys
import zoneinfo

_SELF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SELF_DIR)
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


parse = CE._gig_ts_to_jst_date  # RED: AttributeError, does not exist yet

# a numeric-epoch row -> correct JST date (2026-07-08 12:55:37 JST = epoch below)
epoch_jst_noon = datetime.datetime(2026, 7, 8, 12, 55, 37, tzinfo=JST).timestamp()
chk("numeric-epoch ts -> correct JST date", parse(epoch_jst_noon), "2026-07-08")

# ISO-8601 Z-suffixed row (UTC) -> correct JST date (2026-07-08T12:55:37Z = 21:55:37 JST same day)
chk("ISO-8601 Z-suffixed ts -> correct JST date",
    parse("2026-07-08T12:55:37.000000Z"), "2026-07-08")

# ISO-8601 offset-suffixed row -> correct JST date (already +09:00, no shift)
chk("ISO-8601 +09:00-offset ts -> correct JST date",
    parse("2026-06-29T17:00:00+09:00"), "2026-06-29")

# an ISO-8601 UTC timestamp just before JST midnight rollover: verifies real timezone conversion,
# not a naive string-slice of the date portion (2026-07-08T15:30:00Z = 2026-07-09T00:30:00 JST)
chk("ISO-8601 Z ts near JST midnight rolls to the NEXT JST calendar day (real tz conversion)",
    parse("2026-07-08T15:30:00Z"), "2026-07-09")

chk("null ts -> None, never crash", parse(None), None)
chk("missing ts (empty string) -> None, never crash", parse(""), None)
chk("unparseable string ts -> None, never crash", parse("not-a-timestamp-at-all"), None)

# regression pin (found live 2026-07-11, gig-cadence self-fix session): a bash-written row can quote
# a UNIX epoch as a JSON STRING of digits (`"ts":"$(date +%s)"`) rather than an ISO string or a bare
# JSON number — this must resolve the same as the numeric-epoch case, not silently return None.
epoch_str = str(int(datetime.datetime(2026, 7, 11, 21, 22, 38, tzinfo=JST).timestamp()))
chk("digit-only STRING epoch ts -> correct JST date (bash `\"ts\":\"$(date +%s)\"` convention)",
    parse(epoch_str), "2026-07-11")

# regression pin: the EXISTING numeric-only helper is untouched by this feature.
existing_epoch_jst = CE._epoch_to_jst_date(epoch_jst_noon)
chk("regression: existing _epoch_to_jst_date (clip/affiliate/video) still works unchanged",
    existing_epoch_jst, "2026-07-08")

print(f"=== test_gig_ts_parser: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
