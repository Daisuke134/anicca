# BROWSER-GEN-1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A real Telegram natural-language request becomes one durable cloud job that discovers and selects an unregistered suitable website, performs one explicitly delegated reversible action in Railway-private Steel Chromium, independently reads the provider result back, sends a trace/receipt to Telegram, and releases the Steel session without touching a Mac browser.

**Architecture:** Keep self-hosted Steel as the browser infrastructure and add Stagehand v3 as the natural-language browser-agent layer inside the existing Node Railway service. The Telegram webhook classifies only explicit delegated browser requests, durably enqueues them in Supabase, and acknowledges quickly. A single-claim cloud worker runs each job against a newly created private Steel session, records append-only trace stages, independently extracts provider readback, sends the terminal Telegram receipt, and always releases the session. Site choice is made at runtime through browser search; no site adapter or allowlist supplies the answer.

**Tech Stack:** Node.js 20+, CommonJS, `@browserbasehq/stagehand` v3, `zod`, existing Steel REST/CDP service, Gemini API, Supabase PostgREST/PostgreSQL, Telegram Bot API, Node test runner.

## Global Constraints

- Existing Mac mini launchd loops stay loaded and running. This work adds a cloud browser worker only.
- No Browserbase account, Browserbase cloud session, local Chrome, localhost CDP, dry run, fake provider receipt, or hard-coded target site may satisfy the production E2E.
- Only explicit, reversible, zero-cost delegated actions enter the autonomous path. Financial outflow, account deletion, legal acceptance, KYC, CAPTCHA, OAuth, 2FA, and ambiguous commitments stop with an honest handoff.
- Credentials and page text containing personal data never enter source, logs, Telegram, or the trace ledger. Provider readback is reduced to a bounded receipt schema.
- A submit/action is at-most-once. After an uncertain side effect the job becomes `possibly_completed`; it is never blindly retried.
- Every created Steel session is released in `finally`, including classifier, agent, extraction, Telegram, timeout, and persistence failures.
- The production proof must include: real Telegram update id, prompt hash, model decision, runtime-selected URL and rationale, Steel session id, provider-side readback, Telegram message id, release receipt, Railway deployment SHA, and a local-browser side-effect count of zero.

## Evidence for the chosen stack

| Source | URL | Core evidence | Decision |
|---|---|---|---|
| Steel README | https://github.com/steel-dev/steel-browser | “Full Browser Control” through CDP and session/state management; self-host deployment is supported | Keep Steel as the cloud Chrome/session layer |
| Stagehand README | https://github.com/browserbase/stagehand | “control web browsers with natural language and code” and use AI on unfamiliar pages while retaining deterministic code | Use Stagehand as the planner/action layer |
| Steel Stagehand TypeScript cookbook | https://github.com/steel-dev/steel-cookbook/tree/main/examples/stagehand-ts | “Stagehand handles the reasoning and Steel handles the browser”; `env: "LOCAL"` accepts the Steel CDP URL | Use the officially demonstrated Steel + Stagehand composition without Browserbase cloud |
| Browser Use README | https://github.com/browser-use/browser-use | Strong general browser agent, but the embeddable library is Python and its own README recommends hosted cloud browsers for leading stealth/scaling | Do not add a second Python runtime or hosted browser dependency for this Node/Railway milestone |
| Browserless README | https://github.com/browserless/browserless | Strong self-hosted browser pool with Playwright/Puppeteer connections, but the OSS core is browser infrastructure rather than the missing natural-language task planner | Do not replace already-proven Steel transport during BROWSER-GEN-1 |

---

### Task 1: Fix the behavioral contracts with failing tests

**Files:**

- Create: `apps/life-manager/lib/browser-task-classifier.test.js`
- Create: `apps/life-manager/lib/browser-job-store.test.js`
- Create: `apps/life-manager/lib/generic-browser-task.test.js`
- Create: `apps/life-manager/lib/stagehand-steel-driver.test.js`
- Create: `apps/life-manager/test/browser-task-telegram-http-contract.test.js`
- Create: `apps/life-manager/lib/browser-job-migration.test.js`

- [ ] Write a classifier test that accepts an ordinary natural-language delegated browser action without a slash command and rejects conversation, feedback, settings commands, financial outflow, KYC, and ambiguous requests.
- [ ] Write queue tests proving Telegram message idempotency, tenant binding, strict prompt hashing, no raw credential persistence, and one concurrency-safe job claim.
- [ ] Write orchestrator tests proving discovery precedes site selection, selection is not supplied by a site registry, action precedes independent provider readback, Telegram is terminal, and Steel release always occurs.
- [ ] Write at-most-once tests: pre-action failure may return `failed`; post-action uncertainty returns `possibly_completed` and never invokes the action twice.
- [ ] Write a driver boundary test for private Railway Steel CDP, `Host: localhost:<port>`, Gemini-backed Stagehand, typed readback, and rejection of public/local CDP endpoints.
- [ ] Write the real HTTP contract test: an authenticated Telegram update for a linked user enqueues exactly one browser job and returns 200 before any browser action; an unrelated message retains the current onboarding/reply behavior.
- [ ] Write the migration contract test for tenant-safe queue, prompt hash uniqueness, closed statuses, claim RPC, bounded trace/receipt JSON, and service-role-only access.
- [ ] Run the new tests and capture RED caused by missing production modules, not by malformed fixtures.

### Task 2: Implement the safe natural-language intake and durable queue

**Files:**

- Create: `apps/life-manager/lib/browser-task-classifier.js`
- Create: `apps/life-manager/lib/browser-job-store.js`
- Create: `apps/life-manager/migrations/2026-07-28-lm-browser-jobs.sql`
- Modify: `apps/life-manager/server.js`

- [ ] Implement a Gemini JSON-schema classifier whose output is validated and fail-closed.
- [ ] Convert only `explicit_request + reversible + zero_cost + browser_required` into a queue request.
- [ ] Persist `uid`, Telegram chat/message/update ids, prompt hash, bounded redacted goal, locale, state, timestamps, and empty trace; do not persist credentials or raw model prose.
- [ ] Add an atomic PostgreSQL claim RPC using `FOR UPDATE SKIP LOCKED` and a stale-lease rule.
- [ ] Insert classification after typed wallet/feedback/control routing and before onboarding fallback, preserving every existing branch.
- [ ] Reply once with a queued receipt only after the durable insert succeeds; duplicate Telegram delivery returns the existing job id without creating another job.
- [ ] Run the Task 1 intake/store/HTTP/migration tests until GREEN.

### Task 3: Implement the Steel + Stagehand generic driver

**Files:**

- Create: `apps/life-manager/lib/stagehand-steel-driver.js`
- Modify: `apps/life-manager/lib/steel-cdp-client.js`
- Modify: `apps/life-manager/package.json`
- Modify: `apps/life-manager/package-lock.json`

- [ ] Add pinned Stagehand v3 and Zod dependencies.
- [ ] Expose a Steel session lifecycle that returns the raw private websocket endpoint without creating the old deterministic CDP connection twice.
- [ ] Construct Stagehand with `env: "LOCAL"`, private Steel `cdpUrl`, Railway-safe `cdpHeaders`, and `google/gemini-2.5-flash` using the existing `GEMINI_API_KEY`.
- [ ] Start on a search engine and give the agent one closed task: discover candidates, choose a suitable unregistered site, explain the choice in structured output, and perform the explicitly delegated action once.
- [ ] Independently extract a bounded typed provider receipt from the resulting provider page. Agent narration alone is never success.
- [ ] Return only the selected origin/URL, selection rationale, action status, provider receipt fields, session id, and release status.
- [ ] Run the driver/orchestrator tests until GREEN.

### Task 4: Implement the cloud worker and terminal Telegram trace

**Files:**

- Create: `apps/life-manager/lib/generic-browser-task.js`
- Create: `apps/life-manager/lib/browser-job-runtime.js`
- Create: `apps/life-manager/lib/browser-job-runtime.test.js`
- Modify: `apps/life-manager/server.js`

- [ ] Implement one-job execution with ordered trace stages: `claimed → discovery → selected → action_started → action_observed → provider_readback → telegram_sent → steel_released`.
- [ ] Persist every stage with timestamps and bounded non-secret metadata.
- [ ] Make terminal state conditional on provider readback: `completed`, `possibly_completed`, `handoff_required`, or `failed`.
- [ ] Render one concise Telegram terminal receipt with selected site, action, provider confirmation identifier/status, and trace id; store the real Telegram `message_id`.
- [ ] Start the browser worker independently of Mac/OpenClaw loop ownership, with a process-local overlap guard plus the database claim.
- [ ] Run runtime tests covering success, classifier abstention, login/CAPTCHA handoff, timeout before action, timeout after action, Telegram rejection, worker restart, and session release.

### Task 5: Verify locally and deploy

**Files:**

- Modify: `apps/life-manager/package.json`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

- [ ] Run the focused browser suite.
- [ ] Run the full `npm test` suite.
- [ ] Apply the production migration and verify its schema/RPC from PostgreSQL.
- [ ] Commit and push the feature branch; open and merge the PR only after CI is green.
- [ ] Verify Railway deployed the exact merge SHA and the service health endpoint reports the new build.

### Task 6: Run the real production E2E

**Files:**

- Create: `apps/life-manager/scripts/browser-gen-production-e2e.js`
- Create: `docs/evidence/browser/2026-07-28-browser-gen-1.json`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

- [ ] Use a real Telegram natural-language request for a reversible, zero-cost task using the agent-owned `contact@aniccaai.com` identity.
- [ ] Let the production classifier and queue receive it; do not call the driver directly.
- [ ] Verify the job selects a site that is absent from repository configuration and was discovered during the cloud run.
- [ ] Verify the action in the provider UI and capture independent provider-side readback.
- [ ] Verify Telegram receives the final trace and record its real message id.
- [ ] Verify the Steel session is released and a second session can be created immediately.
- [ ] Verify no local Chrome/CloakBrowser/Playwright/CDP process, tab, navigation, or profile timestamp changed during the run.
- [ ] Save a secret-free evidence bundle and mark BROWSER-GEN-1 done only if every done-contract field is present.
- [ ] Commit, push, merge, and then advance the SSOT cursor to BROWSER-AUTH-1.
