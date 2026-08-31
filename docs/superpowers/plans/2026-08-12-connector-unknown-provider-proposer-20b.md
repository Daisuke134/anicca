# Unknown-provider Bounded Proposer Seam Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact Browser Harness production/test files.

**Goal:** Allow the same one explicitly configured extension provider to ask the existing bounded Terra proposer for one sanitized same-page control, while every unconfigured provider remains rejected.

**Architecture:** Add one optional `extensionProvider` token to `createBoundedActionProposer`. Reuse the existing provider token contract, structured control enum, 10-step cap, evidence directory, and parent-owned private-value boundary. The default constructor remains seven-provider-only. Do not change Harness execution, factory/router, or add a provider implementation.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 4–10 LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 30–60 LOC.

## Grounding

- Existing local `createBoundedActionProposer` already sanitizes controls, constrains the JSON schema to an exact enum, permits one action, caps steps at 10, and requires Codex Terra success metadata.
- Node.js CommonJS modules: <https://nodejs.org/api/modules.html#modules-commonjs-modules> — reuse the current constructor/export; no package is required.
- KokuchPro guide: <https://www.kokuchpro.com/pages/guide/> — organizer-defined questions mean the model may choose a public control, but the parent must continue to resolve all answers and verify the result.
- Prior read-only site measurement preserved shared CDP pages `4 → 5 → 4` and performed no external action.

### Task 1: Add the single configured proposer extension

**Files:**

- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] **Step 1: Write RED proposer tests**

  Require the exact configured extension token to reach the existing structured runner with sanitized controls only. Require unconfigured, second-token, malformed, and built-in collisions to fail closed.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js
  ```

- [x] **Step 3: Implement the smallest GREEN predicate**

  Validate the optional token once and use one local predicate in the proposer input gate. Do not alter prompt, schema, provider-specific native fast paths, result verification, or action execution.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js lib/connector-browser-harness-adapter.test.js
  node --check lib/connector-production-browser-harness.js
  git diff --check
  ```

- [x] **Step 5: Report without committing**

  Write RED/GREEN counts, exact diff, contract mapping, and concerns to the SDD report. Sol reviews, commits, and pushes.

## Acceptance checklist

- [x] Exact configured extension token can propose one action through the existing bounded runner.
- [x] Prompt and schema contain only provider name, step/state, and sanitized public controls; no private values or candidate body are added.
- [x] Unconfigured or non-exact providers and malformed/colliding configuration fail closed.
- [x] Existing seven providers, max 10 steps, Terra metadata gate, evidence path, native fast paths, and return contract are unchanged.
- [x] No factory/router/native/discovery/Calendar/evidence/launchd/external effects.

## Result

Luna added the optional proposer token with RED `150/151`. Sol's independent pre-review found an omitted-provider `undefined === undefined` hole before commit; Luna added the missing-provider RED and guarded extension equality with `extensionProvider != null`. Final Harness+adapter tests are `155/155`, syntax/diff checks pass. Fresh Sol review reports Spec compliance and Code quality PASS with Critical/Important 0. Code commit: `b45f183dd`.
