# GA-13B1 Bounty Healthcheck Local CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `bounty-core-healthcheck`'s direct dependency on the external bounty CLI checkout while preserving its report-only production behavior.

**Architecture:** Resolve `bounty-cli.sh` from the healthcheck's own immutable release directory. Extend the existing focused test to prove the resolved CLI is release-local and the healthcheck contains no developer-checkout path. Do not change the daily bounty CLI, cadence, state, provider effects, or loaded label in this slice.

**Tech Stack:** Bash and pytest.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md` (GA-13).

## Global Constraints

- GA-13A must have a target-SHA natural terminal pass before implementation begins.
- No direct launchctl mutation; production uses a main-derived immutable release and targeted `lm-loop apply`.
- Keep the prior release and exact prior plist as rollback evidence.
- No marketplace contact, Coconala change, provider effect, or human approval step.

---

### Task 1: Release-local healthcheck CLI

**Files:**
- Modify: `skills/bounty/test_bounty_healthcheck.py`
- Modify: `skills/bounty/bounty-healthcheck.sh`

**Interfaces:**
- Consumes: `bounty-cli.sh` adjacent to the healthcheck in `skills/bounty/`.
- Produces: `CLI=<script-directory>/bounty-cli.sh`; all existing report-only exits remain unchanged.

- [ ] **Step 1: Write the failing contract**

Add this source contract beside the existing behavior test:

```python
def test_healthcheck_uses_adjacent_bounty_cli():
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in source
    assert 'CLI="$HERE/bounty-cli.sh"' in source
    assert "profitable-claude" not in source
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest -q skills/bounty/test_bounty_healthcheck.py`

Expected: FAIL because the source still contains the external CLI path.

- [ ] **Step 3: Implement the smallest change**

In `bounty-healthcheck.sh`, define `HERE` from `BASH_SOURCE[0]` and set `CLI="$HERE/bounty-cli.sh"`. Do not alter heartbeat, lock, safe-probe, or stale-report logic.

- [ ] **Step 4: Verify source GREEN**

Run:

```bash
python3 -m pytest -q skills/bounty/test_bounty_healthcheck.py
bash -n skills/bounty/bounty-healthcheck.sh
git diff --check
```

Expected: focused tests PASS, shell syntax PASS, external CLI path count 0.

- [ ] **Step 5: Publish and prove production**

Push a branch, require Security Scan GREEN, merge to main, cut a sparse immutable release containing the loop-control and bounty paths, targeted-apply only `bounty-core-healthcheck`, retain prior release/plist, and require a natural target-SHA `phase=report,status=pass` before marking GA-13B1 complete.
