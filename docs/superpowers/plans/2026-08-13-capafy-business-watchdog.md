# Capafy 300-Second Business Watchdog Plan

**Goal:** Load the existing 300-second watchdog only after it can detect stale money reconciliation, missing owner reports, and non-convergent incidents, then wake exactly one existing repair-owner loop.

**Architecture:** Extend the existing deterministic Python health classifier with two missing business observables and fixed owner-to-launchd routing metadata. Keep the shell as the single executor: it accepts only three allowlisted launchd labels and calls `launchctl kickstart` once, without `-k`, so an already-running owner is not killed. Retain the legacy generic self-fix fallback only for third-party checker output that lacks routing metadata; every built-in unhealthy result carries a fixed repair label.

**Ponytail scope:** Modify two production files and one existing Python test file. No new daemon, state ledger, wrapper, dependency, or plist. Estimated production change: at most 100 lines; tests may exceed this.

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
   - missing/malformed/old `hourly:` delivery → `reason=owner_report_missing`, owner `company`, label `ai.anicca.capafy-goal-monitor`;
   - missing/malformed/old `daily_close:` delivery → the same company owner/label;
   - existing incident logic, with owner from the incident record and a fixed allowlist mapping;
   - existing terminal-outcome logic.
3. Support incident owners `builder|capafy-builder`, `marketer|capafy-marketer`, and `company|capafy-company`. Map them respectively to:
   - `ai.anicca.capafy-loop-daily`
   - `ai.anicca.capafy-ig-marketing-daily`
   - `ai.anicca.capafy-goal-monitor`
   Unknown incident owners fail unhealthy with `reason=unknown_incident_owner` and no attacker-controlled label.
4. Every built-in unhealthy payload includes `repair_owner` and the fixed `repair_label`. Do not echo arbitrary state into a command.
5. In `capafy-loop-healthcheck.sh`, add `CAPAFY_LAUNCHCTL` as the test seam. For a nonzero built-in result with one of the three exact allowed labels, invoke exactly:

```bash
"$LAUNCHCTL" kickstart "gui/$(id -u)/$REPAIR_LABEL"
```

Do not use `-k`, do not call a second owner on failure, and do not call generic self-fix when a valid repair label was supplied. Keep the current generic self-fix fallback only when checker output has no repair label. Use the same seam for the daily scheduler presence check.
6. Update the one Python test file after implementation. Existing incident fixtures receive explicit owners and fresh reconciliation/report baselines. Add direct regression checks for:
   - stale reconciliation routes only to Builder;
   - missing hourly and missing daily-close route only to company;
   - overdue Marketer incident routes only to Marketer;
   - shell calls exactly one allowlisted `kickstart` and never the generic fixer for routed built-in failures;
   - attacker-controlled/unknown labels are never executed.

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
