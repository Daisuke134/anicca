# Connector Connpass existing-first recovery Item 14H plan

## Goal

Return an exact in-window Connpass event whose public detail says `registered` before new available candidates, so the parent can read it back and finish missing evidence without another Submit.

## Measured root cause

- Recovery wake `wake-8073885e011beebea1bfc0da` recorded Connpass audit `6/6/6/5/1` but did not enter a Connpass candidate readback/action; it continued to Peatix and ended without a Connpass receipt or bundle.
- After the successful registration, current public detail for event `400028` normalizes to `registration_status=registered`, `ticket_price_status=free`, exact event identity and interval.
- A read-only isolated run of the same production Calendar reader and Connpass workflow returned zero candidates. Its current audit became `6/6/6/4/0`: the workflow admits only `registration_status=available`, so a registered event is removed before parent recovery.

## Ponytail full gate

- Reuse the normalized detail, candidate window, provider ordering, parent pre-readback, evidence chain, and current audit. Add no receipt lookup, attempt state, DB, cache, browser action, or new module.
- Change only the existing Connpass workflow and its test.
- An exact candidate with `registration_status=registered` and a start inside the current 14-day window is recovery-only: stable-partition it before available candidates and bypass the new-registration free/open/Calendar conflict gates. The runner's pre-readback still independently verifies provider state before evidence.
- Available candidates keep every existing free/open/zero-price/Calendar rule and their mutual order.
- Closed/unknown/non-window/malformed candidates remain excluded or fail closed as before. Do not reinterpret them as registered.
- Keep `free_open_count` as the available free/open count. `calendar_free_count` remains the returned-candidate count, now including exact registered recovery rows, consistent with the existing aggregate's operational meaning.

## Luna implementation slice

Ownership:

1. `apps/mr-bot/lib/connector-connpass-workflow.js`
2. `apps/mr-bot/lib/connector-connpass-workflow.test.js`

Soft target: 2 files; production net `+4–15 LOC`; tests `+25–50 LOC`.

### RED

1. One registered and two available eligible rows return registered first, then available rows in original order; candidate objects remain unchanged.
2. Registered recovery bypasses Calendar conflict evaluation and is returned even when its interval overlaps a normal busy event; available overlap remains blocked.
3. Registered outside the 14-day window, closed/unknown, malformed, and available paid/open-conflicted rows remain excluded/fail closed under existing contracts.
4. Audit free-open count excludes registered recovery while calendar-free count equals returned result length.

### GREEN and verification

- Add one `registeredExisting` partition in the current loop and concatenate it before the existing eligible result.
- Run focused workflow plus runner/production/Harness/provider/RSVP/evidence regressions, syntax, diff check.
- Fresh Sol review verifies no new Submit path, stable order, window binding, Calendar bypass only for already registered, audit semantics, and test non-vacuity.
- Commit/push before one official recovery wake. Acceptance: same wake Luma no-effect, Connpass registered pre-readback, cache/direct/Harness Submit all 0, one Connpass receipt/artifact, one Calendar event/readback, positive Telegram message/photo/report IDs, one applied bundle, cleanup.

## Result

- RED reproduced registered omission, Calendar-bypass absence, and aggregate mismatch at 11/14. GREEN stable-partitions in-window registered rows immediately after the window gate.
- Registered recovery bypasses only available-only price/open/Calendar checks; available order and gates remain unchanged. Diff: production 7/2, tests 50/0 plus one test-only real-interval fixture refinement.
- Luna and Sol independently passed 144/144, syntax, and diff check. Pushed commits `2a4809974` and `39775a5f6`.
- Actual production Calendar reader + workflow read-only proof returned audit `6/6/6/4/1` and exact registered event `400028` as the sole candidate, with writes 0.
- Fresh Sol review: `ship`, Critical 0, Important 0. Schedule remains unloaded; the official bundle recovery is next.
