# Connector circuit-breaker Item 15 acceptance plan

## Goal

Accept the existing minimal Connector circuit breaker only from composed contract tests plus durable production evidence: three consecutive safe failures or ten elapsed minutes stop further browser work, preserve exact privacy-safe history, send a positive Telegram recovery report, and create no five-minute retry path.

## Ponytail full gate

- Do not add another circuit module, timer, retry queue, healthcheck, healer, schedule, or test framework.
- Reuse `connector-minimal-runner.js`, `connector-minimal-operations.js`, the single daily launchd renderer contract, their existing focused tests, and immutable official wake records.
- No live provider failure is induced: an artificial or deliberately destructive registration failure is not necessary because an existing official wake already reached the exact three-failure terminal boundary.
- Code/test LOC target is zero. Only this plan and the SSOT acceptance record may change if every existing proof passes.

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

Pending verification.
