# PHY-runtime — the organ watches by itself; first scan measured, misread, then vindicated

Merged as #1147 (+ review fixes), first production scan 2026-07-26T11:57:30Z, 29 seconds after boot.

## What the first scan truthfully recorded

| field | value | meaning |
|---|---|---|
| history read | 703 calendar events over 548 days (verified by bit-for-bit replay) | complete |
| care-classified visits | 10 (6 clinic, 3 haircut, 1 dental) — `history_event_count` counts THESE, not raw events | correct semantics |
| detection | clinic, personal_interval_days=9, overdue_days=50, 6 source visits | honest math on real events |
| chain | 3 real Marunouchi clinics found (home+work anchors), one with a live web-reservation route | 11b machinery works on real data |

## Two admissions on the record

1. **My false alarm**: I declared the row a 誤検知 because `history_event_count=10` coincided with a
   CLI page cap and my probe saw unrelated events. The investigator killed all three of my hypotheses
   by replaying the exact production inputs and reproducing the row exactly. The row was never wrong.
   The proposed "invalidated" annotation was refused because it would have written a fabrication into
   an append-only audit table — the refusal was correct.
2. **The real latent bug** (found while disproving me): the transport dropped Composio's
   `nextPageToken`, so a big-enough calendar would have been silently truncated into the append-only
   log as truth. Fixed in #1149: cursor-walked single window, throwing `history_unavailable` on any
   truncation it cannot prove complete — no row, no claim, retry next tick. 34/34 tests, suite exit 0,
   including a pin test feeding the real event titles through the classifier.

## What stays open on 11a's path (new row CADENCE-1)

The 9-day interval is real arithmetic on a bimodal distribution: three visits inside ten weeks of
2025, fourteen months of silence, two visits in one week of 2026. A median of that is a burst, not a
cadence — and booking off it would be the actual false positive. The detector needs a stability
guard (e.g., dispersion bound or span coverage) before 11c may act on a detection.
