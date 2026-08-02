# O1C-23 YC Current Program Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale `yc-w26` batch, deadline, amount, and application URL claims with fresh content-addressed facts read from YC-owned Apply and Deal pages, then synchronize only those fact paths into the installed legacy runtime.

**Architecture:** A pure CommonJS builder validates two official source observations and an agent-owned semantic assessment, returning the complete repository fact manifest and privacy-minimal receipt digest. A second pure projection function updates an in-memory legacy spec and proves its non-fact digest is unchanged; the verified projection is applied to the exact installed JSON with an original backup. No browser or submission path runs.

**Tech Stack:** Node.js CommonJS, `node:test`, SHA-256, URL/RFC3339 validation, JSON, agent-reach Jina Reader, Git.

## Global Constraints

- Semantic program reading belongs to the agent; deterministic code performs only provenance, integrity, chronology, arithmetic, schema, and bookkeeping checks.
- Official source roles are exactly `apply` and `deal`, rooted at `https://www.ycombinator.com/apply` and `https://www.ycombinator.com/deal`.
- Source bodies and excerpts remain in memory and never enter committed artifacts.
- The repository fact manifest contains no company answer, founder fact, traction value, media path, credential, browser profile, locator, application ID, save control, or submit control.
- The installed legacy spec may change only the fact paths enumerated in the design; all other paths must have the same masked digest before and after.
- O1C-24 through O1C-27 remain out of scope.

---

### Task 1: Closed official-fact receipt builder

**Files:**
- Create: `apps/life-manager/lib/yc-current-program-facts.js`
- Create: `apps/life-manager/lib/yc-current-program-facts.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `buildYcCurrentProgramFactsReceipt(input, { now })`, where `input` contains `legacyConfigId`, `verifiedAt`, two source observations, one agent assessment, and zero-effect counts.
- Produces: a frozen manifest with `schema_version`, compatibility/program identity, batch, deadline, investment, source receipts, assessment-proof hashes, effect counts, and `fact_receipt_digest`.

- [ ] **Step 1: Write a failing literal valid-receipt test**

Create an Apply body literal containing an arbitrary batch label, schedule, deadline display, late-open statement, and Markdown application link. Create a Deal body literal containing arbitrary selected amount strings. Hand-calculate declared SHA-256 values with the test's local `sha` primitive, but assert literal normalized output values independent of production code. Assert that the output contains no source body, excerpt, rationale, cookie, header, or application ID.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd apps/life-manager && node --test lib/yc-current-program-facts.test.js`

Expected: fail because `yc-current-program-facts.js` does not exist.

- [ ] **Step 3: Add adversarial contract tests before implementation**

Add table-driven cases that independently reject: missing/duplicate source roles, wrong official or retrieval URL, query/credential/fragment URL mutation, body/hash/length substitution, missing excerpt, selected text not bound to its excerpt, application URL absent from Apply links, source role substitution, observation after verification, observations over fifteen minutes apart, receipt over five minutes old, deadline without explicit offset, non-integer/negative amounts, fixed plus MFN arithmetic drift, config field mismatch, non-zero write/submit effects, unknown nested fields, and raw secret-shaped fields.

- [ ] **Step 4: Implement the minimal builder**

Implement exact-key validation, URL parsing, SHA-256 recomputation, bounded text checks, excerpt containment and selected-text binding, link inventory parsing, chronology/freshness, RFC3339-with-offset validation, safe-integer arithmetic, exact zero-effect validation, stable canonical hashing, privacy-minimal output, and recursive freezing. Do not encode current batch/deadline/amount values in production code.

- [ ] **Step 5: Run focused tests GREEN and mutation-check the contract**

Run: `cd apps/life-manager && node --test lib/yc-current-program-facts.test.js`

Expected: every valid/adversarial case passes. Mentally mutate source role, amount addition, URL path, or excerpt binding; at least one named test must fail for each mutation.

- [ ] **Step 6: Wire the focused file into outbound regression**

Add `lib/yc-current-program-facts.test.js` to `test:outbound`, then run `cd apps/life-manager && npm run test:outbound`.

Expected: all outbound tests pass with zero failures.

### Task 2: Bounded legacy projection

**Files:**
- Modify: `apps/life-manager/lib/yc-current-program-facts.js`
- Modify: `apps/life-manager/lib/yc-current-program-facts.test.js`

**Interfaces:**
- Consumes: `projectYcCurrentFactsIntoLegacy(legacySpec, factReceipt)`.
- Produces: `{ projected, before_non_fact_digest, after_non_fact_digest, changed_paths }`, with exact equality of the two masked digests.

- [ ] **Step 1: Write RED tests for exact allowed-path projection**

Use a complete literal legacy fixture containing stable `id`, auth, draft resolution, pages, static answers, and submit configuration. Assert that only `name`, `url`, `official_url`, `application_url`, `facts_verified_at`, `current_batch`, `deadline_kind`, `next_deadline`, `deadline`, `amount_range`, `standard_deal`, `fact_sources`, and `fact_receipt_digest` change. Assert a literal sorted `changed_paths` list and equal non-fact digests.

- [ ] **Step 2: Add failure tests before production projection code**

Reject wrong legacy ID, a receipt that fails its digest/schema validation, input mutation, a non-fact drift introduced after projection, and unknown receipt fields. Ensure the original fixture remains byte-equivalent after every call.

- [ ] **Step 3: Implement minimal projection and masked digest**

Clone the input, set only the closed allowed paths from the receipt, set the flat amount range to exact total min/max, set `next_deadline` from the agent-owned compatibility value, compute both masked digests with the same stable serializer, and fail unless they match. Export the function alongside the receipt builder.

- [ ] **Step 4: Run focused and outbound suites GREEN**

Run:

```bash
cd apps/life-manager
node --test lib/yc-current-program-facts.test.js
npm run test:outbound
```

Expected: zero failures.

### Task 3: Fresh official receipt and versioned manifest

**Files:**
- Create: `apps/life-manager/config/yc-w26.json`
- Create: `docs/evidence/funding/2026-08-02-o1c23-yc-current-program-facts.json`

**Interfaces:**
- Consumes: fresh Jina Reader bodies for the two exact YC official URLs and the agent's full-surface assessment.
- Produces: the exact builder output at `apps/life-manager/config/yc-w26.json`, plus a closeout evidence wrapper that records retrieval/direct-origin hashes, tests, review, legacy synchronization, and claim boundary.

- [ ] **Step 1: Fetch both official sources without persistence**

Fetch `https://r.jina.ai/https://www.ycombinator.com/apply` and `https://r.jina.ai/https://www.ycombinator.com/deal` in memory. Separately GET the direct origin pages and record final URL, HTTP 200, content type, byte length, ETag/date where present, and SHA-256. Do not persist bodies, headers, or cookies.

- [ ] **Step 2: Make the agent-owned assessment from full surfaces**

Select exact excerpts and selected text for the current batch, October–December schedule, San Francisco location, on-time deadline, late-open state, application URL, total investment, fixed-safe amount/equity, and MFN-safe amount. Interpret the displayed PT deadline as an offset-bearing instant for the displayed date. Keep the rationale bounded and source-accounted.

- [ ] **Step 3: Generate and validate the versioned manifest**

Pass the live observations and assessment to `buildYcCurrentProgramFactsReceipt`, use its exact output as `apps/life-manager/config/yc-w26.json`, validate JSON, and rerun the builder against the same in-memory observations to require a stable digest.

- [ ] **Step 4: Prove and apply the bounded installed-runtime update**

Read `/Users/anicca/.openclaw/skills/apply-to-funder/funders/yc-w26.json`, require its expected pre-update SHA-256, build the projection, require equal non-fact digests, preserve an exact recovery copy named with the pre-update digest, then apply only the allowed fact paths. Read the installed file back, compare it to the projected object, and record before/after/full/masked digests. Do not run `prepare.sh`, `run.sh`, `submit.sh`, or any browser command.

### Task 4: Independent review, verification, and closeout

**Files:**
- Modify: `docs/evidence/funding/2026-08-02-o1c23-yc-current-program-facts.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] **Step 1: Request independent read-only review**

Review the builder, adversarial tests, manifest, live source proof, legacy masked-digest proof, privacy output, and O1C-24 through O1C-27 boundary. Convert every Critical/Important finding into a RED regression before fixing it.

- [ ] **Step 2: Run fresh verification**

Run focused tests, `npm run test:outbound`, `npm run test:runtime-up`, full `npm test`, `node --check`, JSON validation, artifact SHA-256, installed-runtime readback, masked-digest equality, and `git diff --check`.

- [ ] **Step 3: Commit implementation and record its SHA**

Commit the builder, tests, package wiring, repository manifest, and plan. Record the full implementation SHA in the evidence and canonical spec.

- [ ] **Step 4: Close O1C-23 in the canonical spec**

Check O1C-23, record 54/143 complete and 89 remaining, state the exact current official facts and no-effect boundary, link design/plan/evidence, and name O1C-24 as next.

- [ ] **Step 5: Commit, push, and verify equality**

Commit evidence/spec closeout, push `feat/five-phase-autonomous`, fetch it, and require local HEAD equals `origin/feat/five-phase-autonomous` with a clean worktree. Preserve the worktree and do not create a PR or merge to main.
