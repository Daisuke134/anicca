# PM Merge Live Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the existing real `merge.py` recovery primitive to the hourly live Polymarket pass before any cash-gated strategy, then prove one real balanced YES/NO merge and its ledger accounting.

**Architecture:** Keep `merge.py` as the sole owner of position selection, approval, transaction submission, receipt verification, pUSD delta, and ledger recording. `run.sh` only invokes it after resolved-position redemption and before bundle-arbitrage/market-maker cash gates, records the result in the existing strategy trace, and continues when merge fails so a temporary RPC failure does not disable the entire earning pass.

**Tech Stack:** Bash, Python 3.14, pytest, Polymarket `SecureClient`, Polygon CTF, launchd.

## Global Constraints

- Live entrypoint remains `PM_DRY_RUN=0`; the scheduled decision loop remains dry and is not modified.
- Merge only equal YES/NO quantities from the same `conditionId`; `amount="max"` is resolved by the installed SDK.
- Private keys never enter the repository, logs, plan, spec, or test fixtures.
- A merge failure is traced and retried next wake; it does not suppress bundle-arbitrage, market-maker, or directional selection.
- Completion requires an independent Polygon receipt with status `0x1`, before/after pUSD and positions, one ledger row for the transaction, and a second pass with no duplicate transaction or ledger row.
- Sources:
  - Polymarket Positions & Tokens — https://docs.polymarket.com/concepts/positions-tokens — “Merging requires equal amounts of Yes and No tokens.”
  - Polymarket Manage Positions — https://docs.polymarket.com/trading/positions/manage — “100 YES tokens + 100 NO tokens → 100 pUSD.”

---

### Task 1: Lock the live-pass recovery order with a shell integration test

**Files:**
- Create: `skills/earn/polymarket-trade/test_run_merge_wiring.py`
- Test: `skills/earn/polymarket-trade/test_run_merge_wiring.py`

**Interfaces:**
- Consumes: `skills/earn/polymarket-trade/run.sh`
- Produces: a subprocess-level contract proving `redeem.py → merge.py → bundle_arb.py → market_maker.py → pick.py` and fail-soft merge behavior.

- [x] **Step 1: Write the failing order test**

Create a temporary skill directory containing the real `run.sh`, empty strategy files, and a fake agent Python executable that appends each invoked script basename to a call log. Run the real Bash entrypoint with a fake private key and assert the literal call order:

```python
assert calls == [
    "redeem.py",
    "merge.py",
    "bundle_arb.py",
    "market_maker.py",
    "pick.py",
]
```

- [x] **Step 2: Write the failing fail-soft test**

Set `PM_TEST_MERGE_RC=7` in the same subprocess harness and assert that `run.sh` still exits `0`, invokes `bundle_arb.py`, `market_maker.py`, and `pick.py`, and writes a strategy trace row with `"action": "merge"` and `"exit": 7`.

- [x] **Step 3: Run the focused test and verify RED**

Run:

```bash
/Users/anicca/.anicca-founder/agents/polymarket-agent/.venv/bin/python \
  -m pytest skills/earn/polymarket-trade/test_run_merge_wiring.py -q
```

Expected: the order test fails because `merge.py` is absent from the observed call list.

### Task 2: Wire merge before cash-gated strategies

**Files:**
- Modify: `skills/earn/polymarket-trade/run.sh:177-200`
- Test: `skills/earn/polymarket-trade/test_run_merge_wiring.py`

**Interfaces:**
- Consumes: `merge.py` exit code and stdout/stderr.
- Produces: `merge` strategy trace rows and recovered pUSD visible to the following strategy processes.

- [x] **Step 1: Add the minimal fail-soft invocation**

After the existing `redeem.py` block and before `bundle_arb.py`, add:

```bash
if [ -f "$SKILL_DIR/merge.py" ]; then
  MERGE_OUT=$(timeout 200 "$AGENT_HOME/.venv/bin/python" "$SKILL_DIR/merge.py" 2>&1); MERGE_RC=$?
  echo "$MERGE_OUT" | tail -10
  append_strategy_trace "merge" "$MERGE_OUT" "$MERGE_RC"
fi
```

- [x] **Step 2: Run the focused test and verify GREEN**

Run the Task 1 pytest command.

Expected: 2 passed.

- [x] **Step 3: Run the complete Polymarket baseline**

Run the pytest-format files as one command and the two script-format tests separately. Expected: existing 76 pytest cases, 5 position cases, 7 verification cases, plus the 2 new wiring cases all pass.

- [ ] **Step 4: Commit the isolated code change**

```bash
git add \
  skills/earn/polymarket-trade/run.sh \
  skills/earn/polymarket-trade/test_run_merge_wiring.py \
  docs/superpowers/plans/2026-07-28-pm-merge-live-pass.md
git commit -m "fix(polymarket): recover balanced positions before trading"
```

### Task 3: Deploy and prove one real merge

**Files:**
- Modify deployed copy: `/Users/anicca/.blockrun/skills/earn/polymarket-trade/run.sh`
- Update after proof: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**
- Consumes: live wallet `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, launchd `ai.anicca.pm-live-trade`.
- Produces: Polygon transaction hash, status `0x1`, pUSD recovery, reduced/no mergeable balance, and exactly one `polymarket-merge` ledger row.

- [ ] **Step 1: Capture pre-merge evidence**

Read Polymarket positions, deposit-wallet pUSD, the current count of `polymarket-merge` ledger rows, and the deployed `run.sh` checksum.

- [ ] **Step 2: Deploy the verified script**

Apply only the merge block to the canonical dirty checkout while preserving unrelated user changes, copy the resulting exact `run.sh` to the `.blockrun` runtime, and confirm the two checksums match.

- [ ] **Step 3: Trigger the real existing launchd loop**

```bash
launchctl kickstart -k "gui/$(id -u)/ai.anicca.pm-live-trade"
```

Wait for the job to exit and require `last exit code = 0`.

- [ ] **Step 4: Independently verify the transaction**

Require:

```text
Polygon receipt status = 0x1
pUSD after - pUSD before > 0
mergeable balanced quantity decreases to zero
ledger contains exactly one row with the transaction hash
```

- [ ] **Step 5: Prove idempotency**

Trigger the same launchd loop again. Require no new merge transaction, no additional ledger row for the first transaction, and a trace/output stating there is no mergeable balanced condition.

- [ ] **Step 6: Update the single source of truth**

Move `PM-MERGE-1` to the completed baseline, advance the current cursor to `S21-MAC-OFF`, replace pre-merge balances with verified post-merge values, and record the transaction hash and receipt evidence in the Life Manager spec.

- [ ] **Step 7: Verify, commit, and push**

Run `git diff --check`, the focused/full test commands, fresh live readbacks, and a stale-cursor search. Commit only task-owned files and push `main`.
