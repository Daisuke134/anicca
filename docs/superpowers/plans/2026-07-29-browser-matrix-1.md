# BROWSER-MATRIX-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that the canonical Life Manager production planner/executor can complete booking, inquiry/message, and application actions on three unrelated live providers without site adapters or a Mac browser.

**Architecture:** Keep one generic Stagehand/Steel executor and pass provider URLs and goals only at runtime. Generalize the classifier's low-risk communication policy and the independent provider-result vocabulary, then drive three durable production jobs through the existing Supabase queue, Railway-private Steel, Telegram receipt, and explicit Steel release. Use agent-owned controlled provider assets so real side effects are observable without sending nuisance requests to unrelated humans.

**Tech Stack:** Node.js, `node:test`, Stagehand v3, Railway-private Steel/CDP, Supabase durable jobs, Telegram Bot API.

## Global Constraints

- Existing loaded Mac loops remain loaded; no Mac Chrome, Cloak, Playwright, or local CDP performs a matrix action.
- No website hostname or selector is added to production code.
- Every action is explicit, zero-cost, non-KYC, and carries no payment, contract, legal attestation, or invented personal fact.
- A model narration is not evidence; completion requires independent provider-authored readback and saved-provider-side receipt.
- Every opened Steel session is released on success, handoff, timeout, and failure.
- Email addresses, response bodies, browser contexts, cookies, OTPs, and credentials stay out of repo, logs, trace, and Telegram.
- One action per controlled provider asset: Cal.com booking, Tally inquiry, Google Forms application.

---

### Task 1: Accept explicit non-binding communication without weakening money/KYC gates

**Files:**
- Modify: `apps/life-manager/lib/browser-task-classifier.js`
- Test: `apps/life-manager/lib/browser-task-classifier.test.js`

**Interfaces:**
- Consumes: `classifyBrowserTask(text, deps)`
- Produces: a validated decision with `binding_commitment: boolean` and canonical `action_kind`

- [x] **Step 1: Write the failing policy tests**

Add decisions for `inquiry` and `application` with `reversible=false`,
`binding_commitment=false`; assert acceptance. Add matching
`binding_commitment=true` cases and assert `binding_or_legal_commitment`.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/life-manager
node --test lib/browser-task-classifier.test.js
```

Expected: schema rejection because `binding_commitment` is not yet part of the
decision contract.

- [x] **Step 3: Implement the bounded policy**

Add `binding_commitment` to `DECISION_KEYS`, the Gemini response schema, prompt,
and validator. Restrict `action_kind` to:

```js
["registration", "booking", "inquiry", "application", "authenticated_readback", "other"]
```

Update rejection order:

```js
if (!decision.zero_cost) return "financial_or_paid_action";
if (decision.requires_kyc) return "kyc_or_identity_gate";
if (decision.binding_commitment) return "binding_or_legal_commitment";
if (!decision.reversible && !["inquiry", "application"].includes(decision.action_kind)) {
  return "irreversible_action";
}
```

The prompt must set `binding_commitment=true` for contracts, paid terms, legal
attestations, regulated submissions, or claims not present in supplied context.

- [x] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: all classifier tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/life-manager/lib/browser-task-classifier.js apps/life-manager/lib/browser-task-classifier.test.js
git commit -m "feat(browser): classify non-binding communication actions"
```

### Task 2: Generalize independent provider completion readback

**Files:**
- Modify: `apps/life-manager/lib/stagehand-steel-driver.js`
- Test: `apps/life-manager/lib/stagehand-steel-driver.test.js`
- Modify: `docs/manifests/oss-merge-1-sources.json`

**Interfaces:**
- Consumes: Stagehand `receiptSchema` extraction after exactly one action
- Produces: `confirmed=true` only for provider-authored terminal booking,
  inquiry/message, or application receipt with no active action/auth form

- [ ] **Step 1: Write failing receipt tests**

Add table-driven cases for:

```js
[
  ["Booking confirmed", "booking_confirmed"],
  ["Message sent", "message_sent"],
  ["We received your inquiry", "inquiry_received"],
  ["Application submitted", "application_submitted"],
  ["Submission received", "submission_received"],
]
```

For each, assert `confirmed=true`. Add negated/pending variants (`not submitted`,
`message failed`, active form, login form) and assert `confirmed=false`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/life-manager
node --test lib/stagehand-steel-driver.test.js
```

Expected: inquiry/application success phrases are not confirmed.

- [ ] **Step 3: Implement a category-neutral terminal vocabulary**

Extend `strongCompletion` only with explicit terminal phrases:

```js
/\b(?:booking|appointment|reservation)\s+confirmed\b/i
/\b(?:message|inquiry|request)\s+(?:sent|received)\b/i
/\b(?:application|submission)\s+(?:submitted|received)\b/i
/\bthank you for (?:contacting|your (?:inquiry|application|submission))\b/i
```

Keep `hardFailure`, pending, blocking verification, active registration form,
active authentication form, KYC, payment, and challenge checks dominant.
Update the Stagehand readback prompt to copy a short exact provider phrase and
never infer success from the action narration.

- [ ] **Step 4: Verify driver plus browser-auth regression**

Run:

```bash
cd apps/life-manager
node --test lib/stagehand-steel-driver.test.js scripts/browser-auth-luma-bootstrap.test.js scripts/browser-auth-production-e2e.test.js
```

Expected: all tests pass and authenticated-continuity behavior is unchanged.

- [ ] **Step 5: Refresh exact OSS manifest hashes and verify**

Run `shasum -a 256` for the modified driver and test, update their two entries
in `docs/manifests/oss-merge-1-sources.json`, then run:

```bash
node scripts/verify-oss-self-contained.mjs
npm run test:oss
```

- [ ] **Step 6: Commit**

```bash
git add apps/life-manager/lib/stagehand-steel-driver.js apps/life-manager/lib/stagehand-steel-driver.test.js docs/manifests/oss-merge-1-sources.json
git commit -m "feat(browser): verify booking message and application receipts"
```

### Task 3: Add a secret-free durable production matrix harness

**Files:**
- Create: `apps/life-manager/scripts/browser-matrix-production-e2e.js`
- Create: `apps/life-manager/scripts/browser-matrix-production-e2e.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: three runtime-only `BROWSER_MATRIX_*_URL` values, controlled goals,
  tenant UID, Telegram chat ID, existing queue/store/runtime
- Produces:

```js
{
  categories: ["booking", "inquiry", "application"],
  job_ids: ["…", "…", "…"],
  provider_origins: ["https://cal.com", "https://tally.so", "https://docs.google.com"],
  steel_session_ids: ["…", "…", "…"],
  telegram_evidence_ids: ["…", "…", "…"],
  provider_receipt_hashes: ["sha256", "sha256", "sha256"],
  released: true
}
```

- [ ] **Step 1: Write failing harness tests**

Assert exact three-category coverage, distinct public origins, completed durable
rows, nonempty provider confirmation, Telegram evidence ID, receipt SHA-256,
and `steel_released=true`. Assert that missing URL, duplicate origin, non-HTTPS
URL, `possibly_completed`, or a raw email/credential field fails closed.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/life-manager
node --test scripts/browser-matrix-production-e2e.test.js
```

Expected: module not found.

- [ ] **Step 3: Implement the harness**

Follow `browser-auth-production-e2e.js`: enqueue one exact job by ID, claim that
job only, execute through `runNextBrowserJob`, reread the terminal durable row,
hash the bounded provider receipt, and return IDs/hashes only. Runtime goals use
agent-owned name/email role labels and contain no secret value.

- [ ] **Step 4: Run harness tests and the browser suite**

Run:

```bash
cd apps/life-manager
node --test scripts/browser-matrix-production-e2e.test.js
npm run test:browser-auth
```

- [ ] **Step 5: Commit**

```bash
git add apps/life-manager/scripts/browser-matrix-production-e2e.js apps/life-manager/scripts/browser-matrix-production-e2e.test.js apps/life-manager/package.json
git commit -m "test(browser): add durable production action matrix"
```

### Task 4: Execute the three real provider actions in production

**Files:**
- Create: `docs/evidence/browser/2026-07-29-browser-matrix-1.md`

**Interfaces:**
- Consumes: agent-owned controlled Cal.com booking page, Tally inquiry form,
  and Google Forms application form; final deployed harness
- Produces: three provider-side stored records plus queue, Steel, Telegram, and
  release evidence

- [ ] **Step 1: Provision controlled provider assets**

Use the agent-owned identity to create:

1. a zero-cost cancellable Cal.com event slot,
2. a Tally inquiry form whose owner response table is readable,
3. a Google Forms application with no legal attestation or sensitive fields.

Do not store account credentials or public response-edit tokens in Git.

- [ ] **Step 2: Deploy exact canonical code**

Push the implementation PR, require all security checks, merge, and verify
Railway `life-call` reports `SUCCESS` at the exact merge SHA before running.

- [ ] **Step 3: Run one durable production job per provider**

Invoke the harness inside the deployed Railway `life-call` container. Each job
must use Railway-private Steel, not a local browser.

- [ ] **Step 4: Independently read provider-side records**

Verify one new booking in Cal.com, one new Tally response, and one new Google
Forms response. Compare bounded response IDs or SHA-256 digests to the durable
job receipt; do not print form contents or identity data.

- [ ] **Step 5: Verify cleanup and leak boundaries**

Assert three distinct Steel IDs, `released=3/3`, no open controlled sessions,
and zero OTP/email/cookie/authorization/raw-context patterns in bounded
production logs.

- [ ] **Step 6: Write evidence and commit**

Record exact merge SHA, Railway deployment/instance, three job IDs, three Steel
IDs, three Telegram evidence IDs, provider-origin/category, receipt hashes,
provider-side readback booleans, and release booleans.

### Task 5: Advance the SSOT only after all three live legs pass

**Files:**
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Modify: `docs/evidence/browser/2026-07-29-browser-matrix-1.md`

**Interfaces:**
- Consumes: Task 4 exact evidence
- Produces: `BROWSER-MATRIX-1=done`; `BROWSER-RECOVERY-1=current`

- [ ] **Step 1: Update every live cursor occurrence**

Mark matrix done only with all three real provider-side receipts. Replace every
live `BROWSER-MATRIX-1 current/pending` statement with the exact evidence link
and set `BROWSER-RECOVERY-1` current.

- [ ] **Step 2: Scan contradictions and secrets**

Run:

```bash
rg -n "BROWSER-MATRIX-1.*(pending|current|in progress)" docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
git diff --check
node scripts/verify-oss-self-contained.mjs
```

Expected: no stale live status, clean diff, OSS PASS.

- [ ] **Step 3: Push, merge, and verify canonical main**

Require PII, gitleaks, TruffleHog, OSS boundary, Python, and Shell checks to pass.
Merge and reread the exact canonical main SHA. Keep the Mac loops untouched.
