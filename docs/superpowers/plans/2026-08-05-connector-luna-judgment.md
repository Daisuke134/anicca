# Connector Luna Judgment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the existing verified event goal/serendipity decision through a locally executed, Codex-pinned `gpt-5.6-luna` bounded worker without allowing the model to claim registration success.

**Architecture:** Keep `event-goal-serendipity.js` as the only grounding and validation authority, but add a provider-neutral structured-decision seam. A new Connector adapter invokes the existing `runtime/agent-runner/agent_runner.py` with `repeatable-agent`, pins provider `codex`, verifies the summary selected `gpt-5.6-luna`, reads only the result inside its owner-only evidence directory, and passes that raw decision back through the existing grounding validator.

**Tech Stack:** Node.js CommonJS, Node test runner, Python agent-runner subprocess, JSON Schema, existing Luma verified inventory/ranking contracts.

## Global Constraints

- Work only in `/Users/anicca/Projects/life-manager-main/.worktrees/connector-native-completion` on `feature/connector-native-completion`.
- Follow RED → GREEN and commit/push this slice before Task 3.
- Luna returns ranking and natural-language reasons only; it never verifies registration, Calendar, receipt, QR, or Telegram success.
- Pin `AGENT_RUNNER_PROVIDER=codex` and reject any result whose summary is not `selected_provider=codex`, `selected_model=gpt-5.6-luna`, `status=success`.
- Never print or return prompt text, provider stdout/stderr, environment values, or raw result paths.
- Preserve the current Gemini transport as a compatibility fallback until the native runtime switches to Luna in Task 3.

---

### Task 1: Provider-neutral grounded decision seam

**Files:**
- Modify: `apps/life-manager/lib/event-goal-serendipity.js`
- Test: `apps/life-manager/lib/event-goal-serendipity.test.js`

**Interfaces:**
- Consumes: existing `inferEventGoalSerendipity(input, options)` input.
- Produces: optional `options.generateDecision({ prompt, schema, timeoutMs }) -> Promise<object>`; returned object still passes `groundModelDecision` and `validateEventGoalSerendipity`.

- [x] **Step 1: Write the failing test**

```js
test("a structured model generator still passes the existing grounding boundary", async () => {
  const input = { ...await sources(), goals: GOALS };
  let request;
  const result = await inferEventGoalSerendipity(input, {
    generateDecision: async (value) => {
      request = value;
      return modelDecision();
    },
  });
  assert.equal(result.ranked_events.length, 2);
  assert.match(request.prompt, /untrusted data/i);
  assert.equal(request.schema.type, "object");
  assert.equal(request.timeoutMs, GOAL_EVALUATION_TIMEOUT_MS);
  assert.equal(isVerifiedEventGoalSerendipity(result), true);
});
```

- [x] **Step 2: Run RED**

Run: `node --test lib/event-goal-serendipity.test.js`

Expected: the new test fails with `EVENT_GOAL_SERENDIPITY_CONFIG_FAILED` because `generateDecision` is not consumed.

- [x] **Step 3: Implement the minimum seam**

Build `eventData`, `prompt`, and schema exactly once. When `generateDecision` is a function, await it with a frozen request and treat its return value as the raw model decision. Otherwise keep the existing Gemini request and response parsing unchanged. Both paths then execute the same `groundModelDecision` and `validateEventGoalSerendipity` code.

- [x] **Step 4: Run GREEN**

Observed: 8/8 pass, including all existing Gemini compatibility and bounded-error tests.

Run: `node --test lib/event-goal-serendipity.test.js`

Expected: all existing Gemini/error tests and the new provider-neutral test pass.

### Task 2: Luna-pinned local agent-runner adapter

**Files:**
- Create: `apps/life-manager/lib/connector-luna-judgment.js`
- Test: `apps/life-manager/lib/connector-luna-judgment.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `{ dateInventory, preferenceRanking, profile, evidenceDir, repoRoot, runnerPath? }` where profile passes `isVerifiedConnectorProfile`.
- Produces: `runConnectorLunaJudgment(input, deps?) -> Promise<VerifiedEventGoalSerendipity>`.
- Calls: `inferEventGoalSerendipity({ dateInventory, preferenceRanking, goals: profile.goals }, { generateDecision })`.

- [x] **Step 1: Write failing adapter tests**

```js
test("Connector judgment accepts only a Luna-pinned structured runner result", async () => {
  const result = await runConnectorLunaJudgment(validInput(), {
    runAgentRunner: async ({ prompt, schema }) => ({
      summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-luna" },
      value: modelDecision(), prompt, schema,
    }),
  });
  assert.equal(isVerifiedEventGoalSerendipity(result), true);
});

test("Connector judgment rejects fallback models and unverified profiles", async () => {
  await assert.rejects(runConnectorLunaJudgment(validInput(), {
    runAgentRunner: async () => ({
      summary: { status: "success", selected_provider: "claude-direct", selected_model: "sonnet" },
      value: modelDecision(),
    }),
  }), /Connector Luna judgment unavailable/);
});
```

- [x] **Step 2: Run RED**

Run: `node --test lib/connector-luna-judgment.test.js`

Expected: FAIL with `MODULE_NOT_FOUND` for `connector-luna-judgment.js`.

- [x] **Step 3: Implement the adapter and production subprocess boundary**

The default runner must:

```text
python3 runtime/agent-runner/agent_runner.py
  --task-class repeatable-agent
  --prompt-stdin
  --schema <owner-only evidenceDir/schema.json>
  --evidence-dir <owner-only evidenceDir>
  --task-label connector-event-judgment
  --loop connector
  --workdir <repoRoot>
```

Set `AGENT_RUNNER_PROVIDER=codex` in the child environment. Require exit 0; parse the one summary JSON object; require Luna/codex/success; resolve `result_path` and require it is a regular file strictly inside `evidenceDir`; parse the structured value. Convert every failure to `Connector Luna judgment unavailable` without raw child output.

- [x] **Step 4: Register tests and run GREEN regression suites**

Run: `node --test lib/connector-luna-judgment.test.js lib/event-goal-serendipity.test.js`

Add `lib/connector-luna-judgment.test.js` and `lib/connector-native-write-pipeline.test.js` to the fixed `test:outbound` list, then run: `npm run test:outbound`

Expected: zero failures.

Observed: focused Luna/grounding suite 11/11 pass; `npm run test:outbound` 280/280 pass with the new Luna and native write-pipeline tests present in the executed command.

- [x] **Step 5: Record evidence, commit, and push**

Update this plan's checkboxes and observed RED/GREEN counts, then run:

```bash
git add apps/life-manager/lib/event-goal-serendipity.js \
  apps/life-manager/lib/event-goal-serendipity.test.js \
  apps/life-manager/lib/connector-luna-judgment.js \
  apps/life-manager/lib/connector-luna-judgment.test.js \
  docs/superpowers/plans/2026-08-05-connector-luna-judgment.md
git commit -m "feat(connector): route event judgment through Luna"
git push
```

## Plan Self-Review

- Spec coverage: the plan pins Luna locally, preserves existing grounding, and keeps every external-effect success decision outside the model.
- Scope: this plan ends at a verified judgment object; Task 3 owns default native runtime and write-pipeline integration.
- Type consistency: the adapter returns the existing `VerifiedEventGoalSerendipity` object consumed by the Task 5 write pipeline.
- No placeholder steps or unbounded provider fallback remain.
