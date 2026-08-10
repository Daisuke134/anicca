# Connector circuit-breaker Item 15 acceptance plan

## Goal

Accept the existing minimal Connector circuit breaker only from composed contract tests plus durable production evidence: three consecutive safe failures or ten elapsed minutes stop further browser work, preserve exact privacy-safe history, send a positive Telegram recovery report, and create no five-minute retry path.

## Ponytail full gate

- Do not add another circuit module, timer, retry queue, healthcheck, healer, schedule, or test framework.
- Reuse `connector-minimal-runner.js`, `connector-minimal-operations.js`, the single daily launchd renderer contract, their existing focused tests, and immutable official wake records.
- No live provider failure is induced: an artificial or deliberately destructive registration failure is not necessary because an existing official wake already reached the exact three-failure terminal boundary.
- Initial code/test LOC target is zero. If fresh review proves a missing deadline boundary, only the existing runner and its focused test may change; no new module or scheduler is allowed.

## Acceptance matrix

1. Runner fixture: three ordinary safe candidate failures produce one `circuit_open`, failure count three, no fourth candidate navigation, and one owned-page cleanup.
2. Deadline fixture: elapsed time above 600,000 ms produces `circuit_open / wake_deadline`, no fallback action, and one terminal report.
3. Safe history fixture: every action row contains only purpose, method, timestamp, result, and duration.
4. Operations fixture: a current circuit report is sent first, persists one positive Telegram provider ID, and remains idempotent without duplicating the current delivery.
5. Production schedule contract: render output contains exactly one daily Connector plist, no `StartInterval`, healthcheck, healer, bridge, `:9223`, or retry sidecar.
6. Durable live evidence: official wake `wake-a85aefe7a153ce0513e7d7df` is exactly `circuit_open / peatix_unknown_required_field / 3`; its delivery has positive Telegram ID `10868`; no provider registration, Calendar, PNG, or bundle effect occurred; owned page, process, and lock cleaned up.
7. Runtime observation: all four Connector-related labels remain unloaded through Item 16, no Connector process/lock exists, and no wake report appears in the five-minute window after the accepted live circuit report.

## Verify

- Run only the named runner, operations, and launchd contract tests above, then their full focused files.
- Read durable state fields only; do not expose event/private values.
- Fresh read-only Sol reviewer checks that the historical wake is from the current minimal runner lineage, the OR condition is satisfied by three failures, later actions are absent, Telegram delivery is positive, and no five-minute retry exists.
- If all pass, update Item 15 to complete, commit, and push. Keep every schedule unloaded and move immediately to Item 16.

## Result

- Initial focused runner/operations/launchd verification passed 33/33. Durable wake and delivery rows matched `circuit_open / peatix_unknown_required_field / 3` and positive Telegram ID `10868`; the five-minute follow-up report count was zero; four labels remained unloaded; process and lock were absent; the native template linted and contained no retry sidecar.
- Fresh Sol review returned `fix-first`, Critical 0 / Important 1. Independent fixtures showed Calendar observation and a zero-candidate provider discovery can consume 600,001 ms and still return `completed_no_effect`; the Calendar case also creates the browser target after the deadline. This violates the ten-minute branch and post-deadline target/action-zero contract.
- Revised implementation ownership is exactly `connector-minimal-runner.js` and its test. Luna must first reproduce both failures, then add deadline checks after long boundaries, including Calendar before target open, target open before provider actions, discovery before candidate handling/provider continuation, and any candidate browser/readback/action boundary that could otherwise start another action after expiry. In-flight operations are not cancelled or raced; existing bounded dependency timeouts finish normally, then the runner records one `circuit_open / wake_deadline`, performs only owned-page cleanup, and starts no later action.
- First fix RED was 24/28 and GREEN runner 28/28, minimal stack 73/73. Production added post-boundary guards without racing in-flight work and preserved completed evidence as `applied_bundle`.
- Sol re-review returned `fix-first`, Critical 0 / Important 1. When Calendar, browser open, candidate navigation, pre/post readback, or repaired-action save advances past the deadline and then rejects, the uncaught error escapes with terminal report zero. Discovery/cache/direct/fallback/canonical errors already converge through local catches.
- The same Luna must add a table-driven rejection-after-deadline regression for every uncaught boundary. The minimal correction is one outer error boundary: after an otherwise-uncaught dependency error, return the existing one `circuit_open / wake_deadline` only when elapsed time has reached the deadline; before the deadline, rethrow the original error unchanged. Preserve the existing `finally` owned-page cleanup and do not catch/report errors thrown by `finish` itself.
- Live/provider failure will not be induced. Final acceptance remains pending second TDD fix, re-review, SSOT update, commit, and push.
