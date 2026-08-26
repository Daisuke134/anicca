# Life Manager Fundraiser Loop Implementation Plan

**Goal:** Reuse the working Luna application behavior and Life Manager runtime so Life Manager wakes
every 30 minutes, finds, submits, and tracks as many eligible funding applications as possible without
provider-specific code or an arbitrary application cap.

**Spec:** `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`

## Completed preparation

- [x] Audit current Life Manager, fundraising skills, working application loop, and four pinned OSS repositories.
- [x] Reject compiler, funder/source registry, numbered catalog, provider adapter, selector map, dedicated database, dedicated MCP, extra scheduler, and extra executor designs.

## Remaining atomic TODO

### Task 1: Add the Fundraiser objective to the existing Luna application behavior

**Files:**
- Modify: `.agents/startup-context.json`
- Modify: `scripts/startup-context/{lib,build-kit}.mjs`
- Regenerate: `fundraising/application-kit/*`
- Create: `skills/fundraiser-agent/SKILL.md`
- Create: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/evals/fundraiser-loop.test.mjs`

- [x] Write RED evals for unseen forms, duplicate/new cohorts, multiple same-pass submissions, reasonable inference, protected exact facts, human-only fields, and ambiguous Submit.
- [x] Extend the canonical context and generated kit with the mission, all-living-beings vision, OSS/cloud delivery, and founder-attested approximately $1,000 revenue provenance.
- [x] Write one provider-agnostic continuous prompt that makes Luna search Web/X, qualify, infer ordinary missing answers, submit each identity once, capture readback, report to Telegram, and continue after the first application.
- [x] Prove through behavioral eval cases that the continuous behavior handles unfamiliar forms and two same-pass applications without provider-specific assumptions.
- [x] Run `node --test test/startup-context.test.mjs test/startup-context-export.test.mjs skills/fundraiser-agent/evals/fundraiser-loop.test.mjs` and reach GREEN.
- [ ] Commit and push `feat(fundraising): maximize continuous Luna fundraiser throughput`.

### Task 2: Connect Fundraiser to the existing Life Manager loop

**Files:**
- Create: `apps/life-manager/migrations/2026-08-26-lm-browser-jobs-system-source.sql`
- Modify: `apps/life-manager/lib/browser-job-store.js`
- Modify: `apps/life-manager/lib/browser-job-store.test.js`
- Create: `apps/life-manager/lib/fundraiser-runtime.js`
- Create: `apps/life-manager/lib/fundraiser-runtime.test.js`
- Modify: `apps/life-manager/lib/connector-luna-judgment.js`
- Modify: `apps/life-manager/lib/connector-luna-judgment.test.js`
- Modify: `apps/life-manager/scheduler.js`
- Create: `apps/life-manager/lib/fundraiser-wiring.test.js`

- [ ] Let a Life Manager runtime job enqueue a browser job with `source_kind=runtime` and `source_ref=<runtime job id>` instead of fake Telegram IDs.
- [ ] Allow the existing local agent runner to invoke `application-intent-planner` and require its selected model to be Luna.
- [ ] Write RED tests for one acquisition claim per 30-minute window, maximum candidate throughput within the pass, and continuous reply tracking.
- [ ] Implement `fundraiserUserOnce` using the existing Life Manager job claim and browser worker; do not add a daemon, CLI, shell/Python runner, scheduler, or browser implementation.
- [ ] Wire `fundraiserUserOnce` into `organsUserOnce` behind the existing `daily_automation_enabled` gate.
- [ ] Keep long Luna/browser work off the scheduler tick: claim, queue, read back the queue row, and return.
- [ ] Prove a Fundraiser failure does not stop another Life Manager organ or tenant.
- [ ] Run `node --test apps/life-manager/lib/fundraiser-runtime.test.js apps/life-manager/lib/fundraiser-wiring.test.js apps/life-manager/lib/maybe-start-loops.test.js` and reach GREEN.
- [ ] Commit and push `feat(life-manager): run fundraiser as a native organ`.

### Task 3: Reuse existing receipts for exactly-once application

**Files:**
- Create: `apps/life-manager/migrations/2026-08-26-lm-runtime-application-effect.sql`
- Modify: `apps/life-manager/lib/runtime-job-store.js`
- Modify: `apps/life-manager/lib/runtime-job-store.test.js`
- Modify: `skills/fundraiser-agent/prompts/daily.md`

- [ ] Write RED tests for duplicate URLs resolving to the same `organization + program + cohort/window + account` effect identity.
- [ ] Add the smallest generic receipt read needed to give Luna prior application identities; add no fundraising table.
- [ ] Extend the shared runtime contract with the `application` effect class, including reconciliation SQL; add no fundraising table.
- [ ] Claim the application effect immediately before Submit and store the UI/mail readback in the immutable receipt.
- [ ] Make `submit_unknown` replay-zero: the loop tracks it but never clicks Submit again automatically.
- [ ] Prove the same cohort is blocked and a genuinely new cohort remains eligible.
- [ ] Run `node --test apps/life-manager/lib/runtime-job-store.test.js skills/fundraiser-agent/evals/fundraiser-loop.test.mjs` and reach GREEN.
- [ ] Commit and push `feat(runtime): make fundraiser applications replay-zero`.

### Task 4: Track applications through interview and funding

**Files:**
- Create: `skills/fundraiser-agent/prompts/inbox.md`
- Create: `skills/fundraiser-agent/evals/inbox-loop.test.mjs`

- [ ] Write RED evals for confirmation, rejection, waitlist, interview, offer, funding, duplicate mail, and unrelated mail.
- [ ] Match Gmail provider/thread IDs to the existing ApplicationReceipt and append the next state.
- [ ] Create a Calendar event and interview brief when an interview is confirmed.
- [ ] Stop for founder attendance, CAPTCHA, video, KYC, binding terms, banking, or funds movement.
- [ ] Require executed terms plus provider/bank readback before recording `funded`.
- [ ] Run `node --test skills/fundraiser-agent/evals/inbox-loop.test.mjs` and reach GREEN.
- [ ] Commit and push `feat(fundraising): track application outcomes`.

### Task 5: Turn on and prove the 24/7 Life Manager loop

**Files:**
- Create: `docs/evidence/fundraising/fundraiser-live-acceptance.md`
- Modify: `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`

- [ ] Deploy through the existing Life Manager scheduler and browser worker; start no second owner.
- [ ] Run one natural acquisition slot and verify scheduler claim, Luna/browser trace, Submit effect, and provider readback.
- [ ] Complete three unrelated live forms without changing production code between forms.
- [ ] Run the next 30-minute slot and verify zero duplicate application effects while new identities continue.
- [ ] Verify the four-hour tracking slot updates the original receipt and creates interview Calendar data when applicable.
- [ ] Audit the public repository for credentials, private receipts, provider-specific code, compiler, and registry artifacts.
- [ ] Commit and push the live evidence and final spec state.

## Done

The feature is complete only when the natural Life Manager owner submits an unseen eligible form,
stores official readback, the next daily slot is replay-zero, and the tracking loop advances the same
receipt without any provider-specific production change.
