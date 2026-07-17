# Fix: [Travel] block noise (home→home) + retire legacy travel systems — VCSDD

Date: 2026-06-19 | worktree `../anicca-lm-travelfix` / `fix/lm-travel-noise`

## RED (reproduced with live evidence)

Dais's real calendar has **31 `[Travel]` blocks**, including ones before at-home activities
(😴 Sleep, 🧘 Meditation, 🏃 Running) whose `location` IS his home (新宿区南元町15-27). No travel is
needed for home→home. **Every** bogus block's description is `Auto-inserted by Anicca B-travel
(spec27…)` — i.e. the **LEGACY** travel system, NOT the cloud life-call `travel.js` (whose description
is `Auto-inserted by Anicca Life Manager …`).

Two legacy travel jobs are still enabled and duplicate the cloud loop:
- Netlify scheduled function `life-travel` — `0 21 * * *` (netlify.toml)
- OpenClaw cron `anicca-travel-fill` — `0 5 * * *` (jobs.json)

The cloud `travel.js` already has the correct guard (`norm(origin) === norm(ev.location)` → skip), so
it does NOT create home→home blocks. The legacy B-travel lacks that guard.

## SPEC (correct behavior)

1. Exactly ONE travel system: the cloud life-call `travel.js` loop (every 30 min). Legacy retired.
2. A `[Travel]` block is inserted ONLY when real travel is required:
   - event has a real `location`, AND
   - it is not one of Anicca's own helper blocks, AND
   - the origin (previous event's location if back-to-back ≤90 min, else home) is KNOWN, AND
   - origin ≠ event location (normalized) — **home→home / same-place ⇒ NO block**.
3. The travel decision is a PURE, unit-tested function (`travelDecision`) so the guard can't regress.

## Plan (build → verify)

| # | Step | Verify |
|---|---|---|
| 1 | Extract `travelDecision(ev, prev, home)` pure fn in travel.js; fillTravel uses it | unit test (node --test) RED→GREEN: home→home skip, no-location skip, office→home insert, far-prev⇒home |
| 2 | Disable legacy: netlify.toml `life-travel` schedule + openclaw `anicca-travel-fill` cron | grep shows disabled; cron not in active list |
| 3 | Delete the 31 bogus `[Travel]` blocks from Dais's calendar (Composio) | re-list → 0 `[Travel]` (or only genuine office→home ones) |
| 4 | No-mock E2E: run cloud `travelTick` for Dais → it does NOT recreate home→home blocks | live: travelTick inserted count for home activities = 0 |
| 5 | Adversarial gate: fresh-context `vcsdd:vcsdd-adversary` reviews the guard + retirement | binary PASS |

## Out of scope
Legacy notify crons (anicca-life-notify-scan/poll) → retired with WS6g (#60).
