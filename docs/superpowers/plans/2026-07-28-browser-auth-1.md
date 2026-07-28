# BROWSER-AUTH-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist an authorized Steel browser context encrypted and bound to one
Life Manager tenant, origin, and principal; restore it after a Railway process
restart; and return an honest re-authentication handoff when it is no longer
valid.

**Architecture:** Steel remains an ephemeral, Railway-private Chromium worker.
Life Manager exports Steel's closed `sessionContext`, validates it, encrypts it
with AES-256-GCM and tenant-bound AAD, and stores only ciphertext in PostgreSQL.
A later job loads only the exact `uid + origin + principal_kind` row and injects
it into a new Steel session. Provider readback decides whether to keep or
invalidate the restored session.

**Tech Stack:** Node.js 20.19+, CommonJS, Node `crypto`, PostgreSQL, existing
Railway-private Steel REST/CDP, Stagehand 3.7.1, Gemini, Node test runner.

## Global Constraints

- Design SSOT: `docs/superpowers/specs/2026-07-28-browser-auth-1-design.md`.
- Existing Mac mini loops remain loaded and running; no cutover or unload occurs
  in BROWSER-AUTH-1.
- Never use Steel `persist: true`; the OSS implementation uses one fixed
  `user-data-dir` and is not a tenant boundary.
- Raw passwords, OTPs, cookies, local/session storage, IndexedDB values,
  encryption keys, IVs, and auth tags never enter source, logs, trace, receipt,
  Telegram, or evidence.
- `LM_BROWSER_SESSION_KEY` is a Railway secret containing exactly 64 hexadecimal
  characters and is never printed.
- Auth lookup is exact on `uid + normalized HTTPS origin + principal_kind`;
  there is no fallback to another tenant, origin, or principal.
- `principal_kind` is exactly `none`, `agent_owned`, or `user_provided`.
- CAPTCHA, login rejection, 2FA, KYC, and payment remain honest handoffs.
- Every opened Steel session is released, including context load/save,
  provider-readback, Telegram, and database failures.
- BROWSER-AUTH-1 completes only with two-tenant isolation, pre/post-redeploy
  authenticated readback, expired-session handoff, production migration
  readback, secret scans, exact deployment SHA, and local Mac browser use zero.

---

### Task 1: Add tenant-bound encrypted auth storage and queue identity

**Files:**

- Create: `apps/life-manager/lib/browser-auth-session-store.js`
- Create: `apps/life-manager/lib/browser-auth-session-store.test.js`
- Create: `apps/life-manager/migrations/2026-07-28-lm-browser-auth-sessions.sql`
- Create: `apps/life-manager/lib/browser-auth-session-migration.test.js`
- Modify: `apps/life-manager/lib/browser-task-classifier.js`
- Modify: `apps/life-manager/lib/browser-task-classifier.test.js`
- Modify: `apps/life-manager/lib/browser-job-store.js`
- Modify: `apps/life-manager/lib/browser-job-store.test.js`
- Modify: `apps/life-manager/migrations/2026-07-28-lm-browser-jobs.sql`
- Modify: `apps/life-manager/lib/browser-job-migration.test.js`
- Modify: `apps/life-manager/test/browser-task-telegram-http-contract.test.js`

**Interfaces:**

- Produces:
  - `normalizeAuthOrigin(value): string`
  - `validateSessionContext(value): object`
  - `sealBrowserContext(input, keyHex): sealedRow`
  - `openBrowserContext(row, keyHex): object`
  - `readBrowserAuthSession(input, opts): Promise<authRecord|null>`
  - `upsertBrowserAuthSession(input, opts): Promise<authRecord>`
  - `invalidateBrowserAuthSession(input, opts): Promise<boolean>`
- Queue output adds `principal_kind`.

- [ ] **Step 1: Write failing crypto and isolation tests**

  Add literal contexts for two tenants at the same origin and assert:

  ```js
  const one = { cookies: [{ name: "session", value: "tenant-one", domain: "auth.example", path: "/" }] };
  const two = { cookies: [{ name: "session", value: "tenant-two", domain: "auth.example", path: "/" }] };
  const sealedOne = sealBrowserContext({
    uid: "u-one", origin: "https://auth.example", principalKind: "user_provided", context: one,
  }, "11".repeat(32));
  const sealedTwo = sealBrowserContext({
    uid: "u-two", origin: "https://auth.example", principalKind: "user_provided", context: two,
  }, "11".repeat(32));
  assert.deepEqual(openBrowserContext({ ...sealedOne, uid: "u-one", origin: "https://auth.example", principal_kind: "user_provided" }, "11".repeat(32)), one);
  assert.throws(() => openBrowserContext({ ...sealedOne, uid: "u-two", origin: "https://auth.example", principal_kind: "user_provided" }, "11".repeat(32)), /browser auth context invalid/i);
  assert.doesNotMatch(JSON.stringify(sealedOne), /tenant-one/);
  assert.notEqual(sealedOne.ciphertext, sealedTwo.ciphertext);
  ```

- [ ] **Step 2: Run Task 1 tests and verify RED**

  Run:

  ```bash
  cd apps/life-manager
  node --test lib/browser-auth-session-store.test.js lib/browser-auth-session-migration.test.js
  ```

  Expected: FAIL because the new module and migration do not exist.

- [ ] **Step 3: Implement closed validation and AES-256-GCM**

  Accept only `cookies`, `localStorage`, `sessionStorage`, and `indexedDB`;
  reject unknown top-level keys, non-object origins, values over 1 MiB, non-HTTPS
  origins, invalid principal kinds, and a key that is not 32 decoded bytes.
  Use a random 12-byte IV and the exact AAD:

  ```js
  `${uid}\n${origin}\n${principalKind}\n1`
  ```

  Return base64url ciphertext/IV/tag plus
  `context_sha256 = sha256(canonical plaintext JSON)` and `key_version = 1`.
  Map every decrypt/authentication failure to `browser auth context invalid`
  without including provider or crypto values.

- [ ] **Step 4: Implement the service-only auth table**

  Create `public.lm_browser_auth_sessions` with:

  ```sql
  uid text NOT NULL,
  origin text NOT NULL,
  principal_kind text NOT NULL CHECK (principal_kind IN ('agent_owned','user_provided')),
  ciphertext text NOT NULL,
  iv text NOT NULL,
  auth_tag text NOT NULL,
  context_sha256 text NOT NULL,
  key_version integer NOT NULL DEFAULT 1,
  state text NOT NULL CHECK (state IN ('active','invalidated')),
  expires_at timestamptz,
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  PRIMARY KEY (uid, origin, principal_kind)
  ```

  Enable RLS, revoke all from `anon` and `authenticated`, and grant no direct
  client policy. Use parameterized SQL for exact-row select/upsert/invalidate.

- [ ] **Step 5: Extend the classifier and durable queue**

  Add `principal_kind` to the strict Gemini schema:

  ```js
  principal_kind: { type: "string", enum: ["none", "agent_owned", "user_provided"] }
  ```

  Enforce `requires_login=false → principal_kind=none`; a login-dependent job
  requires `agent_owned` or `user_provided`. Persist only the enum in
  `lm_browser_jobs`; no credential text is added.

- [ ] **Step 6: Repair the existing HTTP baseline at its PostgreSQL boundary**

  The pre-existing test currently mocks a removed PostgREST insert while
  `browser-job-store` uses `pg`. Before requiring `server.js`, replace the
  cached `browser-task-intake.js` export with a wrapper that calls the real
  `handleBrowserTaskMessage` while injecting only its `enqueue` dependency.
  The injected enqueue returns the same literal inserted job and captures the
  bounded job object. Restore the original module export in `finally`. Keep the
  assertions that the production HTTP route and real classifier/intake execute,
  the webhook opens no Steel session, and the queued object stores no raw
  email/password.

- [ ] **Step 7: Run Task 1 tests until GREEN**

  Run:

  ```bash
  node --test \
    lib/browser-auth-session-store.test.js \
    lib/browser-auth-session-migration.test.js \
    lib/browser-task-classifier.test.js \
    lib/browser-job-store.test.js \
    lib/browser-job-migration.test.js \
    test/browser-task-telegram-http-contract.test.js
  ```

  Expected: all tests PASS with zero warning containing a raw fixture secret.

- [ ] **Step 8: Commit**

  ```bash
  git add -A
  git commit -m "feat(life-manager): encrypt tenant browser auth sessions"
  ```

### Task 2: Add the verified Steel context round-trip

**Files:**

- Modify: `apps/life-manager/lib/steel-cdp-client.js`
- Modify: `apps/life-manager/lib/steel-cdp-client.test.js`
- Modify: `apps/life-manager/lib/stagehand-steel-driver.js`
- Modify: `apps/life-manager/lib/stagehand-steel-driver.test.js`

**Interfaces:**

- Consumes Task 1 auth-store functions.
- Produces:
  - `steelClient.getSessionContext(sessionId): Promise<object>`
  - `driver.openSession({ uid, goal, requiresLogin, principalKind }): Promise<session>`
  - `driver.releaseSession(sessionId, { providerReceipt }): Promise<releaseReceipt>`

- [ ] **Step 1: Write failing Steel context tests**

  Add a test that returns a complete real-shaped response:

  ```js
  const context = {
    cookies: [{ name: "sid", value: "opaque", domain: "auth.example", path: "/", secure: true, httpOnly: true }],
    localStorage: { "https://auth.example": { theme: "dark" } },
    sessionStorage: {},
    indexedDB: {},
  };
  assert.deepEqual(await client.getSessionContext("abc"), context);
  assert.equal(fetchImpl.calls[0].url, "http://steel-browser.railway.internal:8080/v1/sessions/abc/context");
  assert.equal(fetchImpl.calls[0].method, "GET");
  ```

  Add rejection tests for an unknown key, payload over 1 MiB, missing session
  id, and a non-2xx Steel response.

- [ ] **Step 2: Write failing driver restore/save tests**

  The same public origin with `uid=u-one` must inject only context one; `u-two`
  injects only context two. Assert the exact `createRawSession` body and assert
  that no cookie value occurs in action output, trace metadata, or release
  receipt. A discovery goal without an explicit URL must not call auth lookup.

- [ ] **Step 3: Run Task 2 tests and verify RED**

  ```bash
  node --test lib/steel-cdp-client.test.js lib/stagehand-steel-driver.test.js
  ```

  Expected: FAIL because `getSessionContext` and auth-aware driver arguments do
  not exist.

- [ ] **Step 4: Implement the Steel context endpoint**

  Use:

  ```http
  GET /v1/sessions/:sessionId/context
  ```

  Validate through the Task 1 closed context validator. `createRawSession`
  continues to call `POST /v1/sessions`, now with `sessionContext` only when an
  exact auth row was restored. Do not use `persist` or `userDataDir`.

- [ ] **Step 5: Implement exact auth restore and save**

  `openSession` extracts the explicit public HTTPS origin using the existing
  URL guard. When `requiresLogin=true`, call `readBrowserAuthSession` with the
  exact `uid/origin/principalKind`, pass its context into Steel, and retain only
  non-secret metadata in the driver's process-local session map.

  `releaseSession` obtains the context before Steel release. When provider
  readback says `handoff_reason=login`, invalidate the exact row. Otherwise
  upsert the exported context. If export/save fails, preserve the prior row,
  classify `auth_context_saved=false`, and still release Steel.

- [ ] **Step 6: Run Task 2 tests until GREEN**

  ```bash
  node --test lib/steel-cdp-client.test.js lib/stagehand-steel-driver.test.js
  ```

- [ ] **Step 7: Commit**

  ```bash
  git add -A
  git commit -m "feat(life-manager): restore Steel browser contexts per tenant"
  ```

### Task 3: Wire auth lifecycle into the durable browser job

**Files:**

- Modify: `apps/life-manager/lib/generic-browser-task.js`
- Modify: `apps/life-manager/lib/generic-browser-task.test.js`
- Modify: `apps/life-manager/lib/browser-job-runtime.js`
- Modify: `apps/life-manager/lib/browser-job-runtime.test.js`
- Modify: `apps/life-manager/lib/browser-job-store.js`
- Modify: `apps/life-manager/lib/browser-job-store.test.js`
- Modify: `apps/life-manager/migrations/2026-07-28-lm-browser-jobs.sql`
- Modify: `apps/life-manager/lib/browser-job-migration.test.js`

**Interfaces:**

- Consumes Task 2 driver lifecycle.
- Produces bounded trace stages `auth_context_loaded`,
  `auth_context_saved`, and `auth_context_invalidated`.

- [ ] **Step 1: Write failing runtime lifecycle tests**

  Assert that `openSession` receives:

  ```js
  {
    uid: "u-1",
    goal: "Open https://auth.example/account",
    requiresLogin: true,
    principalKind: "user_provided",
  }
  ```

  Assert that `releaseSession` receives the bounded provider receipt, and that
  trace metadata contains only origin/principal kind/booleans/hash/version. Use
  raw fixture strings and assert none occur in `JSON.stringify(result)` or the
  collected traces.

- [ ] **Step 2: Add expired-session and save-failure tests**

  A provider `handoffRequired=true, handoffReason=login` must finish
  `handoff_required`, append `auth_context_invalidated`, release Steel, and send
  an honest Telegram message. Context export/save failure must append
  `auth_context_saved=false`, preserve provider outcome, and release Steel.

- [ ] **Step 3: Run Task 3 tests and verify RED**

  ```bash
  node --test \
    lib/generic-browser-task.test.js \
    lib/browser-job-runtime.test.js \
    lib/browser-job-store.test.js \
    lib/browser-job-migration.test.js
  ```

- [ ] **Step 4: Implement bounded auth trace and lifecycle**

  Pass the job identity to `openSession`. After provider readback, pass only its
  closed receipt to `releaseSession`. Extend the trace allowlist and SQL RPC
  allowlist with the three auth stages. Add only:

  ```js
  {
    origin,
    principal_kind,
    loaded,
    saved,
    invalidated,
    context_sha256,
    key_version,
  }
  ```

  after omitting null keys. Never append a nested context or caught raw error.

- [ ] **Step 5: Run Task 3 tests until GREEN**

  Run the Task 3 command, then the entire focused browser suite:

  ```bash
  node --test \
    lib/browser-auth-session-store.test.js \
    lib/browser-auth-session-migration.test.js \
    lib/browser-task-classifier.test.js \
    lib/browser-task-intake.test.js \
    lib/browser-job-store.test.js \
    lib/browser-job-migration.test.js \
    lib/steel-cdp-client.test.js \
    lib/stagehand-steel-driver.test.js \
    lib/generic-browser-task.test.js \
    lib/browser-job-runtime.test.js \
    test/browser-task-telegram-http-contract.test.js
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "feat(life-manager): persist browser auth lifecycle receipts"
  ```

### Task 4: Build a secret-free production verification harness

**Files:**

- Create: `apps/life-manager/scripts/browser-auth-production-e2e.js`
- Create: `apps/life-manager/scripts/browser-auth-production-e2e.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**

- CLI modes:
  - `seed-two-tenant-contexts`
  - `verify-two-tenant-contexts`
  - `verify-expired-handoff`
- Output is one bounded JSON object containing hashes and IDs only.

- [ ] **Step 1: Write failing CLI contract tests**

  Assert unknown modes exit nonzero; required env absence fails without printing
  values; two tenants use distinct opaque markers; output includes only:

  ```js
  {
    mode,
    tenant_count,
    origin,
    context_hashes,
    job_ids,
    steel_session_ids,
    telegram_evidence_ids,
    released,
  }
  ```

  Assert raw marker, cookie, key, email, Telegram token, database URL, and
  provider body never occur in stdout/stderr.

- [ ] **Step 2: Run the CLI test and verify RED**

  ```bash
  node --test scripts/browser-auth-production-e2e.test.js
  ```

- [ ] **Step 3: Implement the harness over production modules**

  Use the real auth store, Steel client, durable browser queue, and Telegram
  path. Do not directly claim success from a fixture. Each mode must verify
  provider readback and Steel release before emitting its secret-free summary.

- [ ] **Step 4: Run the CLI tests until GREEN**

  ```bash
  node --test scripts/browser-auth-production-e2e.test.js
  ```

- [ ] **Step 5: Run full local verification**

  ```bash
  npm test
  npm run eval
  ```

  Record exact pass/fail counts. Pre-existing failures are not waived: either
  repair their real root cause in scope or leave BROWSER-AUTH-1 incomplete.

- [ ] **Step 6: Commit**

  ```bash
  git add -A
  git commit -m "test(life-manager): verify browser auth continuity"
  ```

### Task 5: Apply migration, deploy, and prove restart continuity

**Files:**

- Create: `docs/evidence/browser/2026-07-28-browser-auth-1.md`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

**Interfaces:**

- Evidence document contains no raw authentication material.
- SSOT advances to `BROWSER-MATRIX-1` only after every verification contract
  item is present.

- [ ] **Step 1: Configure the production key without exposing it**

  Generate 32 random bytes locally, set `LM_BROWSER_SESSION_KEY` as a masked
  Railway variable, delete the temporary file, and verify only
  `configured=true` plus decoded length `32`. Never print the value.

- [ ] **Step 2: Apply and independently read back the migration**

  Apply both auth-session and browser-job additive migrations to production
  PostgreSQL. Read back table columns, primary key, checks, RLS, grants, and
  trace-stage function definition. Store only schema names and boolean results.

- [ ] **Step 3: Push, PR, merge, and verify exact deployment**

  Run fresh focused and full tests, push the feature branch, create the PR, wait
  for required checks, merge, and verify Railway `life-call` reports the exact
  merge SHA and healthy browser loop. Do not stop Mac loops.

- [ ] **Step 4: Prove two-tenant non-mixing**

  Use one public HTTPS origin and two synthetic production tenant IDs with
  different random opaque session markers. Save through real Steel context
  export, restore through new Steel sessions, and verify each tenant reads only
  its own marker. Verify wrong tenant/origin/principal reads none. Delete or
  invalidate the synthetic rows after evidence capture.

- [ ] **Step 5: Prove authenticated provider continuity before restart**

  Establish an authorized agent-owned session using the runtime-only
  `LM_AGENT_BROWSER_EMAIL` identity without persisting its email, password, or
  OTP. Send a real Telegram browser request through production, capture provider-authored
  authenticated readback, Telegram PNG/message ID, job ID, Steel session ID,
  context hash, and release receipt.

- [ ] **Step 6: Restart and prove continuity from a new process/session**

  Redeploy the same merge SHA or restart `life-call`, verify the process
  changed, then send the same auth-dependent request. Require a new Steel
  session ID, `auth_context_loaded=true`, the same provider account/session
  readback, Telegram evidence, and `steel_released=true`.

- [ ] **Step 7: Prove expired-session handoff**

  Invalidate the exact auth row or use a provider-rejected context, run the
  auth-dependent job, and require:

  ```text
  status=handoff_required
  handoff_reason=login
  auth_context_invalidated=true
  steel_released=true
  ```

  Confirm no action success claim and no duplicate side effect.

- [ ] **Step 8: Scan for secrets and local-browser use**

  Scan repository diff, production logs, job trace, Telegram receipt, and
  evidence document for the seeded raw markers and runtime secrets; require zero
  matches. Verify no local Mac Chrome/CloakBrowser/Playwright/CDP navigation or
  profile mutation occurred during all production runs.

- [ ] **Step 9: Record evidence and advance the SSOT**

  Write exact job/deployment/session/message IDs and secret-free hashes to the
  evidence file. Mark BROWSER-AUTH-1 done and BROWSER-MATRIX-1 current only when
  Steps 1–8 all pass.

- [ ] **Step 10: Commit and push the evidence/SSOT**

  ```bash
  git add -A
  git commit -m "docs(life-manager): prove tenant-safe cloud browser auth"
  git push
  ```
