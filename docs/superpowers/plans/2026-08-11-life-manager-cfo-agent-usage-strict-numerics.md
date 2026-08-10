# CFO-2a2b.1a — Strict Provider Numerics Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers test-driven-development and
> verification-before-completion. Luna owns production/test edits; Sol owns this plan, review, final verification,
> state, commit, and push.

**Status:** COMPLETE — strict parsing, fresh review, independent verification, and producer feature-branch push done

**Goal:** Stop converting a provider's present invalid optional token/cost number into a valid zero or estimate while
preserving documented defaults only when that optional field is absent.

**Architecture:** Change only the existing pure `extract_provider_usage` boundary and its existing unit-test harness.
No ledger schema, attempt persistence, provider execution, budget, CFO consumer, launchd, OTel, Telegram, DB, or cloud
change.

**Soft target:** two existing files and <=60 added LOC total:

- `skills/agent-runner/agent_runner.py`
- `skills/gig-work/tests/test_agent_runner.py`

## RED

- [x] Add one table-driven pure-unit regression around `extract_provider_usage`. For Codex, Claude, and OpenClaw,
      prove an absent optional token field keeps its documented zero/derived default, while the same field when present
      as boolean, negative, fractional, or non-numeric makes the whole token measurement unavailable with all token
      fields null. Prove a present negative/non-finite/non-numeric Claude `total_cost_usd` becomes null/unavailable
      without discarding otherwise valid tokens. Run only this test and record the genuine failure.

## GREEN

- [x] Add the smallest presence-aware numeric helper(s). Required tokens remain non-negative Python integers excluding
      booleans. Optional tokens default only when the key is absent; present invalid values invalidate token usage.
      Optional provider cost is finite and non-negative or unavailable. Do not change valid payload output, token
      algebra, pricing tables, cost labels, budget behavior, or any schema.

## VERIFY / STATE

- [x] Run the focused test, the existing provider-usage and token-budget tests, full `test_agent_runner.py`, syntax, and
      `git diff --check`. Luna reports exact counts/diffstat and edits no docs, live state, commit, or remote.
- [x] Fresh Sol review checks numeric truth and scope only. Sol independently reruns the gates, updates the docs,
      commits/pushes the producer repo, and advances only to CFO-2a2b.1b.

## Completion evidence

- Luna recorded a genuine RED with nine failures: present invalid optional values were accepted as provider-reported,
  and a negative Claude cost was accepted. GREEN changes only the existing parser and existing test harness:
  two files, `+56/-3` total; production is `+9/-3`.
- The table covers Codex, Claude, and OpenClaw absent defaults plus present boolean, null, negative, fractional, and
  string token values; Claude valid/invalid cost; and OpenClaw's valid explicit `total=0`.
- Luna and Sol each passed the focused test `1/1`; the relevant provider/budget set passed `5/5`; compile and
  `git diff --check` passed. Full `test_agent_runner.py` ran 58 tests with 56 pass and two failures reproduced unchanged
  on the clean parent commit: one stale schema-const assertion and one executable-fallback fixture failure. The older
  agent-runner unit folder also has two pre-existing stale `daily_scope` call errors outside this diff.
- Fresh Sol returned `ship — Spec ✅`. Producer commit `82a3b349` plus the latest provider-recovery merge was pushed to
  `origin/feature/cfo-agent-usage-capture`; no live loop/state/provider/network/Telegram action occurred.
