# CFO-2a2b.4 — Real Local Capture E2E and Close Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and
> superpowers:test-driven-development to implement this plan task-by-task. Luna owns the one test-harness edit; Sol
> owns this plan, real verification, review, state, commit, and push.

**Status:** READY FOR LUNA — fresh plan review `ship`

**Goal:** Close durable agent-usage capture with real local evidence: existing owner usage ledgers stay byte-identical,
historical rows without write-ahead attempts report `capture_not_started` rather than fake complete coverage, and the
real Python provider boundary proves both same-ID completion and a durable missing completion without a paid provider.

**Architecture:** Update the existing read-only Node real-ledger E2E to the completed hourly receipt/span contract; it
continues to clone real usage bytes into a `mkdtemp` sandbox and hash the real sources before/after. Separately, Sol
runs the two existing real Python `agent_runner.py` subprocess tests that use a fake local `codex` executable: one
proves attempt-before-launch and same-ID completion, the other makes the usage target a directory and proves the
durable attempt survives completion-write failure. No new integration harness or production code is needed.

**Tech Stack:** Node.js 20, existing CommonJS real-E2E script, Python `unittest`, real `agent_runner.py`, temporary
local files, fake local provider binary.

## Global Constraints

- Ponytail `full`: reuse one existing Node E2E and two existing Python subprocess tests; no new file, helper service,
  fixture framework, provider call, dependency, DB, OTel exporter/store, launchd mutation, Telegram, pricing, or cloud.
- Luna implementation scope: exactly one existing file, `apps/life-call/test/cfo-local-agent-usage-real-e2e.js`, and
  at most 35 added LOC. Sol's post-review plan/spec state updates are separate controller documentation.
- The real owner ledgers are read-only: `~/.local/state/{life-manager,anicca}/telemetry/agent-usage.jsonl`. Record their
  SHA-256 digests before the sandbox run and require identical bytes/digests afterward.
- Do not read, print, persist, or commit raw rows, token values, paths, owner identity, prompts, outputs, event IDs,
  credentials, account data, or exception text. Stdout remains one fixed counts-only PASS/FAIL line.
- Existing historical usage predates the attempt ledger. Its exact truthful capture result is two reconciled empty
  receipts, two `capture_not_started` source exceptions, sorted unique top exception `capture_not_started`, and
  top-level `status=partial`; historical usage events remain measured and are not relabeled missing.
- The isolated Python probes use fake executables and temporary ledgers only. They must make no paid/provider/network
  request and must not touch either owner ledger.

---

### Task 1: Update and run the real local capture closure

**Files:**

- Modify/Test: `apps/life-call/test/cfo-local-agent-usage-real-e2e.js`

**Interfaces:**

- Preserves the current executable interface: `node test/cfo-local-agent-usage-real-e2e.js` and exit 0/1.
- Updates the frozen receipt exact keys to `capture_sources`, `collected_at`, `coverage_exceptions`, `sources`, `status`.
- Requires both exact capture envelopes to be `status="reconciled"`, with the pure empty receipt, null cutover, all
  integer counts zero, and `coverage_exceptions=["capture_not_started"]`.
- Updates the one existing INTERNAL span exact-deep-equality oracle with the 12 capture attributes from CFO-2a2b.3.
  Expected capture values are: `status="partial"`, source count 2, reconciled source count 2, all eight row counters 0,
  capture coverage-exception count 2 (one per source), and top-level unique coverage-exception count 1. Existing usage
  event counts and source attributes remain derived exactly.
- PASS stdout adds only `capture_not_started_sources=2`; it prints no per-row or private value.

- [ ] **Step 1: Run the stale harness for genuine RED**

```bash
cd apps/life-call
node test/cfo-local-agent-usage-real-e2e.js
```

Expected: fixed `FAIL` and exit 1 because the old exact receipt/status/span contract rejects the new capture fields.
Missing dependencies or missing real source files are blockers, not RED.

- [ ] **Step 2: Make the minimum one-file harness update**

Update only the exact receipt/capture/span assertions and counts-only PASS line described above. Keep real-source scan,
clone, permissions, causal-chain verification, console-silence guard, before/after digest comparison, provider shutdown,
and exact-prefix temp cleanup unchanged. Do not add a producer invocation to Node.

- [ ] **Step 3: Run GREEN and regression checks**

```bash
cd apps/life-call
node test/cfo-local-agent-usage-real-e2e.js
node --test lib/cfo-local-agent-capture-reconciliation.test.js lib/cfo-local-agent-usage-runner.test.js
npm run test:cfo
npm test
node --check test/cfo-local-agent-usage-real-e2e.js
git diff --check
```

Expected: every command exits 0; Node E2E emits one counts-only PASS line with `sources=2`,
`capture_not_started_sources=2`, and `spans=1`. Luna reports exact counts/LOC/diff and touches no other file; no commit,
push, live mutation, or Telegram.

- [ ] **Step 4: Sol runs the existing real Python provider-boundary probes**

```bash
cd /Users/anicca/profitable-claude/.worktrees/cfo-agent-usage-capture
python3 skills/gig-work/tests/test_agent_runner.py \
  AgentRunnerContractTest.test_attempt_row_is_visible_before_launch_and_completion_reuses_id \
  AgentRunnerContractTest.test_usage_completion_failure_leaves_durable_unmatched_attempt
```

Expected: 2/2 pass. These tests execute the real Python runner against a fake local `codex`; they prove the attempt is
visible before launch, success/failure completion reuses the same random 24-hex ID, and a completion-write failure
leaves the attempt durable with measured usage evidence. They perform no paid or network provider call.

- [ ] **Step 5: Fresh review and close state**

Fresh Sol review checks real-ledger immutability, historical cutover truth, exact receipt/span privacy, fake-provider
boundary evidence, temp cleanup, and Ponytail scope. Luna fixes only load-bearing findings in the same one harness file.
Sol independently re-runs the Node E2E and both Python probes, updates this plan and parent/child specs, commits/pushes,
sends one counts-only Telegram milestone, checks CFO-2a2b complete, and advances only to CFO-2a3.
