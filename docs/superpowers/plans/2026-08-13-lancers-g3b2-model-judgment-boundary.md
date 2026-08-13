# Lancers G3B.2 Model Judgment Boundary Implementation Plan

> **For agentic workers:** Implement directly in the existing isolated worktree. The primary owns spec/plan/deploy/E2E. The implementer owns only the two named code/test files and post-implementation commands. Do not perform RED-first TDD.

**Goal:** Remove hardcoded Japanese-language business-priority judgment from ranking while retaining deterministic projected-profit order and the one-submit bound.

**Architecture:** Eligible/recurring judgment remains with the existing planner and grounded validation. Deterministic code computes projected net JPY and stable-sorts validated candidates by that arithmetic value only.

**Tech Stack:** Python stdlib and existing unittest.

## Global constraints

- Building-agents: no regex/keyword/if-else business judgment. Deterministic code may do arithmetic/bookkeeping only.
- Ponytail full: no new schema, field, prompt, agent call, DB, state, dependency, service, or production file.
- Primary owns spec/plan/deploy/E2E. Luna owns only direct code/test implementation and commands; no docs/live changes.
- No RED-first TDD. Modify the regression after implementation and run verification.
- Fresh Sol adversarial review exactly once. No second reviewer.
- Preserve existing eligible validation, query rotation, empty-result fix, claim filtering, provider stable tie, and maximum one submit.

## File map and hard ceiling

| File | Responsibility | Ceiling |
|---|---|---:|
| `skills/earn/lancers/scripts/application_loop.py` | rank by projected net JPY only | 6 changed production LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | prove generic higher-net beats monthly lower-net and ties stay stable | 20 changed test LOC |

## Task 1: Remove keyword priority from the rank key

The original 2-LOC estimate counted only the return-type/key replacements and omitted the three deleted judgment lines.
The corrected ceiling is six changed LOC (`+2/-4`); this is deletion of the forbidden judgment, not scope expansion.

### Step 1: Direct implementation

Change `_eligible_rank` to return a one-element tuple containing only negative projected net JPY. Remove `evidence`, `explicit_monthly`, and the monthly regex from the helper. Do not change any other production path.

### Step 2: Post-implementation regression

Update the G3B regression so project A has generic ongoing evidence and the highest projected net, while B/C have explicit monthly evidence with lower projected net. Assert only A is submitted. Keep the equal-net B/C stable-order assertion. Do not add a new test function.

### Step 3: Verification

Require exit 0:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py apps/lancers-revenue/tests/test_lancers_status.py apps/lancers-revenue/tests/test_install_local.py apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test*.py'
python3 -m py_compile skills/earn/lancers/scripts/application_loop.py
git diff --check
```

Only the two owned files may change. Do not deploy.

### Step 4: Commit and push

```bash
git add skills/earn/lancers/scripts/application_loop.py apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "fix(lancers): keep ranking arithmetic only"
git push origin HEAD:feat/lancers-g3b-ranking
```

Return status, SHA, tests, diffstat, selected/tie IDs, concerns. Do not edit docs.

## Primary acceptance

1. Primary reruns all verification.
2. One fresh Sol adversarial reviewer attacks hidden keyword judgment, net arithmetic, stable ties, claim filtering, invalid planner fail-closed, and one-submit bound.
3. Primary pushes main, deploys exact SHA, reloads owners, and executes one launchd-owned tick. Accept only bounded no-op, one verified application, or one quarantined uncertainty.

## Completion record

- Primary plan/correction commits: `9f52092365b8870b867277fd0f05d600e915fb84` and `68f42e5b44680a22e6c0f6603d31550bf5c94f0b`.
- Luna implementation git SSOT: `f427f480b2c5ee43dceae72f2852116274212c33`; two owned files, production `+2/-4`, test `+2/-2`.
- Verification: HOL 17, combined Lancers 32, agent-runner 15, compile and diff check pass.
- Fresh Sol adversarial review: 1/1, `ship`; no hidden natural-language judgment in the changed rank path, no second review.
- Canonical main/deployed exact release: `68f42e5b44680a22e6c0f6603d31550bf5c94f0b`.
- Real launchd tick: query `AI活用`, observed 1, eligible 0, submitted false, verified 0, exit 0, empty stderr.
- State/ledger/listing hashes unchanged; pending 0, fingerprints 19, verified application receipts 14. Both owners remain enabled and exact-release bound.
