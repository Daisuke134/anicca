# BROWSER-MATRIX-1 evidence (in progress)

Live acceptance (3/3 provider legs) is NOT complete. This file records the
bounded evidence gathered so far, newest last. SSOT: spec §0.4.6a.

## 1. Verifier ownership correction (Task 3a) — 2026-07-30

| Item | Value |
|---|---|
| PR | #1361, merged as canonical main `569cf748e23d3a1de880791a3f6ad79ed621f0a5` |
| Harness change | enqueue-only + bounded terminal polling; `browser-job-runtime` / `claimBrowserJobById` / executor dependency removed (source-scan test asserts absence) |
| Tests | RED-first 8 fail → harness 9/9, `test:browser-auth` 47/47, full `npm test` chain exit 0, OSS boundary PASS, security CI 7/7 |
| Railway | deployment `7ea230f6-f8f4-41f6-8310-b6ae324d1d52` `SUCCESS` at the exact merge SHA |
| Boot log | `[life-call] browser jobs ON (Railway private Steel)` |
| Plan docs | #1362 (Task 3a evidence), #1365 (fixture wording aligned to spec As-Is/To-Be) |

## 2. Resident-loop ownership probe (production, zero side effect) — 2026-07-30

One read-only job was enqueued from inside the deployed `life-call` container
(`enqueueBrowserJob` + `readBrowserJob` only; the probe never claimed and never
called any executor). The resident production browser loop claimed and ran it.

| Item | Value |
|---|---|
| Durable job | `8cdd6942-6443-44c9-80c0-d33baa9b57fb`, tenant `lm_784ad…` (bounded) |
| Claim owner | resident loop — trace `queued → claimed (+5s) → discovery → telegram_sent → steel_released` |
| Verifier direct execution | 0 (enqueue + poll only) |
| Steel session | `219ecae7-1dfa-4e1d-b602-0557c53ecfb1`, `released=true` |
| Telegram evidence | message `483` |
| Outcome | `failed`, `side_effect_started=false`, production log `browser discovery did not reach a specific action page` |

Reading: the probe goal was intentionally read-only, so the runtime's
fail-closed refusal (no fabricated success, honest failure receipt, session
released) is the desired MUST-7 behavior. This probe demonstrates the
spec §0.4.6a MUST-1/MUST-2 ownership mechanics live (resident claim, verifier
poll-only, release, honest terminal receipt). The three real provider legs
(booking / inquiry / application) remain pending and are the done-gate.
