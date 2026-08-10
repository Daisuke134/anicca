# CFO-2a2a.1 — Local Agent Usage Normalizer Plan

Status: COMPLETE

## Goal

Normalize one existing agent-runner usage event without changing its runner-normalized token values and without
turning unavailable usage into zero or treating the runner's reused `event_id` as unique.

## Ponytail gate

- Reuse `ledger.js` validation style and existing unattributed shape.
- Add no dependency, file scanner, database, scheduler, pricing table, or OTel exporter.
- Change exactly `apps/life-call/lib/ledger.js` and `apps/life-call/lib/ledger.test.js`.
- The committed slice is already +80/-1 LOC. Repair soft target: the same two files and <=20 further net additions,
  preserving the original <=100 cumulative additions from the pre-slice base. Stop and re-plan before that boundary.

## Measured correction

The prior implementation passed its fixture but used `agent_usage:<event_id>` as the idempotency key. Real ledgers
disprove that assumption: one Life Manager runner ID identifies 405 distinct observations, and 428 Anicca IDs collide.
The runner source confirms `event_id = sha256(evidence_dir + attempt_index)[:24]`. The correction keeps that field for
correlation and requires an opaque collector-supplied source-row ref for identity.

## Task 1 — RED

In `ledger.test.js`, add focused contracts for `normalizeLocalAgentUsageEvent`:

1. a real-shaped Codex `provider_reported` row with a nested `tokens` object and a context containing a 64-hex
   `source_row_ref` preserves every runner-normalized token
   field, provider provenance, and explicit
   attribution, while labeling the token basis as runner-normalized;
2. a Claude `provider_reported` row preserves cache fields plus a concrete `upstream_model` and stays unattributed
   when mapping is null;
3. an `openai-api` row is preserved rather than silently excluded;
4. an `unavailable` failed attempt keeps all tokens null and returns `coverage_status=missing_usage`;
5. two distinct rows sharing a runner `event_id` remain distinct when their source-row refs differ;
6. invalid/non-plain input, missing/zero/malformed source-row refs, invalid IDs/counts/status/measurement, or provider-reported null counts fail with one fixed
   redacted error prefix and never echo hostile input.

Every test call supplies `source_row_ref`. Run only the focused test and record RED from the collision contract: the
current implementation emits the same `agent_usage:<event_id>` for two distinct source-row refs.

## Task 2 — GREEN

In `ledger.js`, implement and export the smallest pure normalizer:

- accept only plain input and a plain `{source_row_ref, financial_unit_id}` context;
- validate the closed input fields used by the canonical contract;
- require one plain nested `tokens` object and copy all six runner-normalized fields exactly;
- preserve `provider`, `provider_name`, `model`, and nullable `upstream_model`;
- emit `local_agent_usage:<source_row_ref>` plus correlation-only `runner_event_id`, normalized RFC3339 time, terminal run identity, attribution, measurement,
  `token_value_basis`, and coverage;
- return a deeply frozen plain object;
- emit only `cfo_local_agent_usage_invalid:<fixed_reason>` errors.

Run the focused test, then `npm run test:cfo`, `npm test`, syntax checks, `git diff --check`, and the file/LOC gate.

## Task 3 — Verify

A fresh Sol reviewer checks only correctness, scope, evidence truth, redaction, and YAGNI. Sol independently reruns the
focused/CFO/full tests, updates the child spec checkbox/status, commits, and pushes before starting 2a2a.2.

## Superseded evidence

- Fresh review found the flat-token fixture could not read real ledger rows; the same Luna corrected it to nested
  `input.tokens` and shared freeze reuse.
- The earlier real read-only E2E count is superseded by the identity-aware run below.
- Focused 17/17, CFO 270/270, and full 923/923 tests passed for token preservation but did not test real identity
  collisions; they are insufficient for completion.
- Implementation scope is exactly two files and +80/-1 LOC.

## Completion evidence

- Luna recorded the collision-contract RED, then implemented the repair in the same two files with +12 net repair LOC.
- Fresh Sol review returned `ship` with Critical 0 and Important 0.
- Focused 4/4, CFO 270/270, full suite exit 0, syntax, and `git diff --check` pass.
- Real read-only E2E normalized all 4,931 complete source rows with exact token equality: Life Manager 1,095 rows
  (1,083 covered, 12 missing usage, 6 runner-ID collision groups) and Anicca 3,836 rows (3,575 covered,
  261 missing usage, 428 collision groups). Distinct rows remain distinct.
- Production plus test scope remains exactly two files and +92/-1 cumulative LOC from the pre-slice base, inside the
  +100 gate.
