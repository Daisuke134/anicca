# Alpaca L02 Explicit Deployment Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and superpowers:test-driven-development task-by-task.

**Goal:** Require one exact `LIFE_MANAGER_INVESTMENT_DEPLOYMENT=local|cloud` value and record it in every new Alpaca decision receipt and successful pass status.

**Architecture:** Validate the existing environment boundary in `run.py`; add the validated value to decisions before the existing receipt functions and to stdout summary. The macOS launchd renderer injects `local` only for `alpaca-investment`; no generic config system or cloud wiring is added.

**Tech Stack:** Python 3 standard library and existing `unittest` suite.

## Global Constraints

- One active atom: L02 only.
- Exact accepted values are `local` and `cloud`; absent, empty, combined, whitespace-padded, or differently-cased values fail closed.
- Do not implement credential/mode separation, live effects, cloud scheduling, profile coordination, migration, or failover.
- No new dependency, framework, registry field, scheduler, queue, ledger, adapter, or directory.
- Preserve paper behavior, Telegram, retry, effect, reconciliation, and dashboard isolation.

---

### Task 1: Validate and record the profile in the finite pass

**Files:**
- Modify: `skills/alpaca-investment/test_run.py`
- Modify: `skills/alpaca-investment/run.py`

**Interfaces:**
- Produces: `_deployment() -> str`, returning only `local` or `cloud`.
- Produces: `decision["deployment"]` before receipt creation and `summary["deployment"]` on success.

- [x] **Step 1: RED**

Add a `DeploymentProfileTest` that calls `_deployment()` under exact `local` and `cloud` values and rejects `None`, `""`, `"local,cloud"`, `" local"`, and `"LOCAL"` with `ValueError("investment_deployment_invalid")`. Make existing pass tests default to `local`. In the success pass test, stop mocking `record_no_trade`, read the real temporary `receipts.jsonl`, and assert the decision receipt and stdout summary both contain `"deployment": "local"`.

Run `python3 -m unittest skills.alpaca-investment.test_run`; expect failure because `_deployment` and recorded deployment do not exist.

- [x] **Step 2: GREEN**

Add the minimum validator:

```python
def _deployment() -> str:
    value = os.environ.get("LIFE_MANAGER_INVESTMENT_DEPLOYMENT")
    if value not in {"local", "cloud"}:
        raise ValueError("investment_deployment_invalid")
    return value
```

Call it at the beginning of the protected pass before broker reconciliation. Add its result to both the fixed campaign-exit decision and the allocator decision before `seal()` or `record_no_trade()`, and to the successful stdout summary. Do not change failure payloads or retry policy.

Run `python3 -m unittest skills.alpaca-investment.test_run skills.alpaca-investment.test_reporter`; expect all tests PASS.

---

### Task 2: Inject the local profile from the macOS host

**Files:**
- Modify: `runtime/loop/tests/test_lm_loop_apply.py`
- Modify: `runtime/loop/lm_loop_apply.py`

**Interfaces:**
- Produces: generated `alpaca-investment` plist environment value `LIFE_MANAGER_INVESTMENT_DEPLOYMENT=local`.

- [x] **Step 1: RED**

Add a focused renderer test that renames the existing example registry row to `alpaca-investment`, renders its plist, and asserts:

```python
self.assertEqual(
    rendered["EnvironmentVariables"]["LIFE_MANAGER_INVESTMENT_DEPLOYMENT"],
    "local",
)
```

Run `python3 -m unittest runtime.loop.tests.test_lm_loop_apply.LmLoopApplyTest.test_alpaca_plist_declares_local_deployment`; expect a missing-key failure.

- [x] **Step 2: GREEN**

In `_plist()`, add one Alpaca-specific environment assignment after the base plist is built:

```python
if loop_id == "alpaca-investment":
    value["EnvironmentVariables"]["LIFE_MANAGER_INVESTMENT_DEPLOYMENT"] = "local"
```

Run the focused test, the Alpaca tests, runtime loop tests, registry test, and `git diff --check`; expect all PASS.

---

### Task 3: Primary verification and state update — DONE

**Files:**
- Modify: `docs/superpowers/specs/2026-09-01-alpaca-money-maximizer-design.md`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- Modify: this plan only to check completed steps.

After clean reviews, mark L02 DONE and L03 ACTIVE without reordering. Merge to main, cut an immutable release, target only `alpaca-investment`, and require a natural wake whose loaded/event SHA match, stdout status and newest decision receipt both report `local`, and Telegram delivery remains confirmed.
