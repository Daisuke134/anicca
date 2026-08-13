# Lancers G3B Deterministic Eligible Ranking Implementation Plan

> **For agentic workers:** Implement this plan directly in the existing isolated worktree. The primary owns spec, plan, deployment, and final E2E. The implementer owns only the two named code/test files and post-implementation commands. Do not perform RED-first TDD.

**Goal:** Submit the strongest already-validated monthly recurring opportunity first when one tick contains multiple eligible Lancers projects.

**Architecture:** Keep the existing planner schema and validation. Add one pure rank-key helper over validated decisions, stable-sort the eligible `(row, decision)` pairs, and retain the existing `eligible[:1]` submit bound.

**Tech Stack:** Python stdlib and existing unittest.

## Global constraints

- Ponytail full: no schema field, DB, state, ML/LLM ranker, second planner call, dependency, report field, or new production file.
- Primary Sol owns spec/plan/deploy/E2E. Luna owns direct implementation and commands only; Luna must not edit docs.
- No RED-first TDD. Add the minimum regression after implementation and then run verification.
- Fresh Sol adversarial review exactly once. No second reviewer.
- Rank only decisions that already passed `_validate`; do not duplicate qualification, budget, date, or margin validation.
- Preserve query rotation, one discovery/tick, provider order as stable tie, claim/fingerprint filtering, and maximum one submit/tick.
- Do not touch live state, ledger, browser, launchd, Telegram, or provider during implementation.

## File map and size budget

| File | Responsibility | Soft target |
|---|---|---:|
| `skills/earn/lancers/scripts/application_loop.py` | pure eligible rank key and one stable sort | <=15 changed production LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | post-implementation priority and stable-tie regression | <=35 changed test LOC |

If another file, schema edit, or more than 15 production changed LOC is required, stop with `NEEDS_CONTEXT`. Do not edit spec, plan, progress, schema, status, installer, launchd, ledger, reporter, or runtime state.

## Task 1: Rank validated eligible candidates before the existing one-submit slice

**Files owned by implementer:** exactly the two files above.

**Interfaces:**

- Consumes: each validated decision has `price_jpy: int` and a qualification mapping with the four names in `QUALIFICATION_COST_FIELDS` plus exact-substring `ongoing_sns_outsourcing_evidence`.
- Produces: `_eligible_rank(item: tuple[Mapping[str, object], Mapping[str, object]]) -> tuple[int, int]`.
- Keeps: `_plan_and_submit` still returns `eligible_count` before slicing and still executes only `eligible[:1]`.

### Step 1: Implement direct ranking

The rank helper must return an ascending-sort key equivalent to:

```python
decision = item[1]
qualification = decision["qualification"]
evidence = qualification["ongoing_sns_outsourcing_evidence"]
explicit_monthly = bool(re.search(r"(?:月額|毎月|定期)", evidence))
projected_net_jpy = decision["price_jpy"] - sum(
    qualification[name] for name in QUALIFICATION_COST_FIELDS
)
return (-int(explicit_monthly), -projected_net_jpy)
```

Apply Python's stable `sorted(..., key=_eligible_rank)` to the existing eligible pairs immediately before the existing no-eligible check/submit loop. Do not add an explicit project-ID tie breaker. Do not change validation or the `eligible[:1]` slice.

### Step 2: Add post-implementation regression

Add one focused test using three valid eligible decisions in provider order:

- project A: generic ongoing evidence without `月額/毎月/定期`, highest projected net;
- project B: explicit monthly evidence, lower projected net than C;
- project C: explicit monthly evidence, highest projected net among monthly candidates.

Assert eligible count remains 3, submitter is called exactly once, and only project C is submitted. In the same test or one additional compact assertion, make B and C rank keys equal and assert provider order B remains before C. Use injected discoverer/planner/submitter and temporary state only.

### Step 3: Run post-implementation verification

Require exit 0:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py apps/lancers-revenue/tests/test_lancers_status.py apps/lancers-revenue/tests/test_install_local.py apps/lancers-revenue/tests/test_telegram_report.py
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test*.py'
python3 -m py_compile skills/earn/lancers/scripts/application_loop.py
git diff --check
```

Report diffstat and require only the two owned files changed. Do not deploy.

### Step 4: Commit and push

```bash
git add skills/earn/lancers/scripts/application_loop.py apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "feat(lancers): rank validated monthly opportunities"
git push origin HEAD:feat/lancers-g3b-ranking
```

Return status, commit SHA, test counts, selected project IDs for priority and stable-tie cases, diffstat, and concerns. Do not edit any docs.

## Primary acceptance after implementation

1. Primary inspects diff and reruns every verification command.
2. Exactly one fresh Sol adversarial verifier tries to falsify monthly priority, projected net arithmetic, stable ties, validated-only assumption, eligible count, claim exclusion, and one-submit bound.
3. FIX_FIRST findings return once to the same implementer; primary re-verifies without a second review.
4. Primary updates SSOT, pushes canonical main, installs exact SHA, and reloads the existing launchd owners.
5. Primary triggers one real application owner tick. A qualified result may submit at most one project; any uncertainty quarantines only that project and is never blindly resent.
