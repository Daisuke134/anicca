# Gate 13 Experiment Attribution Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Join each verified publication to social, click, install/order, paid/refund, and revenue evidence without inventing post-level causality.

**Architecture:** A pure attribution joiner reads an immutable publication intent plus the canonical native identity ledger, append-only post metrics, click receipts, and product-scoped business snapshots. It emits one append-only experiment snapshot whose individual metric results carry status, attribution class, confidence, time window, and evidence references. Provider collectors remain separate; the joiner never turns missing data into zero or a product/day aggregate into deterministic post attribution.

**Tech Stack:** Python 3 standard library, SQLite publication intent store, JSONL ledgers, JSON Schema Draft 2020-12, Supabase REST read-only receipt query, existing `lm` CLI.

---

### Task 1: Lock the attribution schema and invariants

**Files:**
- Create: `skills/earn/marketing-engine/schemas/experiment-attribution.schema.json`
- Create: `skills/earn/marketing-engine/measure/test_experiment_attribution.py`
- Create: `skills/earn/marketing-engine/measure/experiment_attribution.py`

1. Write failing tests for required identity fields and the complete metric set: impressions, views, qualified clicks, first-time downloads, installs, trials, paid orders, refunds, gross revenue, net revenue.
2. Require each metric result to carry `status`, nullable `value`, `unit`, `source`, `attribution_class`, `confidence`, window, evidence references, and a reason whenever value is null.
3. Implement schema validation and fail-closed timestamp, identity, unit, attribution-class, and null/zero rules.
4. Run `python3 -m unittest measure/test_experiment_attribution.py -v` and confirm GREEN.

### Task 2: Implement the deterministic joins

**Files:**
- Modify: `skills/earn/marketing-engine/measure/test_experiment_attribution.py`
- Modify: `skills/earn/marketing-engine/measure/experiment_attribution.py`

1. Write failing tests proving an exact publication/native identity joins social metrics as `deterministic`.
2. Write failing tests proving exact token-scoped successful click queries may report zero or a count as `deterministic`.
3. Write failing tests proving wrong product/token/native identity is rejected and missing/missed metrics remain null.
4. Implement the joins and stable attribution snapshot ID.

### Task 3: Implement honest aggregate and maturity handling

**Files:**
- Modify: `skills/earn/marketing-engine/measure/test_experiment_attribution.py`
- Modify: `skills/earn/marketing-engine/measure/experiment_attribution.py`

1. Write failing tests proving ASC campaign cohorts are `apple_aggregate`, never deterministic.
2. Write failing tests proving RevenueCat/Stripe product-day totals remain `unknown` unless an exact supported campaign/checkout token exists; modeled attribution requires a declared method and interval.
3. Write failing tests for `not_mature`, `unavailable`, and `unknown`, including the rule that null never becomes zero.
4. Implement maturity gates and aggregate result construction.

### Task 4: Add the production CLI and append-only state

**Files:**
- Modify: `skills/earn/marketing-engine/bin/lm`
- Create: `skills/earn/marketing-engine/measure/verify_gate13.py`
- Modify: `skills/earn/marketing-engine/measure/test_experiment_attribution.py`
- Create at verified run: `skills/earn/marketing-engine/state/experiment-attribution.jsonl`

1. Add `lm measure attribution` inputs for publication DB/key, identity, social, click, business, observed time, output ledger, and evidence artifact.
2. Make exact replay idempotent and conflicting replay fail closed.
3. Query click receipts only by the intent's token and product; do not visit the production redirect or create a synthetic click.
4. Generate a current production snapshot. Young or delayed metrics remain `not_mature`; unavailable providers remain explicit.
5. Verify the artifact from source ledgers and provider receipt evidence.

### Task 5: Verify and document Gate 13

**Files:**
- Modify: `specs/27-MARKETING-ENGINE-END-TO-END.md`
- Modify: `specs/26-MOBILE-APP-EBOOK-10K-LOOPS.md`
- Create: `skills/earn/marketing-engine/evidence/attribution/gate13/verification.json`

1. Run focused attribution tests, all Marketing Engine tests, and `git diff --check`.
2. Record exact test counts, snapshot ID, metric statuses/classes, and evidence paths in both specs.
3. Send a truthful Telegram receipt containing no inferred views, installs, orders, or revenue.
4. Mark Gate 13 complete only if every required metric has a reconciled result record and every unknown remains explicit.
