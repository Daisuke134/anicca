# CFO-2a2b.5c1 — Portable Life Manager Runner Numeric Truth Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Sol owns this plan,
> worktree setup, final review, state, commit, and push. Luna owns only the two listed implementation files.

**Status:** READY FOR SOL REVIEW

**Goal:** Port the already-reviewed numeric/null behavior from profitable-claude commit `5ca6c00` onto the portable
Life Manager runner before that runner starts write-ahead capture. Present invalid optional token/cost values become
unavailable/null; absent optional values retain their documented defaults.

**Measured precondition:** `/Users/anicca/Projects/life-manager-main` is clean `main` at `5b1d81d9`. Its
`skills/life-manager/life-manager-daily.sh` exports the real Life Manager usage ledger before calling
`skills/earn/marketing-engine/run_agent.sh`, which resolves to `runtime/agent-runner/agent_runner.py`. That portable
runner still uses `optional_token or 0`, `total or derived`, and unbounded `float(cost)` behavior. Do not edit main;
Sol creates `/Users/anicca/Projects/life-manager-main/.worktrees/cfo-agent-usage-cutover` on branch
`feature/cfo-life-manager-agent-usage-cutover` from the measured commit.

## Ponytail full scope

Exactly two files, target/hard maximum **56 gross added LOC**:

- `runtime/agent-runner/agent_runner.py` — at most 9 gross additions
- `runtime/agent-runner/tests/test_numeric_truth.py` — at most 47 gross additions

Copy the six reviewed conditions and compact regression semantically; do not merge another branch or copy a whole
runner file. Add no helper, dependency, ledger, attempt schema, retry, agent, service, scheduler, launchd, OTel,
pricing, Moneytree, Telegram, DB, cloud, or real provider call. Write-ahead capture remains 5c2.

## Exact behavior

- Codex required input/output stay non-negative non-boolean integers. Present optional cached/reasoning values must
  also satisfy that rule or the whole token measurement is unavailable with all token fields null. Absent optional
  values remain zero.
- Claude applies the same rule to cache-create/cache-read/reasoning. Present `total_cost_usd` is accepted only when
  finite, non-negative, non-boolean, and Python-float representable. Use the overflow-safe closed condition with
  `sys.float_info.max` before conversion; reject NaN, infinity, negative, `True`, string, and `10**1000` without an
  exception. Invalid cost leaves otherwise valid tokens provider-reported but cost null/unavailable.
- OpenClaw applies the same optional rule. Absent total remains input+output; present integer zero remains zero.
- Preserve current portable routing, Codex schema adaptation, budget admission, usage schema, and every unrelated
  behavior.

## TDD / verify / state

1. Sol creates the dedicated worktree/branch and records clean porcelain plus hashes for the two owned files.
2. RED: Luna creates one compact `unittest` method
   `NumericTruthTest.test_provider_usage_distinguishes_absent_and_invalid_optional_numbers`, adapted from the reviewed
   profitable-claude regression. Exact invalid cost tuple is `True, -1, float("inf"), 10**1000, "bad"`. Run
   `python3 -m unittest runtime.agent-runner.tests.test_numeric_truth`; require failures proving invalid optionals are
   currently coerced and OpenClaw total zero is replaced.
3. GREEN: change only `extract_provider_usage`; `sys` is already imported in the measured portable runner. Rerun the focused test, then
   `PYTHONPATH=runtime/agent-runner python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py'`,
   `python3 -m py_compile runtime/agent-runner/agent_runner.py runtime/agent-runner/tests/test_numeric_truth.py`, and
   `git diff --check`.
4. Require full status baseline plus exactly the two owned modifications, production additions `<=9`, test additions
   `<=47`, total `<=56`. Luna does not stage, commit, push, trigger launchd, call a provider, or touch real ledgers.
5. Fresh Sol reviews only invalid-number coercion/overflow, absence defaults, OpenClaw zero, preservation of portable
   behavior, and scope. Required fixes return to the same Luna.
6. Sol reruns gates, commits/pushes only the two files, updates parent/child state, sends one real `Codex:::` Telegram
   milestone, and advances only to 5c2.
