# CFO-2a2b — Durable Agent-Usage Capture Design

| Field | Value |
|---|---|
| Status | ACTIVE — CFO-2a2b.1a/1b/2 complete; CFO-2a2b.3 hourly publication is next |
| Method | Ponytail `full` → Superpowers Goal/Loop/Verify/State |
| Roles | Sol plans/specifies/verifies; Luna writes production code/tests |
| Runtime | Local JSONL first; no DB, service, browser, or cloud dependency |

## Goal

Prove exactly how many managed agent attempts started, succeeded, failed, or lost their usage completion. A missing
usage write becomes a named coverage gap, never zero tokens or zero cost. This slice does not price tokens or enable a
total-cost label.

```mermaid
flowchart LR
    L[Managed local loop] --> A[Durable attempt row\nbefore provider launch]
    A -->|write fails| X[Do not launch provider]
    A -->|write succeeds| P[Codex / Claude / OpenClaw]
    P --> U[Durable usage completion\nsame attempt ID]
    A --> J[Local CFO reconciliation]
    U --> J
    J --> C{Exact capture counts}
    C -->|attempt = completion| O[Coverage complete]
    C -->|attempt > completion| M[Named missing completion\ntotal cost disabled]
```

## Measured starting truth

The real audit found valid historical rows but also reused runner event IDs and no durable proof that every provider
attempt produced a completion. Historical usage remains measured evidence; write-attempt coverage begins only at the
first valid write-ahead row. Existing evidence directories are per-run artifacts and cannot prove historical capture.

## Ponytail full decision

- Reuse the shared `agent_runner.py`, its locked `0600` JSONL append+flush+fsync writer, the current usage ledger,
  normalized usage ingestion, and local hourly CFO loop.
- Add only one adjacent append-only `agent-usage-attempts.jsonl`. Each row gets a new random 24-hex `event_id`; its
  completion row reuses that exact ID.
- Do not add Supabase, a queue, daemon, database, browser automation, raw session rescanning, another agent, custom OTel
  exporter, pricing, retry orchestration, or dashboard.
- OTel correlates verified reconciliation later; it is not token truth and cannot repair a missing producer write.

## Exact local contracts

### Attempt row

One line is fsynced before any provider process can launch:

```json
{"version":1,"event_id":"<24 lowercase hex>","timestamp":"<UTC ISO-8601>","loop":"<nonempty>","task_label":"<nonempty>","attempt":1,"provider":"<nonempty>","model":"<nonempty>"}
```

- Default beside the usage ledger as `agent-usage-attempts.jsonl`; test/owner override is
  `ANICCA_USAGE_ATTEMPT_LEDGER`.
- Attempt and usage ledger paths must differ.
- `loop`, `task_label`, and every candidate `provider`/`model` must be non-empty strings. Reject invalid values before
  evidence-directory, budget, ledger, provider, or fallback effects.
- Attempt append failure returns a fixed redacted nonzero error and launches no provider or fallback.
- A current budget reservation is settled at zero because no provider call occurred.

### Completion usage row

The existing schema stays unchanged except `event_id` becomes the attempt ID. Success and failure both write
completions. Required token fields are non-negative integers. An absent optional token field keeps its documented
default; a present boolean, negative, fractional, non-numeric, or otherwise invalid field makes token measurement
unavailable with every token field null. A present invalid provider cost becomes null/unavailable without discarding
otherwise valid tokens. Completion-write failure remains visible and leaves the durable attempt unmatched.

### Reconciliation result

For rows at or after the capture cutover, the consumer validates both schemas and reports exact integer counts:

- `attempted_rows`
- `success_rows`
- `failed_rows`
- `missing_completion_rows`
- `duplicate_attempt_rows`
- `conflicting_attempt_rows`
- `unmatched_completion_rows`
- `ambiguous_completion_rows`

`success_rows + failed_rows + missing_completion_rows = attempted_rows` must hold. Missing, duplicate, conflicting,
ambiguous, malformed, truncated, or unread evidence adds a named coverage exception. A nonempty upstream usage-chain
coverage array adds `usage_chain_incomplete`. Until all required sources are fresh and every exception is zero, no
total-cost label is allowed. Plan: `2026-08-11-life-manager-cfo-agent-usage-capture-reconciliation.md`.

## One-at-a-time delivery

- [x] **CFO-2a2b.1a — numeric truth:** absent optional values remain defaults; present invalid values are unavailable.
      Producer commit: `82a3b349`.
- [x] **CFO-2a2b.1b — producer boundary:** write-ahead attempt row and focused real-runner tests. Producer commits:
      `ef233a90` + `a0fe0c35`; 2 files, `+80/-6`; fresh Sol review: ship.
- [x] **CFO-2a2b.2 — pure reconciliation:** strict local attempt/usage join and immutable counts receipt. Commit
      `ea3f87408`; 3 files, `+92/-1`; focused 7/7; CFO 297/297; fresh Sol review: ship.
- [ ] **CFO-2a2b.3 — hourly publication:** wire the receipt into the one-hour loop and prove forced usage-persistence
      failure appears as missing coverage, never zero cost or a complete total.
- [ ] **CFO-2a2b.4 — real E2E and close:** verify real ledgers remain append-only, run one isolated provider-boundary
      probe without a paid provider, review, update state, push, and send one counts-only Telegram milestone.

## Acceptance gates

1. Attempt-ledger failure launches no provider.
2. Successful and failed attempts each have one attempt row and one same-ID completion.
3. Forced usage-ledger failure leaves one unmatched attempt and never becomes zero usage/cost.
4. Missing optional numerics use documented defaults; present invalid values become unavailable/null, never coerced.
5. Duplicate/conflicting rows cannot increase totals.
6. Source ledgers remain append-only `0600`; tests emit no prompt, output, token value, path, credential, or owner.
7. Each implementation slice uses at most three files and no more than 100 gross added LOC; new CFO tests are
   registered in the durable `test:cfo` command.
