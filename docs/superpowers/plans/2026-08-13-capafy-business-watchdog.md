# Capafy 300-Second Business Watchdog Plan

**Goal:** Load the existing 300-second watchdog only after it can detect stale money reconciliation, missing owner reports, and non-convergent incidents, then wake exactly one existing repair-owner loop.

**Architecture:** Extend the existing deterministic Python health classifier with two missing business observables and fixed repair routing metadata. Keep the shell as the single executor: it accepts only five allowlisted launchd labels and calls `launchctl kickstart` once, without `-k`, so an already-running owner is not killed. Unknown/corrupt incident ownership routes once to a fixed integrity self-fix action, never to an invented business owner or attacker-controlled command.

**Ponytail scope:** Modify two production files and one existing Python test file. No new daemon, state ledger, wrapper, dependency, or plist. Initial production target is 100 lines; the one adversarial correction may exceed it only for trust-boundary validation, without adding files or abstractions.

## Files owned by implementer

- `skills/self/capafy-loop/capafy_business_health.py`
- `skills/self/capafy-loop/capafy-loop-healthcheck.sh`
- `skills/self/capafy-loop/tests/test_capafy_business_health.py`

The implementer must not edit this plan, the authoritative spec, launchd plists, production state, or any other file.

## Required implementation

1. Add deterministic health inputs:
   - `CAPAFY_RECONCILIATION_LEDGER`, default `~/anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl`.
   - `CAPAFY_RECONCILIATION_MAX_HOURS`, default `48`.
   - `CAPAFY_REPORT_DELIVERY_STATE`, default `$CAPAFY_OUTCOME_STATE_DIR/capafy-goal-monitor-delivery.json`.
   - `CAPAFY_HOURLY_REPORT_MAX_MINUTES`, default `90`.
   - `CAPAFY_DAILY_CLOSE_MAX_HOURS`, default `26`.
2. Evaluate in this priority order so only one owner is selected:
   - missing/non-file/old reconciliation ledger → `reason=stale_reconciliation`, owner `builder`, label `ai.anicca.capafy-loop-daily`;
   - missing/malformed/old `hourly:` delivery → `reason=owner_report_missing`, owner `company`, label `ai.anicca.capafy-goal-monitor-hourly`;
   - missing/malformed/old `daily_close:` delivery → owner `company`, label `ai.anicca.capafy-goal-monitor-daily-close`;
   - existing incident logic, with owner from the incident record and a fixed allowlist mapping;
   - existing terminal-outcome logic.
3. Support incident owners `builder|capafy-builder`, `marketer|capafy-marketer`, and `company|capafy-company`. Map them respectively to:
   - `ai.anicca.capafy-loop-daily`
   - `ai.anicca.capafy-ig-marketing-daily`
   - `ai.anicca.capafy-goal-monitor`
   Unknown incident owners fail unhealthy with `reason=unknown_incident_owner`, `repair_owner=integrity`, and a fixed `repair_action=self_fix`; they never route to Company or hide corruption behind an invented owner.
4. Validate all configured thresholds as finite positive numbers. Invalid configuration returns deterministic unhealthy integrity/self-fix output rather than crashing or becoming healthy. Reject naive timestamps. Treat future reconciliation mtime, future outcome/incident age timestamps, and future delivered timestamps as invalid/stale; future `next_retry_at` remains valid because it is a schedule, not evidence of a past observation.
5. Validate every delivery row before trusting it: exact v2 fields, aware RFC3339 `delivered_at`, `sha256:` plus 64 lowercase hex projection ID, numeric Telegram message ID, and a real-calendar `hourly:YYYY-MM-DDTHH` or `daily_close:YYYY-MM-DD` key. Malformed or future proof is missing/unhealthy.
6. Every built-in unhealthy payload includes a fixed repair action. Do not echo arbitrary state into a command.
7. In `capafy-loop-healthcheck.sh`, add `CAPAFY_LAUNCHCTL` as the test seam. For a nonzero built-in result with one of the five exact allowed labels, invoke exactly:

```bash
"$LAUNCHCTL" kickstart "gui/$(id -u)/$REPAIR_LABEL"
```

Do not use `-k`, do not call a second owner on failure, and do not call generic self-fix when a valid repair label was supplied. For fixed `repair_action=self_fix`, call the generic fixer exactly once and never kickstart a launchd owner. Keep the legacy generic self-fix fallback for third-party checker output without routing metadata. Use the same seam for the daily scheduler presence check.
8. Update the one Python test file after implementation. Existing incident fixtures receive explicit owners and fresh reconciliation/report baselines. Add direct regression checks for:
   - stale reconciliation routes only to Builder;
   - missing hourly routes only to the hourly job and missing daily-close only to the daily-close job;
   - overdue Marketer incident routes only to Marketer;
   - shell calls exactly one allowlisted `kickstart` and never the generic fixer for routed built-in failures;
   - attacker-controlled labels are never executed, while unknown incident owner triggers exactly one fixed integrity self-fix;
   - future/naive timestamps, invalid calendar periods, malformed proof IDs, and non-finite/non-positive thresholds cannot return healthy.

## Direct verification — no TDD/RED cycle

Run once after implementation:

```bash
python3 -m pytest -q skills/self/capafy-loop/tests/test_capafy_business_health.py
bash skills/self/capafy-loop/tests/test_capafy_healthcheck_business.sh
python3 -m py_compile skills/self/capafy-loop/capafy_business_health.py
bash -n skills/self/capafy-loop/capafy-loop-healthcheck.sh
plutil -lint skills/self/capafy-loop/launchd/ai.anicca.capafy-loop-healthcheck.plist
git diff --check
```

Then commit and push the isolated implementation branch.

## Single review and production closure

- One fresh Sol adversarial reviewer attacks timestamp parsing, missing/malformed ledgers, wrong precedence, arbitrary-label injection, duplicate owner wakes, `-k` killing, fallback double-wake, and current-production routing. At most one correction returns to the same implementer; there is no second review cycle.
- Parent merges only after independent verification.
- Parent requires source-installed plist byte equality, bootstraps the currently-unloaded job, and verifies `StartInterval=300`.
- The first real watchdog wake is expected to classify the current overdue incident as `retry_due` and kickstart exactly `ai.anicca.capafy-ig-marketing-daily`. Capture health/owner run counters, health log, exit codes, and ensure neither Builder nor company runs advances from that watchdog wake.
- A controlled healthy-state read-only classifier check must return healthy without waking an owner. Do not rewrite production incidents to manufacture health.
- Close Item 8 with spec evidence, commit, push, and make Item 9 active.
