# BROWSER-MATRIX-1 Implementation Plan

> Live status、execution ownership、credential裁定、done条件のSSOTは
> `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4.6a。
> 本planの旧「harnessが対象jobをdirect claim/executeする」手順は無効であり、verifierはenqueue-only +
> terminal poll、execution ownerはresident production browser loopだけとする。

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

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write failing receipt tests**

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

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/life-manager
node --test lib/stagehand-steel-driver.test.js
```

Expected: inquiry/application success phrases are not confirmed.

- [x] **Step 3: Implement a category-neutral terminal vocabulary**

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

- [x] **Step 4: Verify driver plus browser-auth regression**

Run:

```bash
cd apps/life-manager
node --test lib/stagehand-steel-driver.test.js scripts/browser-auth-luma-bootstrap.test.js scripts/browser-auth-production-e2e.test.js
```

Expected: all tests pass and authenticated-continuity behavior is unchanged.

- [x] **Step 5: Refresh exact OSS manifest hashes and verify**

Run `shasum -a 256` for the modified driver and test, update their two entries
in `docs/manifests/oss-merge-1-sources.json`, then run:

```bash
node scripts/verify-oss-self-contained.mjs
npm run test:oss
```

- [x] **Step 6: Commit**

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

- [x] **Step 1: Write failing harness tests**

Assert exact three-category coverage, distinct public origins, completed durable
rows, nonempty provider confirmation, Telegram evidence ID, receipt SHA-256,
and `steel_released=true`. Assert that missing URL, duplicate origin, non-HTTPS
URL, `possibly_completed`, or a raw email/credential field fails closed.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/life-manager
node --test scripts/browser-matrix-production-e2e.test.js
```

Expected: module not found.

- [x] **Step 3: Implement the first harness checkpoint（historical / superseded）**

The merged checkpoint followed `browser-auth-production-e2e.js`: it enqueues one
exact job by ID, claims that job directly, executes through
`runNextBrowserJob`, rereads the terminal durable row, hashes the bounded
provider receipt, and returns IDs/hashes only. This proves the generic cloud
executor contract but does not prove resident-loop ownership, so it MUST NOT be
used for Task 4 live acceptance.

- [x] **Step 4: Run harness tests and the browser suite**

Run:

```bash
cd apps/life-manager
node --test scripts/browser-matrix-production-e2e.test.js
npm run test:browser-auth
```

- [x] **Step 5: Commit**

```bash
git add apps/life-manager/scripts/browser-matrix-production-e2e.js apps/life-manager/scripts/browser-matrix-production-e2e.test.js apps/life-manager/package.json
git commit -m "test(browser): add durable production action matrix"
```

### Task 3a: Correct verification ownership before live actions

- [x] **Step 1: Write RED ownership tests**

Require production deps to expose enqueue/read/poll boundaries only. Assert no
`claimBrowserJobById`, `runNextBrowserJob`, driver, or executor call is possible
from the verifier.

- [x] **Step 2: Replace direct execution with bounded terminal polling**

After enqueue, poll durable rows until all three are terminal or the bounded
deadline expires. The already-running production browser loop is the only
component allowed to claim and execute them.

- [x] **Step 3: Verify and deploy**

Run the focused browser suite, full app suite, OSS boundary, required security
CI, merge, and verify the exact Railway deployment SHA and
`browser jobs ON (Railway private Steel)` boot log before Task 4.

Evidence (2026-07-30): PR #1361 merged as canonical main
`569cf748e23d3a1de880791a3f6ad79ed621f0a5`. RED first (8 fail/1 pass), then
harness tests 9/9, `test:browser-auth` 47/47, full `npm test` chain exit 0,
OSS boundary PASS, security CI 7/7. Railway `life-call` deployment
`7ea230f6-f8f4-41f6-8310-b6ae324d1d52` `SUCCESS` at the exact merge SHA with
boot log `[life-call] browser jobs ON (Railway private Steel)`. The verifier
module no longer references `browser-job-runtime`, `claimBrowserJobById`, or
any executor; deps are `durableQueue.enqueue`/`durableQueue.read` plus an
injectable clock, with poll bounds
`BROWSER_MATRIX_POLL_TIMEOUT_MS`/`BROWSER_MATRIX_POLL_INTERVAL_MS`.

### Task 4: Execute the three real provider actions in production

**Files:**
- Create: `docs/evidence/browser/2026-07-30-browser-matrix-1.md`

**Interfaces:**
- Consumes: three controlled responder URLs (booking / inquiry / application)
  on distinct public origins, established per spec §0.4.6a As-Is/To-Be without
  pre-created admin UI logins; final deployed harness
- Produces: three provider-side stored records plus queue, Steel, Telegram, and
  release evidence

- [ ] **Step 1: Establish controlled responder URLs without pre-created admin logins**

SUPERSEDED WORDING (2026-07-30): the earlier "create Cal.com + Tally + Google
Forms accounts first" instruction is void — spec §0.4.6a As-Is/To-Be already
rejected "admin UI loginを3 provider全てで先に作る案" and requires readback via
"confirmation email、webhook、API、owner response tableのうちsecretを出さず独立
照合できるsurface". Follow the spec:

1. Prefer surfaces reachable from credentials/context the tenant already has
   (e.g. the connected Google account) over any new provider account.
2. Any fixture that does require creation is produced by the resident cloud
   loop itself (enqueued job with tenant-bound auth context) or by a
   server-side API call — never by a local/Mac browser (§0.4.6a MUST 6:
   local/Mac browser side effect 0).
3. Actions stay zero-cost, cancellable, non-binding; no nuisance to
   uncontrolled third parties; three distinct public HTTPS origins.
4. Do not store account credentials, URL tokens, or response-edit tokens in
   Git; controlled URLs live only in runtime secrets.

- [ ] **Step 2: Deploy exact canonical code**

Push the implementation PR, require all security checks, merge, and verify
Railway `life-call` reports `SUCCESS` at the exact merge SHA before running.

- [ ] **Step 3: Enqueue one durable production job per provider**

Invoke the harness inside the deployed Railway `life-call` container. The
harness MUST enqueue and bounded-poll only. It MUST NOT call
`claimBrowserJobById`, `runNextBrowserJob`, a driver, or an executor. The
already-running production browser loop must claim each job and use
Railway-private Steel, not a local browser.

- [ ] **Step 4: Independently read provider-side records**

Verify one new booking in Cal.com, one new Tally response, and one new Google
Forms response. Compare bounded response IDs or SHA-256 digests to the durable
job receipt; do not print form contents or identity data.

- [ ] **Step 5: Verify cleanup and leak boundaries**

Assert three distinct Steel IDs, `released=3/3`, no open controlled sessions,
resident-loop claim 3/3, verifier direct execution 0, and zero
OTP/email/cookie/authorization/raw-context patterns in bounded production logs.

- [ ] **Step 6: Write evidence and commit**

Record exact merge SHA, Railway deployment/instance, three job IDs, three Steel
IDs, three Telegram evidence IDs, provider-origin/category, receipt hashes,
provider-side readback booleans, and release booleans.

### Task 5: Advance the SSOT only after all three live legs pass

**Files:**
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Modify: `docs/evidence/browser/2026-07-30-browser-matrix-1.md`

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
