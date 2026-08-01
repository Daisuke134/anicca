# O1C-22 YC Legacy Continuation Readback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove from a fresh authenticated YC Home read that the legacy Summer application is a separate historical application and is not offered by current Home as the Fall application identity, without any browser write.

**Architecture:** A pure CommonJS receipt builder accepts two current page observations and an agent-owned assessment. It validates exact YC URLs, UUID/link identity, source chronology, excerpt containment, body digests, zero effects, and owned-tab cleanup. A live one-owned-tab browser read supplies the observations; only the privacy-minimal receipt is committed.

**Tech Stack:** Node.js CommonJS, `node:test`, SHA-256, Playwright Core over the existing CloakBrowser daily-driver CDP endpoint.

---

### Task 1: Define the closed continuation receipt contract

**Files:**
- Create: `apps/life-manager/lib/yc-legacy-continuation.js`
- Create: `apps/life-manager/lib/yc-legacy-continuation.test.js`
- Modify: `apps/life-manager/package.json`

- [ ] **Step 1: Write the failing valid-observation test**

Create a literal fixture with distinct legacy/current UUIDs, exact Home and legacy preview URLs, page bodies containing exact Fall/status/Summer excerpts, Home linking only the current UUID, legacy preview linking only the legacy UUID, zero write/submit operations, and one owned tab created/closed. Assert `decision=separate_historical_application`, `same_application=false`, no raw body/excerpt/rationale in output, and a 64-character receipt digest.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `node --test lib/yc-legacy-continuation.test.js`

Expected: FAIL because `yc-legacy-continuation.js` does not exist.

- [ ] **Step 3: Write adversarial tests before production code**

Add literal cases that independently reject: identical IDs, legacy ID linked on Home, missing current ID, wrong origin/path, inaccessible legacy preview, missing excerpt, reversed/stale timestamps, source digest substitution, unknown decision, observed continuation control, any write/submit operation, unclosed owned tab, unexpected nested fields, and raw secret-shaped fields.

- [ ] **Step 4: Implement the minimal pure receipt builder**

Export `buildYcLegacyContinuationReceipt(input)`. Validate exact input keys and nested keys; validate HTTPS YC origin/path and UUIDs; recompute body SHA-256; require exact excerpt containment; require Home current-ID inclusion and legacy-ID exclusion; require legacy preview legacy-ID inclusion; require distinct IDs; require observations within fifteen minutes and before `recordedAt`; require `created_owned_pages=1`, `closed_owned_pages=1`, `browser_close_operations=0`, `write_operations=0`, and `submit_operations=0`. Emit only hashes, lengths, IDs, labels, counts, decision, and a stable receipt digest.

- [ ] **Step 5: Run focused tests GREEN**

Run: `node --test lib/yc-legacy-continuation.test.js`

Expected: all receipt tests pass with zero failures.

- [ ] **Step 6: Add the focused file to `test:outbound` and run the suite**

Run: `npm run test:outbound`

Expected: all outbound tests pass.

### Task 2: Produce a fresh live receipt without external effects

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c22-yc-legacy-continuation.json`

- [ ] **Step 1: Open exactly one owned page in the existing daily-driver**

Connect Playwright Core over CDP to `http://127.0.0.1:9222`, require one shared context, record existing pages, create one page, and close that page in `finally`. Do not call `browser.close()`.

- [ ] **Step 2: Read current Home and legacy preview by GET only**

Read `https://apply.ycombinator.com/home`, then `https://apply.ycombinator.com/apps/99b966b0-7e90-4856-ab0d-93651488a4ea`. Capture bodies in memory, exact application-link UUIDs, final URL/path, observation times, and zero-effect counts. Do not click, fill, upload, save, create, update, or submit.

- [ ] **Step 3: Make the semantic assessment from the full surfaces**

Select exact current batch/status and legacy batch excerpts from the in-memory bodies. Record `separate_historical_application` only when Home links the submitted Fall UUID but not the legacy UUID, while the direct legacy preview remains labeled Summer 2026. Keep the claim limited to the current Home path.

- [ ] **Step 4: Build and persist the privacy-minimal receipt**

Pass the live observation and assessment to `buildYcLegacyContinuationReceipt`. Persist the returned receipt plus test/review metadata only. Never persist raw bodies, cookies, headers, WebSocket URLs, founder answers, or raw excerpts.

### Task 3: Review, verify, and close the canonical item

**Files:**
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] **Step 1: Request independent read-only review**

Review the builder, adversarial tests, live receipt, no-effect boundary, and O1C-23 through O1C-26 scope separation. Fix every Critical/Important finding through RED→GREEN regression tests.

- [ ] **Step 2: Run fresh verification**

Run focused tests, `npm run test:outbound`, `npm run test:runtime-up`, full `npm test`, `node --check`, JSON validation, `git diff --check`, and verify the daily-driver has no owned YC tab left behind.

- [ ] **Step 3: Commit implementation and record its SHA**

Commit the module, tests, package wiring, and plan. Record that commit in the evidence and canonical spec.

- [ ] **Step 4: Close O1C-22 in the canonical spec**

Check O1C-22, record 53/143 complete and 90 remaining, state the bounded conclusion, link design/plan/evidence, and name O1C-23 as next.

- [ ] **Step 5: Commit, push, and verify equality**

Commit evidence/spec closeout, push `feat/five-phase-autonomous`, fetch it, and require local HEAD equals `origin/feat/five-phase-autonomous` with a clean worktree.
