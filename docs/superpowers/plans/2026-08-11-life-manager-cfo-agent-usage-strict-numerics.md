# CFO-2a2b.1a — Strict Provider Numerics Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers test-driven-development and
> verification-before-completion. Luna owns production/test edits; Sol owns this plan, review, final verification,
> state, commit, and push.

**Status:** READY FOR LUNA

**Goal:** Stop converting a provider's present invalid optional token/cost number into a valid zero or estimate while
preserving documented defaults only when that optional field is absent.

**Architecture:** Change only the existing pure `extract_provider_usage` boundary and its existing unit-test harness.
No ledger schema, attempt persistence, provider execution, budget, CFO consumer, launchd, OTel, Telegram, DB, or cloud
change.

**Soft target:** two existing files and <=60 added LOC total:

- `skills/agent-runner/agent_runner.py`
- `skills/gig-work/tests/test_agent_runner.py`

## RED

- [ ] Add one table-driven pure-unit regression around `extract_provider_usage`. For Codex, Claude, and OpenClaw,
      prove an absent optional token field keeps its documented zero/derived default, while the same field when present
      as boolean, negative, fractional, or non-numeric makes the whole token measurement unavailable with all token
      fields null. Prove a present negative/non-finite/non-numeric Claude `total_cost_usd` becomes null/unavailable
      without discarding otherwise valid tokens. Run only this test and record the genuine failure.

## GREEN

- [ ] Add the smallest presence-aware numeric helper(s). Required tokens remain non-negative Python integers excluding
      booleans. Optional tokens default only when the key is absent; present invalid values invalidate token usage.
      Optional provider cost is finite and non-negative or unavailable. Do not change valid payload output, token
      algebra, pricing tables, cost labels, budget behavior, or any schema.

## VERIFY / STATE

- [ ] Run the focused test, the existing provider-usage and token-budget tests, full `test_agent_runner.py`, syntax, and
      `git diff --check`. Luna reports exact counts/diffstat and edits no docs, live state, commit, or remote.
- [ ] Fresh Sol review checks numeric truth and scope only. Sol independently reruns the gates, updates the docs,
      commits/pushes the producer repo, and advances only to CFO-2a2b.1b.

