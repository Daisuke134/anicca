# Lancers G3A Bounded Query Coverage Implementation Plan

> **For agentic workers:** Implement this plan directly in the existing isolated worktree. The primary owns the spec, this plan, production deployment, and final E2E. The implementer owns only the named production/test files and post-implementation commands. Do not perform RED-first TDD.

**Goal:** Expand Lancers acquisition from one permanent query to deterministic coverage of ten approved queries without increasing one-tick provider calls or the one-submit safety bound.

**Architecture:** Reuse the existing 30-minute application owner and `status.run_discovery`. Select exactly one query from an immutable tuple using the current UTC 30-minute slot, then execute the unchanged discovery/planner/submit path. Persist no rotation cursor: the time slot is the cursor.

**Tech Stack:** Python stdlib, existing unittest, existing application loop and launchd.

## Global constraints

- Ponytail full: no new state, DB, scheduler, HTTP client, crawler, aggregator, ranking framework, or dependency.
- Primary Sol owns spec/plan/deploy/E2E. Luna owns direct implementation and commands only; Luna must not edit docs.
- No RED-first TDD. Add the minimum regression after implementing, then run all verification commands.
- Fresh Sol adversarial review exactly once after implementation. No second reviewer.
- Preserve one discovery call per tick, `limit=20`, provider `started_at` ordering, explicit query override, claim/fingerprint dedupe, and maximum one submit per tick.
- Do not touch live state, ledger, browser, launchd, Telegram, or provider during implementation.

## File map and size budget

| File | Responsibility | Soft target |
|---|---|---:|
| `skills/earn/lancers/scripts/application_loop.py` | immutable query set, slot selector, reuse one tick clock value | <=25 changed production LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | post-implementation rotation/override/call-bound regression | <=35 changed test LOC |

If production needs another file, persistent cursor, more than one discovery per tick, or more than 25 changed LOC, stop with `NEEDS_CONTEXT`. Do not edit schema, status, adapter, installer, launchd, ledger, application state, reporter, spec, or this plan.

## Task 1: Deterministic one-query-per-tick rotation

**Files owned by implementer:** exactly the two files in the table above.

**Interfaces:**

- Consumes: existing `run_loop(..., clock=None, now=None, query=None)` and `status.run_discovery(query: str, limit: int, timeout: float)`.
- Produces: `DISCOVERY_QUERIES: tuple[str, ...]` and `_discovery_query(value: object) -> str` inside `application_loop.py`.
- Keeps: `query` argument is an exact override; no public CLI query option is added.

### Step 1: Implement the minimum production change

Add the immutable tuple in this exact order:

```python
DISCOVERY_QUERIES = (
    "SNS運用", "SNS投稿", "コンテンツ制作", "X運用", "LinkedIn",
    "B2Bマーケティング", "AI活用", "継続依頼", "長期", "月額",
)
```

Implement `_discovery_query(value)` with this contract:

1. Accept a timezone-aware `datetime` or timezone-aware RFC3339 string.
2. Normalize to UTC and compute `int(timestamp // 1800) % len(DISCOVERY_QUERIES)`.
3. Return `DEFAULT_DISCOVERY_QUERY` for a plain `date`, naive datetime/string, malformed value, or unsupported type.
4. Never read or write state.

In `run_loop`, evaluate `(clock or now or utc-now callable)` once per tick. Use the captured value for both query selection and the existing `_tick_date` validation. Call discovery exactly once with:

```python
query=query if query is not None else _discovery_query(tick_value)
```

Do not reorder opportunities or change `_plan_and_submit`.

### Step 2: Add post-implementation regression

Replace the old single-default-query assertion with one test that captures discoverer calls and proves:

- ten consecutive timezone-aware 30-minute UTC slots select all ten tuple values exactly once in tuple order;
- two calls in the same 30-minute slot select the same query;
- `query="explicit-query"` passes through unchanged;
- every run makes exactly one discoverer call with `limit=20`;
- the existing two-eligible regression still submits only the first eligible project.

Use an empty opportunity result so this regression performs no submit and does not require planner output.

### Step 3: Run post-implementation verification

Run these commands from the worktree and require exit 0:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py apps/lancers-revenue/tests/test_lancers_status.py apps/lancers-revenue/tests/test_install_local.py apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test*.py'
python3 -m py_compile skills/earn/lancers/scripts/application_loop.py
git diff --check
```

Also report production/test diffstat and assert `git diff --name-only` contains only the two owned files. Do not deploy.

### Step 4: Commit and push feature branch

Commit only the two owned files with:

```bash
git add skills/earn/lancers/scripts/application_loop.py apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "feat(lancers): rotate bounded discovery queries"
git push origin HEAD:feat/lancers-g3-profitable-acquisition
```

Return the commit SHA, selected query sequence, test counts, diffstat, and any concern. Do not edit progress/spec/plan files.

## Primary acceptance after implementation

1. Primary inspects the exact diff and reruns all commands.
2. Exactly one fresh Sol adversarial verifier tries to falsify: one-call bound, ten-slot coverage, same-slot stability, timezone behavior, explicit override, planner date reuse, claimed-project safety, and one-submit bound.
3. FIX_FIRST findings return once to the same implementer; primary mechanically re-verifies without a second review.
4. Primary updates SSOT, fast-forwards canonical main, installs exact SHA, and records pre-deploy state/ledger/listing hashes.
5. Primary triggers the existing application launchd owner once and verifies the selected production query indirectly from exact slot calculation plus the real tick output. Any eligible result may perform at most one normal application under the already-enabled policy.
6. Require state/ledger changes to match only verified provider receipts; otherwise quarantine the affected project and stop G3A acceptance without blind resend.

## Completion record

- Primary-authored spec/plan commit: `cd01379b8d10fe4eb4ce034145cdebb7d00e21df`.
- Luna direct implementation commit: `a2081bc0462623a6da1ba531bcb73f17219c7ee4`; only the two owned files changed. Luna did not edit spec/plan or live state.
- Post-implementation verification: HOL 15, combined Lancers 30, agent-runner 15, compile and diff check all exit 0.
- Fresh Sol adversarial review: 1/1, `ship`, no mandatory finding. No second review ran.
- Canonical main and deployed exact release: `a2081bc0462623a6da1ba531bcb73f17219c7ee4`, normal mode, 15-file manifest.
- Real launchd-owned tick selected `LinkedIn` and returned observed 2, qualified 0, submitted false, verified 0, exit 0, empty stderr.
- Application state, ledger, and listing SHA-256 remained unchanged; pending 0, fingerprints 19, application verified receipts 14.
- Final scheduler state: application enabled at 1800 seconds and reporter enabled at 300 seconds, both exact-release bound.
