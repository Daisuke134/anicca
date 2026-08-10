# CFO-2a2a.1 — Local Agent Usage Normalizer Plan

## Goal

Normalize one existing agent-runner usage event without changing its runner-normalized token values and without
turning unavailable usage into zero.

## Ponytail gate

- Reuse `ledger.js` validation style and existing unattributed shape.
- Add no dependency, file scanner, database, scheduler, pricing table, or OTel exporter.
- Change exactly `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- Soft target: production 40 LOC, tests 50 LOC, total 90 added LOC. Stop and re-plan before 100 added LOC.

## Task 1 — RED

In `ledger.test.js`, add focused contracts for `normalizeLocalAgentUsageEvent`:

1. a Codex `provider_reported` row preserves every runner-normalized token field, provider provenance, and explicit
   attribution, while labeling the token basis as runner-normalized;
2. a Claude `provider_reported` row preserves cache fields plus a concrete `upstream_model` and stays unattributed
   when mapping is null;
3. an `openai-api` row is preserved rather than silently excluded;
4. an `unavailable` failed attempt keeps all tokens null and returns `coverage_status=missing_usage`;
5. invalid/non-plain input, invalid IDs/counts/status/measurement, or provider-reported null counts fail with one fixed
   redacted error prefix and never echo hostile input.

Run only the focused test and record the expected missing-export failure.

## Task 2 — GREEN

In `ledger.js`, implement and export the smallest pure normalizer:

- accept only plain input and a plain `{financial_unit_id}` mapping context;
- validate the closed input fields used by the canonical contract;
- copy all six runner-normalized token fields exactly;
- preserve `provider`, `provider_name`, `model`, and nullable `upstream_model`;
- emit `agent_usage:<event_id>`, normalized RFC3339 time, terminal run identity, attribution, measurement,
  `token_value_basis`, and coverage;
- return a deeply frozen plain object;
- emit only `cfo_local_agent_usage_invalid:<fixed_reason>` errors.

Run the focused test, then `npm run test:cfo`, `npm test`, syntax checks, `git diff --check`, and the file/LOC gate.

## Task 3 — Verify

A fresh Sol reviewer checks only correctness, scope, evidence truth, redaction, and YAGNI. Sol independently reruns the
focused/CFO/full tests, updates the child spec checkbox/status, commits, and pushes before starting 2a2a.2.
