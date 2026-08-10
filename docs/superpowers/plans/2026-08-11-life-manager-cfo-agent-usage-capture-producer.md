# CFO-2a2b.1b — Producer Write-Ahead Attempt Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use Superpowers test-driven-development and
> verification-before-completion. Execute checkboxes in order. Luna owns production/test edits; Sol owns this plan,
> review, final verification, state, commit, and push.

**Status:** COMPLETE — write-ahead boundary, fresh review, independent verification, and feature push done

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

- [x] Extend the existing subprocess harness with four bounded boundary cases. The provider stub must observe its
      already-fsynced attempt row at its own launch; success and failure completions reuse that ID. Forced completion
      failure leaves the attempt durable. Forced attempt-ledger failure launches neither provider nor fallback and a
      current budget reservation is settled to zero. Equal resolved attempt/usage paths are rejected before provider,
      ledger, or evidence effects.
- [x] Keep fixtures private and assert only fixed/count/schema facts. No paid provider, network, live ledger, live
      evidence, Telegram, launchd, or source-repo state is touched.

## GREEN

- [x] Resolve the usage path and `ANICCA_USAGE_ATTEMPT_LEDGER` once. Default the latter to
      `agent-usage-attempts.jsonl` beside the usage ledger and reject equal resolved paths before effects.
- [x] Generate one new 24-lowercase-hex ID per candidate attempt. Append the exact attempt schema with the existing
      locked, flush+fsync, `0600` writer before provider launch. If it fails, settle any current budget reservation at
      zero, print one fixed redacted message, return nonzero, and launch no provider/fallback.
- [x] Reuse the same ID as the existing completion `event_id`. Preserve existing success/failure, measurement, token,
      cost-basis, evidence, fallback, and result behavior. Do not add retry, abstraction, service, DB, or OTel code.

## VERIFY / STATE

- [x] Run the focused RED/GREEN test, existing agent-runner/token-budget tests, syntax/compile checks, and the smallest
      relevant profitable-claude suite. Run `git diff --check`; report exact pass counts and diffstat. Luna does not edit
      specs, commit, push, or change live state.
- [x] Fresh Sol review checks only the design contract, provider-before-persistence ordering, numeric truth, secret
      safety, and unnecessary scope. Luna fixes any required issue in the same files.
- [x] Sol independently reruns the focused gates, updates this plan and the child/parent specs with measured evidence,
      commits and pushes the producer repository, then advances only to CFO-2a2b.2.

## Completion evidence

- The first RED test draft grew to 119 LOC and was stopped by the Ponytail gate. Luna reused the existing harness and
  reduced the same four contracts to 38 added test lines; production added 29 and removed 5. Final slice scope is two
  files, `+67/-5`, below the 100-LOC target.
- Genuine compact RED produced five failures. GREEN proves the provider stub sees the fsynced attempt row at launch,
  success/failure completions share its unique 24-hex ID, a blocked usage ledger leaves one durable unmatched attempt,
  a blocked attempt ledger launches neither provider nor fallback and settles the reservation to zero, and equal paths
  or null/blank models fail before effects.
- Luna passed focused `4/4`, strict/provider `2/2`, compile, and diff checks. Full agent-runner ran 62 tests with 60 pass
  and the same two clean-base failures recorded in CFO-2a2b.1a. Sol independently passed the combined mandatory set
  `6/6`; the latest OpenClaw fallback tests passed `2/2` after merging concurrent provider changes.
- Fresh Sol first found the missing nonempty-model gate; Luna fixed it in the same files and fresh re-review returned
  `ship — Spec ✅`. Producer commit `ef233a90` plus the latest provider-recovery merge is pushed to
  `origin/feature/cfo-agent-usage-capture`. No live producer, paid provider, source ledger, launchd, or Telegram runtime
  was changed.
