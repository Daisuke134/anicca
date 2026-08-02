# O1C-25 YC Full Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Observe and assess current YC company facts, founder profile, founder video, demo, and progress without mutation, then produce a privacy-minimal receipt that separates full-preview completion from submit readiness.

**Architecture:** Agent-owned semantic judgments enter a closed JavaScript receipt builder together with fresh read-only observations and content-addressed source metadata. The builder validates structure, chronology, media bounds, issue/result consistency, and exact zero mutation effects only. A completed five-scope preview may truthfully block every later submit effect.

**Tech Stack:** Node.js CommonJS, `node:test`, SHA-256, JSON, Playwright Core over CDP, ffprobe, Git.

## Global constraints

- The exact application is Fall 2026 application `0b61fe42-e383-490d-b60e-04f1ad7ec5df`; it is already submitted and `In review`.
- O1C-07 remains the sole application-submit effect. O1C-25 cannot write, select, attach, save, submit an update, or submit an application.
- Browser access uses the existing CloakBrowser daily-driver at exact `http://127.0.0.1:9222`, one existing context, owned temporary pages, and no `browser.close()`.
- Semantic truth/currentness judgments are agent-owned inputs. Production code performs no keyword, regex, similarity, or score-based semantic classification.
- Public evidence contains no raw answers, personal contact data, birth date, cookies, authentication tokens, signed media URLs, or page bodies.
- `preview_complete` and `submit_ready` are independent. Every blocker requires `submit_ready:false`.
- O1C-26 may never perform a second application submission.

---

### Task 1: Closed five-scope preview receipt

**Files:**
- Create: `apps/life-manager/lib/yc-full-preview.test.js`
- Create: `apps/life-manager/lib/yc-full-preview.js`
- Modify: `apps/life-manager/package.json`

**Interface:**
- Consumes: `buildYcFullPreviewReceipt(input, { now })`, where input contains exact application identity/state, eight required content-addressed source artifacts including the O1C-07 submit receipt plus an optional dedicated demo artifact, five fresh scope observations with explicit agent verdicts/issues, and exact effect counts.
- Produces: a recursively frozen, privacy-minimal receipt with one entry per scope, a deterministic `preview_receipt_digest`, `preview_complete:true`, and a consistent `submit_ready` verdict.

- [ ] **Step 1: Write the valid closed-receipt test first**

Construct a literal preview with current company/founder/progress assessments, one valid remote/local founder-video observation, one valid dedicated demo artifact/remote observation, unique source roles, fresh timestamps, and zero effects. Assert exact five-scope order, hashes/metadata only, recursive freezing, stable digest, and absence of raw prose or sensitive keys.

- [ ] **Step 2: Verify RED for the missing module**

Run `node --test lib/yc-full-preview.test.js`. Expected: module-not-found failure.

- [ ] **Step 3: Add adversarial tests before implementation**

Reject one mutation per case: unknown/missing/duplicate or scope-incompatible source role; extra key; recomputed digest/byte mismatch/path/ref; application identity/state drift; O1C-07 application/effect mismatch; invalid or stale timestamp; observation after receipt; preview older than five minutes; company/founder/progress currentness contradiction; founder-video present without playable remote media or source-bound local SHA/bytes/H.264/AAC metadata; demo present without dedicated artifact and remote media; agent-selected blocker with `submit_ready:true`; readiness false without a blocker; non-zero write/select/attach/save/update-submit/application-submit/browser-close effect; attempted application submit count above the historical one-submit boundary; forged digest; input mutation.

- [ ] **Step 4: Implement the minimal validator/builder**

Add exact-key validation, role/scope uniqueness, SHA-256 and byte bounds, canonical timestamp/freshness/chronology checks, media bounds, explicit enum/issue/result consistency, exact zero mutation effects, stable canonical hashing, privacy-minimal projection, and recursive freezing. Do not inspect raw answer text.

- [ ] **Step 5: Verify GREEN and wire outbound regression**

Run the focused file, add it to `test:outbound`, and run `npm run test:outbound`.

### Task 2: Fresh read-only five-scope observation

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c25-yc-full-preview.json`

**Interface:**
- Consumes: fresh authenticated read-only browser observations, current repo/external source hashes, ffprobe output, and explicit agent assessment.
- Produces: one validated live preview receipt plus bounded direct-readback evidence and a closed submit gate.

- [ ] **Step 1: Bind current sources**

Hash and size the current English/Japanese READMEs, agent registry, provider manifest, Life Manager answer draft, Application Kit, and founder-video source. Record only repository-relative or logical external refs, not absolute home paths or source prose.

- [ ] **Step 2: Observe application and company facts**

Open the submitted application read-only page and record sanitized route, application state, field/section inventory and bounded value hashes/lengths. Agent-assess whether its company narrative matches current Life Manager facts. Do not persist raw answers.

- [ ] **Step 3: Observe founder profile**

Open the founder profile edit page read-only and record only profile-complete state, bounded section/field inventory, education/work row counts, public-profile link presence, and value hashes where needed. Persist no email, phone, birth date, or raw narratives. Separately agent-assess structural completeness and semantic currentness.

- [ ] **Step 4: Observe founder video and demo**

Read the founder-video and demo pages without touching file inputs. Record video count, ready state, duration, dimensions, sanitized storage origin, and a hash of the source pathname rather than the URL. Verify the local founder video with ffprobe and SHA-256. Require no demo claim when no remote product-demo media and no dedicated current artifact exist.

- [ ] **Step 5: Observe progress**

Open the progress update page read-only and record field names, value lengths/hashes, file-input count, and bounded control inventory. Agent-assess currentness against source-backed current product, user, revenue, and traction facts. Do not click `Submit update`.

- [ ] **Step 6: Build and validate evidence**

Supply the five explicit semantic verdicts and issue codes to the builder. Require five scopes observed, `preview_complete:true`, `submit_ready:false` for the observed blockers, all mutation effects zero, and no privacy scan findings.

### Task 3: Review, verification, and closeout

**Files:**
- Modify: `docs/evidence/funding/2026-08-02-o1c25-yc-full-preview.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] **Step 1: Commit implementation before review**

Commit the builder, tests, package wiring, implementation plan, and initial evidence. Record the full implementation SHA.

- [ ] **Step 2: Request independent read-only review**

Review the exact implementation range, design, plan, live observations, semantic/deterministic boundary, privacy, zero-effect boundary, and duplicate-submit protection. Convert every Critical/Important finding into a focused RED regression before fixing; repeat until zero remain.

- [ ] **Step 3: Run fresh full verification**

Run focused tests, `npm run test:outbound`, `npm run test:runtime-up`, full `npm test`, `node --check`, JSON parsing/validation, source SHA readback, a fresh bounded browser readback, `git diff --check`, and secret/privacy scans.

- [ ] **Step 4: Close O1C-25 in the canonical spec**

Check O1C-25, record 56/143 complete and 87 remaining, state the truthful five-scope verdicts and closed submit gate, link design/plan/evidence and implementation SHA, and identify the next safe action. Do not claim a demo, current remote company/progress data, update submission, confirmation mail, or reply tracking.

- [ ] **Step 5: Commit, push, and verify remote equality**

Commit evidence/spec closeout, push `feat/five-phase-autonomous`, fetch it, and require local HEAD equals `origin/feat/five-phase-autonomous` with a clean worktree. Keep the worktree for the next numbered item.
