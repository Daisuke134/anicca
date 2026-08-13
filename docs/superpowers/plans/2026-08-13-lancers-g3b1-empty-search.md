# Lancers G3B.1 Empty Search Normalization Implementation Plan

> **For agentic workers:** Implement directly in the existing isolated worktree. The primary owns spec/plan/deploy/live E2E. The implementer owns only the two named code/test files and post-implementation commands. Do not perform RED-first TDD.

**Goal:** Treat a successful provider search with zero normalized opportunities as a normal no-op application tick instead of a loop failure.

**Architecture:** Preserve the `status.run_discovery` contract and change only the application boundary's condition ordering so the existing empty-opportunities branch handles `no_normalized_opportunities`.

**Tech Stack:** Python stdlib and existing unittest.

## Global constraints

- Ponytail full: no status/schema/provider/state/DB/scheduler/report change and no new file or dependency.
- Primary Sol owns spec/plan/deploy/E2E. Luna owns direct implementation and commands only; Luna must not edit docs.
- No RED-first TDD. Add one post-implementation regression, then run verification.
- Fresh Sol adversarial review exactly once. No second reviewer.
- Only exact `error == "no_normalized_opportunities"` with an empty opportunities sequence becomes normal no-op.
- Preserve fail-closed behavior for discovery/network/provider/schema/invalid errors, maximum one discovery and one submit, query rotation, ranking, claim filtering, and pending quarantine.
- Do not touch live state, ledger, browser, launchd, Telegram, or provider during implementation.

## File map and budget

| File | Responsibility | Hard ceiling |
|---|---|---:|
| `skills/earn/lancers/scripts/application_loop.py` | allow exact empty-result code to reach existing empty branch | 3 changed production LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | post-implementation empty-result regression | 20 changed test LOC |

Any other file or larger production diff returns `NEEDS_CONTEXT`.

## Task 1: Normalize the exact empty-result contract

**Files owned by implementer:** exactly the two files above.

### Step 1: Implement direct conditional fix

In `run_loop`, change only the first discovery-result branch so `observed.get("ok") is not True` remains an error unless `error == "no_normalized_opportunities"`. Leave the following existing error validation and `elif not opportunities: ApplicationLoopResult(True, reason="no_eligible_project")` intact. Do not change `status.py`.

### Step 2: Add post-implementation regression

Add one test with injected discoverer returning exactly:

```python
{
    "ok": False,
    "error": "no_normalized_opportunities",
    "opportunities": [],
}
```

Inject planner and submitter functions that fail the test if called. Assert result `ok is True`, `reason == "no_eligible_project"`, `submitted is False`, observed/eligible/verified counts are zero, and discoverer was called once.

Keep or reuse an existing regression proving another discovery error remains `ok=false` with that error and no planner/submit.

### Step 3: Verify after implementation

Require exit 0:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py apps/lancers-revenue/tests/test_lancers_status.py apps/lancers-revenue/tests/test_install_local.py apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test*.py'
python3 -m py_compile skills/earn/lancers/scripts/application_loop.py
git diff --check
```

Require only the two owned files changed. Do not deploy.

### Step 4: Commit and push

```bash
git add skills/earn/lancers/scripts/application_loop.py apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "fix(lancers): accept empty discovery ticks"
git push origin HEAD:feat/lancers-g3b-ranking
```

Return status, SHA, test counts, diffstat, and concerns. Do not edit docs.

## Primary acceptance

1. Primary reruns all verification and dispatches exactly one fresh Sol adversarial review for this hotfix.
2. The reviewer attacks nonempty `ok=false`, forged empty error with nonempty opportunities, malformed opportunities, network/provider errors, planner/submit call count, and state safety.
3. Primary pushes canonical main, deploys exact SHA, reloads owners, and kicks application once while `B2Bマーケティング` remains the selected slot if possible.
4. Require `ok=true / reason=no_eligible_project / submitted=false`, exit 0, empty stderr, and unchanged state/ledger/listing. If the slot changes or real candidates appear, accept only existing bounded behavior and verify at most one submit with authoritative receipt or quarantine.

## Completion record

- Primary plan commit: `7df2d072fc5ccb2889b5e002ced10ed6024f4689`.
- Luna implementation commit (git/remote SSOT): `086037263acc11c3877875094d51bd79ed8b3ced`; one production line replaced, 19 test lines added, two owned files only.
- Verification: HOL 17, combined Lancers 32, agent-runner 15, compile and diff check pass.
- Fresh Sol adversarial review: 1/1, `ship`; 19 adversarial payload cases, no mandatory finding, no second review.
- Real launchd-owned `B2Bマーケティング` empty tick: ok true, reason no_eligible_project, observed/eligible/verified 0, submitted false, exit 0, empty stderr.
- Application state, ledger, listing hashes unchanged; pending 0, fingerprints 19, verified receipts 14. Both schedulers enabled and exact-release bound.
