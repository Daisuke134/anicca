# Life Manager Fundraiser Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run one daily Life Manager Fundraiser Agent that discovers and applies to a new eligible funding opportunity from live web and X sources without program-specific code, then tracks it without duplicate applications.

**Architecture:** A scheduled general agent owns discovery, qualification, and unfamiliar browser interaction. Typed MCP tools expose a deterministic Node SQLite ledger for source provenance, opportunity identity, daily/effect claims, readbacks, and state transitions. Program pages and layouts are runtime observations, not checked-in adapters or registry prerequisites.

**Tech Stack:** Existing agent runner, existing browser tools and registry, Node.js `node:sqlite`, MCP SDK, Zod, launchd generated from `loop.toml`, Gmail and Calendar readback.

**Spec:** `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`

## Global Constraints

- No funder-specific Python, JavaScript, shell, selector, field map, or browser adapter.
- `fundraising/funders/<id>.json` is not required before discovery or application.
- Fit, source choice, priority, and form interpretation stay model judgments.
- Use existing registered browser owners and leases; never start a new Chrome owner.
- Run one acquisition pass per day. Inbox reconciliation cannot claim an acquisition effect.
- Submit at most one new identity per pass and never automatically retry `submit_unknown`.
- Do not assert revenue, users, media, submission, offer, or funding without current evidence.
- CAPTCHA, founder video, interview, KYC, visa declarations, binding terms, and funds movement are human ceremonies.
- Every implementation task ends in focused verification, commit, and push.

---

### Task 0: Pin predecessor code and freeze the design

**Files:**
- Create: `docs/evidence/fundraising/2026-08-26-fundraiser-predecessor-code-audit.md`
- Create: `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`
- Create: `docs/superpowers/plans/2026-08-26-life-manager-fundraiser-agent.md`

**Interfaces:**
- Consumes: current fundraising code, browser/X loops, and four cloned OSS repositories.
- Produces: pinned evidence, accepted architecture, and ordered implementation contract.

- [x] **Step 1: Create an isolated worktree from `origin/main`.**

Worktree: `.worktrees/fundraiser-agent-task0-20260826`

- [x] **Step 2: Run the current fundraising baseline.**

Run: `node --test test/startup-context.test.mjs skills/apply-to-funder/__tests__/context.test.mjs`

Observed: 21 tests passed, 0 failed.

- [x] **Step 3: Clone and pin four predecessor repositories.**

The evidence file contains exact commits, licenses, entrypoints, state, effect, readback, recovery,
and adoption/rejection decisions.

- [x] **Step 4: Add DelightX and live X discovery to the source design.**

DelightX is a source seed, not a provider implementation. X discovery uses the registered leased
browser and verifies every actionable claim on an official page.

- [x] **Step 5: Prohibit thin adapters and funder-specific scripts.**

The design assigns judgment to the model and mechanical state to typed tools only.

- [x] **Step 6: Validate Task 0 documents.**

Run the placeholder scan, baseline tests, `git diff --check`, and `git status --short`. Expected:
no placeholder, 21 passing tests, clean diff check, and exactly three new documents.

- [x] **Step 7: Commit Task 0.**

Commit message: `docs(fundraising): design daily general fundraiser agent`

### Task 1: Schedule prompt-backed agents without a per-loop CLI

**Files:**
- Modify: `bin/plistgen.py`
- Create: `test/plistgen-agent-job.test.mjs`
- Create: `loops/fundraiser/loop.toml`

**Interfaces:**
- Consumes: `runtime/agent-runner/agent_runner.py --prompt-file` and `browser-lane-agent`.
- Produces: declarative `agent` jobs generated directly into launchd arguments.

- [ ] **Step 1: Write a failing plist test for an `agent` job.**

Fixture:

```toml
[jobs.acquire]
agent = { prompt = "skills/fundraiser-agent/prompts/daily.md", schema = "skills/fundraiser-agent/schemas/pass.v1.json", task_class = "browser-lane-agent" }
calendar = { hour = 6, minute = 30 }
```

Assert `ProgramArguments` invokes the existing runner with prompt, schema, task class, loop name,
workdir, and evidence directory. Assert there is no new fundraiser launcher.

- [ ] **Step 2: Run `node --test test/plistgen-agent-job.test.mjs` and confirm RED.**
- [ ] **Step 3: Add the mutually exclusive `program` or `agent` branch to `plistgen.py`.**
- [ ] **Step 4: Reject missing/escaping prompt and schema paths.**
- [ ] **Step 5: Declare acquisition at 06:30 and read-mostly inbox reconciliation every four hours.**
- [ ] **Step 6: Run the focused test, existing job-hunter dispatch test, and plist diff.**
- [ ] **Step 7: Commit `feat(loops): schedule prompt-backed agent jobs` and push.**

### Task 2: Add the deterministic fundraising store

**Files:**
- Create: `apps/life-manager/lib/fundraiser-store.js`
- Create: `apps/life-manager/lib/fundraiser-store.test.js`

**Interfaces:**
- Consumes: private SQLite path and ISO timestamps.
- Produces: `FundraiserStore.recordSource`, `recordOpportunity`, `listUnapplied`,
  `claimDailyApplication`, `claimSubmit`, `recordEffect`, `recordReadback`, `recordMessage`, and
  `listDueActions`.

- [ ] **Step 1: Write a failing identity test.**

Two URLs for one organization/program/cohort/account resolve to one opportunity. A new cohort resolves
to another opportunity.

- [ ] **Step 2: Run the focused test and confirm RED.**
- [ ] **Step 3: Implement `node:sqlite` tables for sources, opportunities, applications, effects, readbacks, messages, transitions, and daily claims.**
- [ ] **Step 4: Add unique constraints for opportunity identity, provider message ID, effect digest, and local-date acquisition claim.**
- [ ] **Step 5: Implement the exact state transitions from the spec.**
- [ ] **Step 6: Prove `0600`, replay returns the original receipt, and a second daily/Submit claim fails before I/O.**
- [ ] **Step 7: Run the focused test, commit `feat(fundraising): add durable opportunity and effect store`, and push.**

### Task 3: Expose bookkeeping as typed MCP tools

**Files:**
- Create: `skills/fundraiser-agent/mcp.mjs`
- Create: `skills/fundraiser-agent/mcp.test.mjs`
- Create: `skills/fundraiser-agent/schemas/pass.v1.json`

**Interfaces:**
- Consumes: `FundraiserStore` and `FUNDRAISER_STATE_DIR`.
- Produces: tools `record_source`, `record_opportunity`, `list_unapplied`,
  `claim_daily_application`, `claim_submit`, `record_effect`, `record_readback`, `record_message`, and
  `list_due_actions`.

- [ ] **Step 1: Write failing tests for malformed evidence, invalid transitions, duplicate daily claims, and a second Submit claim.**
- [ ] **Step 2: Run the tests and confirm RED.**
- [ ] **Step 3: Implement Zod handlers that call one store method each.**
- [ ] **Step 4: Assert the MCP exposes no email, browser, shell, payment, or Submit transport.**
- [ ] **Step 5: Run MCP and store tests.**
- [ ] **Step 6: Commit `feat(fundraising): expose typed fundraiser ledger tools` and push.**

### Task 4: Define the general agent prompts and canonical evals

**Files:**
- Create: `skills/fundraiser-agent/SKILL.md`
- Create: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/prompts/inbox.md`
- Create: `skills/fundraiser-agent/evals/cases.jsonl`

**Interfaces:**
- Consumes: startup context, application kit, typed MCP, and existing web/browser/mail/calendar tools.
- Produces: one bounded acquisition decision and read-mostly inbox decisions.

- [ ] **Step 1: Add eval cases before prompts.**

Cover an unseen multi-page form, submitted rolling program, new cohort, X rumor without official page,
DelightX date contradiction, missing founder video, ambiguous Submit, and confirmation message.

- [ ] **Step 2: Write the right-altitude daily prompt with objective, evidence contract, tools, states, daily limit, and human ceremonies.**
- [ ] **Step 3: Write the inbox prompt without `claim_daily_application` or `claim_submit`.**
- [ ] **Step 4: Add an anti-hardcoding test for selector syntax, provider switches, fixed queries, and fixed fit scores.**
- [ ] **Step 5: Run at least eight semantic eval cases.**
- [ ] **Step 6: Commit `feat(fundraising): define general daily fundraiser agent` and push.**

### Task 5: Wire dynamic web and X discovery

**Files:**
- Modify: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/evals/discovery-cases.jsonl`

**Interfaces:**
- Consumes: official web crawl, registered `x:anicca` lease, and prior source yield.
- Produces: source/opportunity records with official evidence chains.

- [ ] **Step 1: Add failing evals requiring new English and Japanese searches each pass.**
- [ ] **Step 2: Require X to produce leads only; official pages establish program truth.**
- [ ] **Step 3: Acquire `x:anicca` read-only through the guard and release it before application work.**
- [ ] **Step 4: Forbid reads/writes to x-repost state and publishing tools.**
- [ ] **Step 5: Continue to adjacent sources after one source has no results.**
- [ ] **Step 6: Prove DelightX and an unknown source use the same prompt/tool path.**
- [ ] **Step 7: Run evals, commit `feat(fundraising): add dynamic web and X discovery`, and push.**

### Task 6: Operate unfamiliar forms with the general browser

**Files:**
- Modify: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/evals/browser-cases.jsonl`

**Interfaces:**
- Consumes: rendered observations and canonical fundraising facts.
- Produces: browser receipts, one-shot effect receipt, and fresh completion observation.

- [ ] **Step 1: Add three unrelated form fixtures with different controls and page layouts.**
- [ ] **Step 2: Require exactly one model-chosen action per fresh observation.**
- [ ] **Step 3: Bind every nontrivial answer claim to current evidence.**
- [ ] **Step 4: Keep unknown revenue, users, legal/visa status, and media blocked.**
- [ ] **Step 5: Re-read the review page, claim Submit, click once, and capture a new observation.**
- [ ] **Step 6: Convert timeout/navigation loss to `submit_unknown` with no retry.**
- [ ] **Step 7: Scan the implementation for funder names outside eval fixtures; expect no execution branch.**
- [ ] **Step 8: Commit `feat(fundraising): operate unseen forms through browser feedback` and push.**

### Task 7: Track confirmation through funded readback

**Files:**
- Modify: `skills/fundraiser-agent/prompts/inbox.md`
- Create: `skills/fundraiser-agent/evals/inbox-cases.jsonl`

**Interfaces:**
- Consumes: Gmail provider IDs/thread IDs, Calendar, and application ledger.
- Produces: confirmed transitions, due actions, interview packs, and human ceremonies.

- [ ] **Step 1: Add confirmation, rejection, interview, waitlist, unrelated mail, duplicate ID, and funding-paperwork fixtures.**
- [ ] **Step 2: Match with provider identity, account, program/application evidence, and time window; never subject keywords alone.**
- [ ] **Step 3: Automate Calendar and interview preparation, not attendance.**
- [ ] **Step 4: Keep KYC, binding terms, and money movement as human ceremonies.**
- [ ] **Step 5: Require executed terms plus provider/bank receipt before `funded`.**
- [ ] **Step 6: Run evals, commit `feat(fundraising): track applications through funded readback`, and push.**

### Task 8: Prove live generalization and deploy the natural owner

**Files:**
- Modify: `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- Create: `docs/evidence/fundraising/2026-08-26-fundraiser-live-acceptance.md`

**Interfaces:**
- Consumes: Tasks 1-7 and the installed release.
- Produces: unseen-form receipts, installed owner, replay-zero, and updated SSOT.

- [ ] **Step 1: Publish and install without a second browser or executor.**
- [ ] **Step 2: Kickstart the existing natural acquisition owner once.**
- [ ] **Step 3: Observe one opportunity absent from the release-time source set.**
- [ ] **Step 4: Complete three unrelated live forms over natural daily passes without provider code changes.**
- [ ] **Step 5: Verify the next pass produces zero duplicate effect for prior applications.**
- [ ] **Step 6: Verify Fundraiser and x-repost lease the browser sequentially without state/session corruption.**
- [ ] **Step 7: Verify installed provenance, UI/mail receipts, ledger, replay-zero, and Telegram message IDs.**
- [ ] **Step 8: Update both specs, commit, and push.**

## Self-review

- Daily discovery, X, unseen forms, one-per-day, dedupe, tracking, human gates, readback, and replay-zero map to Tasks 1-8.
- No new Python or provider-specific application script is planned.
- No funder registry entry is a capability prerequisite.
- Deterministic code stores and fences; model judgment remains in prompts.
- Every implementation task has an independent test/eval and commit boundary.
