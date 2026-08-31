# Unknown-provider Browser Harness Seam Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact Browser Harness production/test files.

**Goal:** Let one explicitly configured event-site extension use the existing same-page bounded Browser Harness without weakening the seven-provider allowlist or enabling arbitrary domains.

**Architecture:** Add one optional `extensionProvider` plus its `extensionWorkflow` to the existing Browser Harness constructor. The configured token reuses the current generic observation, one-action proposal, private-value resolution, mutation dedupe, and verified `registered|pending` readback path. Without that exact constructor pair, behavior is equivalent and unknown providers still fail closed. Do not add a registry, generic crawler, package, service, or production provider yet.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 12–24 LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 45–85 LOC.

## Grounding

- KokuchPro Tokyo listing: <https://www.kokuchpro.com/s/area-%E6%9D%B1%E4%BA%AC%E9%83%BD/> — public listing exposes occurrence-specific event URLs and `募集中`; read-only CDP measurement found 80 unique detail URLs on the first page.
- KokuchPro participant/organizer guide: <https://www.kokuchpro.com/pages/guide/> — the official flow distinguishes `無料イベント・会場払い・銀行振込` and permits organizer-defined additional application questions, so price and required-field checks must remain fail-closed.
- KokuchPro live detail: <https://www.kokuchpro.com/event/97accb85cbf2870c2f3b989b3d4e0e94/3847918/> — the official page separately exposes `料金制度 有料イベント`, a `￥1,000` ticket, `募集中`, and `申込む`; text containing “無料” elsewhere cannot prove a free ticket.
- Node.js CommonJS modules: <https://nodejs.org/api/modules.html#modules-commonjs-modules> — preserve the existing local constructor/export pattern; no dependency is needed.
- Read-only CloakBrowser measurement used one isolated page, made zero clicks/fills/submits, inspected 35 detail pages, found zero strict `料金制度 無料イベント`, and restored pages `4 → 5 → 4`.

## Contract

### Task 1: Add the single configured extension seam

**Files:**

- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] **Step 1: Write RED constructor and fallback tests**

  Require an exact configured extension provider/workflow to enter the existing generic fallback, while partial config, malformed tokens, unconfigured unknown tokens, and a second token fail closed.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js
  ```

  Expected: only the new extension-seam assertions fail because the constructor has no extension options.

- [x] **Step 3: Implement the smallest GREEN constructor seam**

  Validate the optional pair once, use an instance-local provider predicate, select the extension workflow only for the exact token, and reuse the existing generic fallback unchanged.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js lib/connector-browser-harness-adapter.test.js
  node --check lib/connector-production-browser-harness.js
  git diff --check
  ```

- [x] **Step 5: Report without committing**

  Record RED/GREEN commands, exact test counts, changed lines, and any remaining risk in the SDD report. Sol performs review, commit, and push.

## Acceptance checklist

- [x] RED: an exact configured extension provider cannot currently enter the existing generic Browser Harness path.
- [x] Constructor accepts either neither extension option or both an exact safe provider token and a workflow with `readProviderState`; partial/malformed configuration fails closed.
- [x] Only the exact configured extension token is added to that Harness instance; any other unknown token remains rejected.
- [x] Configured extension reuses the existing generic observe → propose one action → perform → verified readback loop on the supplied page; it cannot create/navigate/close a browser target.
- [x] Success requires extension workflow readback status `registered` or `pending`; unavailable/absent/malformed proof is a safe failed result and never saves an action.
- [x] Existing seven providers, provider-specific guards, mutation dedupe, max-step boundary, and private-value resolver remain unchanged.
- [x] Focused Harness tests, syntax, diff check, mutation proof, and fresh Sol review pass.
- [x] Do not change production factory/router/native order, discovery, Calendar/evidence, launchd, or perform a real application in this slice.

## Result

Luna implemented the exact two-file seam with RED `147/149` and initial GREEN `149/149`. Fresh Sol found that an extension must never be able to trust an action-result `provider_state`; round 1 added an explicit extension cache exclusion plus an eight-case independent-readback regression matrix. Final focused/adjacent tests are `150/150` and `154/154`, syntax and diff checks pass, and fresh Sol re-review reports Spec compliance and Code quality both pass with Critical/Important 0. Code commits: `e44a11451`, `0d99afad4`.
