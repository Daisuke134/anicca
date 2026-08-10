# CFO-2a2b.1b — Producer Write-Ahead Attempt Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers test-driven-development and
> verification-before-completion. Execute checkboxes in order. Luna owns production/test edits; Sol owns this plan,
> review, final verification, state, commit, and push.

**Status:** WAITING — starts only after CFO-2a2b.1a closes

**Goal:** Before the shared agent runner can launch a provider, fsync one minimal attempt row; reuse its unique ID on
the existing completion usage row so the later CFO join can detect a missing completion exactly.

**Architecture:** Extend only the existing producer. Keep the current usage schema and locked JSONL writer. Add one
adjacent attempt ledger and one unique ID per candidate attempt. This task does not change the CFO consumer, hourly
launchd job, Telegram, Moneytree, OTel, pricing, DB, or cloud.

**Soft target:** two files, <=100 added LOC total, reusing the existing real-runner harness:

- `skills/agent-runner/agent_runner.py`
- `skills/gig-work/tests/test_agent_runner.py`

Hard stop before a third implementation file or more than 100 additions; report to Sol and reduce scope instead.

## RED

- [ ] Extend the existing subprocess harness with four bounded boundary cases. The provider stub must observe its
      already-fsynced attempt row at its own launch; success and failure completions reuse that ID. Forced completion
      failure leaves the attempt durable. Forced attempt-ledger failure launches neither provider nor fallback and a
      current budget reservation is settled to zero. Equal resolved attempt/usage paths are rejected before provider,
      ledger, or evidence effects.
- [ ] Keep fixtures private and assert only fixed/count/schema facts. No paid provider, network, live ledger, live
      evidence, Telegram, launchd, or source-repo state is touched.

## GREEN

- [ ] Resolve the usage path and `ANICCA_USAGE_ATTEMPT_LEDGER` once. Default the latter to
      `agent-usage-attempts.jsonl` beside the usage ledger and reject equal resolved paths before effects.
- [ ] Generate one new 24-lowercase-hex ID per candidate attempt. Append the exact attempt schema with the existing
      locked, flush+fsync, `0600` writer before provider launch. If it fails, settle any current budget reservation at
      zero, print one fixed redacted message, return nonzero, and launch no provider/fallback.
- [ ] Reuse the same ID as the existing completion `event_id`. Preserve existing success/failure, measurement, token,
      cost-basis, evidence, fallback, and result behavior. Do not add retry, abstraction, service, DB, or OTel code.

## VERIFY / STATE

- [ ] Run the focused RED/GREEN test, existing agent-runner/token-budget tests, syntax/compile checks, and the smallest
      relevant profitable-claude suite. Run `git diff --check`; report exact pass counts and diffstat. Luna does not edit
      specs, commit, push, or change live state.
- [ ] Fresh Sol review checks only the design contract, provider-before-persistence ordering, numeric truth, secret
      safety, and unnecessary scope. Luna fixes any required issue in the same files.
- [ ] Sol independently reruns the focused gates, updates this plan and the child/parent specs with measured evidence,
      commits and pushes the producer repository, then advances only to CFO-2a2b.2.
