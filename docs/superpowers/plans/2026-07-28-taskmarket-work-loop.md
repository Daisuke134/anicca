# TaskMarket WORK Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `earn/taskmarket` slot that autonomously produces and submits one GPT Image 2 still-image bounty per wake.

**Architecture:** A pure orchestration module owns selection and state transitions, while a separate x402 image client owns payment and generation. `run.sh` is the existing loop-compatible entrypoint; the existing award observer remains the only income recorder.

**Tech Stack:** Node.js ESM, Node test runner, TaskMarket CLI, `@blockrun/llm`, `viem`, shell, launchd.

## Global Constraints

- One wake submits at most one task.
- Only active, unstaked, unsubmitted still-image tasks are supported.
- Image model is exactly `openai/gpt-image-2`, size `1024x1024`.
- Per-image quote cap is `$0.06`; daily cap is `$0.12`; post-reservation float floor is `$0.25`.
- No award is income until the existing finalized external-payment observer records it.
- No private key appears in args, stdout, logs, artifacts, or repository files.
- Official TaskMarket readback is the idempotency authority.

---

### Task 1: Pure TaskMarket selection

**Files:**
- Create: `skills/earn/taskmarket/taskmarket-work.mjs`
- Create: `skills/earn/taskmarket/taskmarket-work.test.mjs`

**Interfaces:**
- Produces: `selectTask({tasks, submissions, now, maxImageCostUsd}) -> task|null`
- Produces: `classifyTask(task) -> {supported:boolean, reason:string}`

- [ ] **Step 1: Write failing tests**

Cover active/window/stake/idempotency gates, unsupported short-film rejection,
20× reward-to-cost floor, and expiry/submission-count/reward ordering with
literal fixtures.

- [ ] **Step 2: Verify RED**

Run:

```bash
node --test skills/earn/taskmarket/taskmarket-work.test.mjs
```

Expected: FAIL because `taskmarket-work.mjs` does not exist.

- [ ] **Step 3: Implement minimal pure selection**

Implement only the exported classifiers and selector required by the tests.

- [ ] **Step 4: Verify GREEN**

Run the same test command. Expected: all selection tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/taskmarket
git commit -m "feat(agent-economy): select TaskMarket image work"
```

### Task 2: Capped GPT Image 2 x402 client

**Files:**
- Create: `skills/earn/taskmarket/x402-image-client.mjs`
- Create: `skills/earn/taskmarket/x402-image-client.test.mjs`

**Interfaces:**
- Produces: `generateImage({prompt, walletKey, fetchImpl, signPayment, reserveSpend, maxQuoteUsd}) -> {url,model,costUsd}`

- [ ] **Step 1: Write failing boundary tests**

Use complete 402 and 200 response fixtures. Assert exact model/size request,
wrong quote rejection, over-cap rejection, missing HTTPS URL rejection, and
one successful signed paid retry.

- [ ] **Step 2: Verify RED**

```bash
node --test skills/earn/taskmarket/x402-image-client.test.mjs
```

Expected: FAIL because the client module does not exist.

- [ ] **Step 3: Implement minimal client**

Reuse the working `@blockrun/llm` payment construction pattern from
`skills/earn/x402-sell/image-resale.mjs`. Do not introduce another payment
library.

- [ ] **Step 4: Verify GREEN**

Run the same test command. Expected: all client tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/taskmarket
git commit -m "feat(agent-economy): buy GPT Image 2 with x402"
```

### Task 3: One-pass TaskMarket executor

**Files:**
- Modify: `skills/earn/taskmarket/taskmarket-work.mjs`
- Modify: `skills/earn/taskmarket/taskmarket-work.test.mjs`
- Create: `skills/earn/taskmarket/run.sh`

**Interfaces:**
- Produces: `runTaskMarketPass(options, deps) -> result`
- Consumes: TaskMarket CLI JSON, `generateImage`, filesystem, and earn ledger.

- [ ] **Step 1: Write failing pass tests**

Assert that one eligible task creates exactly `hero.png`,
`concept-note.md`, and `sources.md`; invokes submit once with all three files;
requires same-task official readback; appends a zero-income cost row correlated
to `WAKE_ID`; and makes a second pass a no-spend `already_submitted`.

- [ ] **Step 2: Verify RED**

```bash
node --test skills/earn/taskmarket/taskmarket-work.test.mjs
```

Expected: FAIL because `runTaskMarketPass` is absent.

- [ ] **Step 3: Implement the minimal pass and wrapper**

Use `execFile` with argv arrays for every TaskMarket CLI call. Validate PNG
signature and IHDR width/height before submit. Emit exactly one JSON object on
stdout.

- [ ] **Step 4: Verify GREEN**

Run both TaskMarket test files. Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/taskmarket
git commit -m "feat(agent-economy): execute TaskMarket image bounty"
```

### Task 4: Persistent-loop wiring

**Files:**
- Modify: `skills/registry.json`
- Modify: `runtime/loop/__tests__/earn-slot-e2e.test.mjs`

**Interfaces:**
- Produces: live registry slot `earn/taskmarket`
- Consumes: existing per-method earn-slot routing and `ANICCA_ARGS`.

- [ ] **Step 1: Write failing E2E**

Add a fixture registry containing `earn/taskmarket`, a temporary real
`run.sh`, and a brain response choosing the slot with
`{"action":"execute"}`. Assert the child receives args, wake ID, and earn
ledger path and the wake ledger records `slot=earn/taskmarket`.

- [ ] **Step 2: Verify RED**

```bash
node --test runtime/loop/__tests__/earn-slot-e2e.test.mjs
```

Expected: the new TaskMarket case FAILS before registry/fixture wiring.

- [ ] **Step 3: Wire the live slot**

Declare the slot as `status=live`, `risk=safe`, with a tool description that
states its supported task type, one-task bound, and action contract.

- [ ] **Step 4: Verify GREEN and regressions**

```bash
node --test \
  skills/earn/taskmarket/taskmarket-work.test.mjs \
  skills/earn/taskmarket/x402-image-client.test.mjs \
  runtime/loop/__tests__/earn-slot.test.mjs \
  runtime/loop/__tests__/earn-slot-e2e.test.mjs \
  runtime/loop/__tests__/slot-allowlist.test.mjs
```

Expected: all tests PASS with zero failures.

- [ ] **Step 5: Commit**

```bash
git add skills/registry.json runtime/loop/__tests__/earn-slot-e2e.test.mjs
git commit -m "feat(agent-economy): expose TaskMarket work slot"
```

### Task 5: Production deployment and real submission

**Files:**
- Modify: `~/Library/LaunchAgents/ai.anicca.agent-economy-loop.plist`
- Modify: central agent-economy SSOT and evidence after readback

**Interfaces:**
- Consumes: merged/pushed canonical code and existing launchd supervisor.
- Produces: one official TaskMarket submission and one cost-ledger row.

- [ ] **Step 1: Push implementation and update canonical checkout**

Fetch, push the feature branch, merge through the repository's normal
integration path, then fast-forward `/Users/anicca/anicca`.

- [ ] **Step 2: Sync runtime and configure focused slot**

Set `ANICCA_SLOT_ALLOWLIST=earn/taskmarket`, keep the existing wallet/reserve
settings, and reload only `ai.anicca.agent-economy-loop`.

- [ ] **Step 3: Trigger the existing loop**

Use:

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.agent-economy-loop
```

Do not run the executor directly.

- [ ] **Step 4: Verify real boundaries**

Read back:

```bash
taskmarket task my-submissions
taskmarket stats
launchctl print gui/$(id -u)/ai.anicca.agent-economy-loop
```

Require a new same-task submission ID, loop exit/continued-running evidence,
and a cost row with `earn_usdc=0`.

- [ ] **Step 5: Re-trigger award observer**

```bash
launchctl kickstart -k gui/$(id -u)/ai.anicca.life-manager-taskmarket-ledger
```

Require exit 0 and `recorded=0` unless an actual external award occurred.

- [ ] **Step 6: Update SSOT, commit, and push**

Record the exact task ID, model, x402 cost, submission ID, Base transaction,
readback, and evidence limit. Never state that an award or profit exists
before external settlement.

