# 12c — all three MENTAL triggers delivered over real Telegram, read back from production

Done condition: real TG deliveries for the three schedule-derived triggers. All three now exist as
rows in the production `lm_mental_send_log`, read back over the Supabase REST API on 2026-07-26.

| trigger | TG message id | sent_at (UTC) | how it came to fire |
|---|---|---|---|
| `pre_event` | `260` | 2026-07-25 09:20:51 | fired on its own after the 12c wiring deploy |
| `pre_sleep` | `271` | 2026-07-25 13:30:16 | fired on its own at 22:30 JST against the resolved sleep target |
| `between_events` | `272` | 2026-07-25 18:49:11 | fired 11 seconds after a real 90-minute calendar block ended — after the reachability fix below |

## between_events required a production fix (PR #1129, merged 2026-07-26)

The trough trigger fires on an intense block that **already ended** within 30 minutes. The tick
fetched the calendar with `timeMin = now`, so an ended event could never be in the list — the rule
was correct and unreachable. Proven by inserting a real 90-minute event into the real calendar and
watching nothing fire (monitored to timeout against the production DB).

Fix: the tick's single fetch now looks back 35 minutes (`MENTAL_LOOKBACK_MS`), and only the MENTAL
organ receives the widened list; late-notice, wake levels, and departure resolution are pinned by
test to the strict-future slice (`lib/mental-lookback-wiring.test.js`). A review finding (malformed
`end.dateTime` parsing to NaN skipping the window filter) was fixed before merge with boundary tests.

After the deploy, a fresh real 90-minute event ending five minutes prior was inserted; the trigger
fired 11 seconds after the event's end — which doubles as deploy verification, since the old code
could not produce this row at all.

## Honesty notes

- The two `LM-12C` test events were real calendar rows in the real primary calendar (the E2E-spec
  method), and were deleted after the pass; readback shows 0 remaining.
- `pre_event` and `pre_sleep` fired on organic schedule data with no test scaffolding.
- The daily cap (3/day) and 2-hour spacing held throughout: the three sends span 9.5 hours.
