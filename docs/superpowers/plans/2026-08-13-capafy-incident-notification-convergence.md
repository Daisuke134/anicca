# Capafy Incident Notification Convergence Implementation Plan

> **For agentic workers:** Implement only the assigned production/test files. The parent owns this plan, the authoritative spec, production state, acceptance, merge, and deployment.

**Goal:** Keep one already-notified Marketing recovery incident authoritative when replacement provisioning produces no account row, and prevent the 60-second outcome monitor from notifying the same unresolved incident again.

**Architecture:** Reuse the existing incident record, lifecycle state, handoff, canonical event store, hourly Japanese report, and account-manager schedule. The account manager maps a successful agent pass with no appended row back to the exact session-recovery incident instead of creating a second failure identity. The outcome monitor reserves one deterministic delivery key before any Telegram call and treats any existing unresolved reservation as terminal; strict one-line sender evidence is required. No new daemon, database, delivery ledger, model route, or account action is added.

**Tech Stack:** Bash, existing Python incident/lifecycle CLIs, launchd, shell fixtures.

## Global constraints

- The user explicitly requires direct implementation with no TDD/RED cycle. Run verification after the code and focused regressions are written.
- Parent Sol owns all specification, planning, ordering, acceptance, production E2E, merge, and completion decisions.
- Implementer changes only the four assigned production/test files. Reviewer is read-only and exactly one fresh adversarial review gates this slice.
- Existing loops remain the executor. Codex and the implementer do not create an Instagram account, publish, mutate production incidents, or send production Telegram.
- Ponytail full: reuse the existing handoff/outcome/lifecycle/event machinery; add no dependency, abstraction, service, state file, or schema.
- Direct failure and outcome-monitor delivery use at-most-once reservation. If Telegram is lost between reservation and confirmed send, the period-keyed Japanese owner report is the completeness path.

## Observed production cause

- Browser recovery merge `73855e5c4` correctly rejected live owner `@capafy.skills10491` for registry target `@capafy.skills8m4q2z`, released its lease, retired only the target row, reused incident `capafy-marketer-20260803T070010Z-99b1374a`, repaired its retry, and let account manager PID `40375` acquire the same browser identity without BUSY.
- The replacement model returned provider status success but explicitly performed no browser or registry mutation because the current prompt's email paths were structurally exhausted. The wrapper converted that no-row result into competing incident `capafy-marketer-20260813T120922Z-ed60fa9e`.
- The 60-second outcome monitor generated a different delivery key after the retry/repair text changed and overwrote the original incident's existing direct-failure receipt, sending Telegram `16102`; the replacement failure then sent `16103`.
- Immediate Marketer replay itself is idempotent: runs `20 -> 21`, exit `0`, manager runs unchanged at `1217`, canonical ledger unchanged at 412 rows, incident delivery ID unchanged, and recovery result removed.

## Task 1: Preserve the original incident on no-row replacement

**Files:**
- Modify: `skills/earn/capafy-marketing/capafy-ig-account-manager.sh`
- Test: `skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh`

**Interfaces:** Consume the lifecycle's existing `incident_id`, the exact registry row carrying that incident, and the existing handoff session-recovery contract. Produce the existing `replacement_waiting` result with `session_recovery=true`, stable reason `active Instagram browser tab is missing`, the exact retired handle, bounded future RFC3339 retry, and a plain repair detail.

- [ ] After lifecycle snapshot, resolve exactly one `session_failed` browser-owned registry row whose `incident_id` equals the lifecycle incident. Zero or multiple matches fail closed to the existing generic technical path.
- [ ] When the model returns zero but the registry count did not increase, route that exact case through the session-recovery result instead of creating a new fingerprint.
- [ ] Do not retire another row, wake the manager recursively, create another incident fingerprint, or send a second failure Telegram. The handoff remains the sole incident writer.
- [ ] Preserve successful account-created, malformed-row, missing-credential, failed-verifier, lock, sender-recovery, and challenge behavior.
- [ ] Synchronize the sender fixture with `TELEGRAM_SENT=true MSGID=<digits>`; this is a stale fixture repair, not a production weakening.
- [ ] Add one regression with a pre-existing session-recovery incident and retired row: a zero-mutation agent result reuses that incident, preserves one active incident and its delivery receipt, and adds no manager wake.

## Task 2: Make the outcome monitor at-most-once

**Files:**
- Modify: `skills/earn/capafy-marketing/capafy-outcome-monitor.sh`
- Test: `skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh`

**Interfaces:** Consume the existing rendered envelope/delivery key and incident `terminal_message_key`. Produce the same incident transition and numeric `telegram_message_id`; no new receipt store is introduced.

- [ ] Determine closure versus unresolved before the send boundary.
- [ ] For unresolved incidents, any existing non-empty terminal reservation means already notified/reserved; exit zero even if repair text or retry changes the newly rendered key.
- [ ] For a first unresolved notification, persist the key before Telegram. For a closure, reserve its distinct closure key on the current phase before Telegram. Replay after sender failure/crash never invokes Telegram twice.
- [ ] Accept only exactly one line `TELEGRAM_SENT=true MSGID=<digits>` with sender exit zero; reject substrings, false markers, blank IDs, and multiline output.
- [ ] After strict success, persist the numeric ID and complete the existing unresolved or verified transition. Event-store conflicts remain fatal.
- [ ] Add regressions for changed-retry existing reservation, first-send failure then replay, spoofed/multiline output, and strict success. Preserve verified stale-sidecar silence and repair closure semantics.

## Direct verification

Run after implementation:

```bash
bash skills/earn/capafy-marketing/tests/test_capafy_ig_account_manager.sh
bash skills/earn/capafy-marketing/tests/test_capafy_outcome_monitor.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_controller.sh
bash skills/earn/capafy-marketing/tests/test_capafy_marketing_outcome.sh
python3 -m pytest -q skills/earn/capafy-marketing/tests/test_capafy_outcome.py
bash -n skills/earn/capafy-marketing/capafy-ig-account-manager.sh skills/earn/capafy-marketing/capafy-outcome-monitor.sh
git diff --check
```

The implementer commits and pushes an isolated branch. Exactly one fresh read-only Sol reviewer attacks sender crash/spoof/multiline evidence, reservation ordering, closure loss/duplication, event conflict, existing-key overwrite, ambiguous incident-to-row mapping, new incident creation, recursive manager wake, result replay, secret leakage, and successful account creation. At most one correction returns to the same implementer.

## Production acceptance

1. Parent captures current active Marketer incidents, terminal keys/message IDs, event-ledger hash/rows, manager/monitor counts, and delivery evidence.
2. Parent kickstarts only the existing account manager. A no-row result updates the original recovery incident without creating a third incident or another Telegram; browser/manager leases release.
3. Two outcome-monitor wakes preserve both existing incident delivery IDs, add no message or duplicate event, and exit zero.
4. Immediate account-manager replay adds no row, incident, event, recursive wake, or Telegram. Structural browser login remains separate Item 9c; this slice does not claim Marketing health.
