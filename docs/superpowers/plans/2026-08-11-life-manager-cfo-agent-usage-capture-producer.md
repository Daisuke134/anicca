# CFO-2a2b.1b — Producer Write-Ahead Attempt Plan

> **For Luna:** use Superpowers test-driven-development and verification-before-completion. Luna owns production/test
> edits; Sol owns this plan, review, final verification, state, commit, and push.

**Status:** READY FOR LUNA — CFO-2a2b.1a is closed

**Goal:** Before the shared agent runner can launch a provider, fsync one minimal attempt row; reuse its unique ID on
the existing completion usage row so the later CFO join can detect a missing completion exactly.

**Architecture:** Extend only the existing producer. Keep the usage schema and locked JSONL writer. Add one adjacent
attempt ledger and one unique ID per candidate attempt. Do not change the CFO consumer, hourly job, Telegram,
Moneytree, OTel, pricing, DB, or cloud.

**Hard scope gate:** exactly two existing files and <=100 gross added LOC total:

- `skills/agent-runner/agent_runner.py`
- `skills/gig-work/tests/test_agent_runner.py`

## RED → GREEN order

Run each named regression red before its matching production change, then green before the next behavior:

1. `test_attempt_row_is_visible_before_launch_and_completion_reuses_id`: provider stub opens the attempt ledger at
   launch; both success and failure see one already-durable exact eight-key row and reuse its ID on completion. Assert
   `os.stat(attempt).st_mode & 0o777 == 0o600`. RED: the attempt file does not exist at provider launch.
2. `test_usage_completion_failure_leaves_durable_unmatched_attempt`: make the usage target unwritable after the
   provider starts; the provider succeeds, attempt stays durable, evidence contains a non-empty `telemetry_error`, and
   no completion row exists. RED: no durable attempt exists independently of the failed completion.
3. `test_attempt_ledger_failure_blocks_all_providers_and_settles_zero`: force attempt append failure; exact stderr is
   `agent-runner: usage attempt capture failed`, no provider/fallback marker exists, and the one current budget
   settlement is zero/unavailable. RED: the provider marker exists or no zero settlement exists.
4. `test_equal_usage_and_attempt_ledgers_are_rejected_before_effects`: same resolved path plus empty/whitespace
   `loop`, `task_label`, `provider`, and `model` each return the fixed invalid-input prefix before evidence, budget,
   ledger, provider, or fallback effects. RED: at least one invalid boundary reaches an effect or raises after lookup.
5. Extend existing `test_healthy_sonnet_after_codex_quota_never_invokes_openclaw`: the real two-candidate fallback
   writes two attempts and two completions, IDs are pairwise equal by attempt and mutually unique across candidates.
   RED: there is no attempt ledger to join to the two completions.

Fixtures stay private. No paid provider, network, live ledger/evidence, Telegram, launchd, or source state is touched.

## GREEN

- [ ] Resolve usage and attempt paths once. Default attempt path beside usage as `agent-usage-attempts.jsonl`; reject
  equal resolved paths before effects.
- [ ] Validate non-empty `loop`, `task_label`, and every candidate `provider`/`model` before effects. Generate one
  24-lowercase-hex ID per candidate attempt. Append the exact attempt schema with the existing locked,
  flush+fsync, `0600` writer before launch. On failure, settle a current reservation at zero, print one fixed redacted
  message, return nonzero, and launch no provider/fallback.
- [ ] Reuse the ID as the completion `event_id`. Preserve success/failure, measurement, tokens, cost basis, evidence,
  fallback, and result behavior. Add no retry, abstraction, service, DB, or OTel code.

Use this direct production shape; do not introduce a helper or schema class:

```python
for value, reason in ((parsed.loop, "loop"), (parsed.task_label, "task label")):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{reason} must be a nonempty trimmed string")
for candidate in candidates:
    for key in ("provider", "model"):
        value = candidate.get(key) if isinstance(candidate, dict) else None
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"candidate {key} must be a nonempty trimmed string")

attempt_event_id = uuid.uuid4().hex[:24]
attempt_started = utc_now()
append_usage_event(attempt_ledger_path, {
    "version": 1, "event_id": attempt_event_id, "timestamp": attempt_started,
    "loop": parsed.loop, "task_label": parsed.task_label, "attempt": index,
    "provider": provider, "model": effective_candidate["model"],
})
```

The tests must contain these exact core assertions, folded into existing fixtures:

```python
self.assertEqual(os.stat(attempt).st_mode & 0o777, 0o600)
self.assertEqual(completion["event_id"], durable["event_id"])
self.assertTrue(row["telemetry_error"])
self.assertEqual(proc.stderr.strip(), "agent-runner: usage attempt capture failed")
self.assertEqual(len(set(attempt_ids)), 2)
self.assertEqual(attempt_ids, completion_ids)
```

## VERIFY / STATE

- [ ] Run the five focused commands:
  `python3 -m unittest skills.gig-work.tests.test_agent_runner.AgentRunnerContractTest.test_attempt_row_is_visible_before_launch_and_completion_reuses_id`,
  `python3 -m unittest skills.gig-work.tests.test_agent_runner.AgentRunnerContractTest.test_usage_completion_failure_leaves_durable_unmatched_attempt`,
  `python3 -m unittest skills.gig-work.tests.test_agent_runner.AgentRunnerContractTest.test_attempt_ledger_failure_blocks_all_providers_and_settles_zero`,
  `python3 -m unittest skills.gig-work.tests.test_agent_runner.AgentRunnerContractTest.test_equal_usage_and_attempt_ledgers_are_rejected_before_effects`, and
  `python3 -m unittest skills.gig-work.tests.test_agent_runner.AgentRunnerContractTest.test_healthy_sonnet_after_codex_quota_never_invokes_openclaw`.
  Then run `python3 -m unittest skills.gig-work.tests.test_agent_runner`,
  `python3 -m unittest skills.agent-runner.tests.test_token_budget`, and
  `python3 -m py_compile skills/agent-runner/agent_runner.py skills/gig-work/tests/test_agent_runner.py`.
  Run `git diff --check`, `git diff --numstat`, and require exactly the two owned files with summed gross additions
  `<=100`. Luna edits no docs, live state, commit, or remote.
- [ ] Fresh Sol review is retained because the user's explicit adversarial-review direction and global Sol/Luna routing
  outrank the producer repository's generic Codex-review ban. It checks provider-before-persistence ordering, numeric
  truth, secret safety, and scope only; Luna fixes required issues in the same files.
- [ ] Sol reruns gates, updates this plan and child/parent specs, commits/pushes the producer repo, then advances only to
  CFO-2a2b.2.
