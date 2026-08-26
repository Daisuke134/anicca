# Life Manager Fundraiser Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Life Manager searches the live web and X every day, finds one new eligible funding application, reads and fills its unfamiliar browser form directly, submits once, and tracks the official result without applying twice.

**Architecture:** One general agent uses existing web, browser, mail, Calendar, agent-runner, and runtime effect/receipt capabilities. It reads current Life Manager context and visible form questions directly; there is no compiler, funder/source registry, numbered program list, provider adapter, selector map, or program script. Only submitted/human-blocked ApplicationReceipts persist for dedupe and tracking; rejected discovery candidates remain in per-run evidence.

**Tech Stack:** Existing Life Manager/OpenClaw agent runtime and cron, existing browser lease/tools, existing runtime job/effect/receipt store, Gmail, and Calendar.

**Spec:** `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`

## Global constraints

- No compiler of questions, answers, targets, sources, or applications.
- No funder registry, source registry, numbered accelerator catalog, or capability allowlist.
- No funder-specific Python, JavaScript, shell, selector, field map, or adapter.
- The model generates searches, judges fit, reads visible questions, and chooses browser actions.
- Existing deterministic code stores effects/receipts and prevents duplicates; it does not judge programs.
- Acquisition runs once daily and targets one new eligible application.
- Existing receipts prevent reapplication to the same organization/program/cohort/account.
- X provides leads; the official page provides deadline, eligibility, terms, and application truth.
- No unverified revenue, user, media, legal, visa, or funding claim enters a form.
- CAPTCHA, founder video, interview, KYC, binding terms, and funds movement remain human ceremonies.
- Each task ends with focused verification, commit, and push.

---

### Task 0: Pin predecessor code and correct the architecture

**Files:**
- Create: `docs/evidence/fundraising/2026-08-26-fundraiser-predecessor-code-audit.md`
- Create: `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`
- Create: `docs/superpowers/plans/2026-08-26-life-manager-fundraiser-agent.md`

**Interfaces:**
- Consumes: four pinned OSS repositories and current Life Manager browser/fundraising code.
- Produces: source audit, no-compiler/no-registry specification, and ordered implementation plan.

- [x] **Step 1: Create the isolated `fundraiser-agent-task0-20260826` worktree.**
- [x] **Step 2: Run the existing fundraising tests and observe 21/21 PASS.**
- [x] **Step 3: Clone Outreachr, Venture-Ops, fundraising-skills, and open-org.**
- [x] **Step 4: Read actual entrypoint, state, effect, readback, and recovery code.**
- [x] **Step 5: Record pinned commits, licenses, adopted contracts, and rejected architectures.**
- [x] **Step 6: Make DelightX a live-search example, not a provider implementation.**
- [x] **Step 7: Remove compiler, registry, dedicated store, and dedicated MCP plans.**
- [x] **Step 8: Re-run document, test, diff, and remote verification; commit and push the correction.**

### Task 1: Give the existing general agent the Fundraiser objective

**Files:**
- Create: `skills/fundraiser-agent/SKILL.md`
- Create: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/prompts/inbox.md`
- Create: `skills/fundraiser-agent/schemas/pass.v1.json`
- Create: `skills/fundraiser-agent/evals/cases.jsonl`

**Interfaces:**
- Consumes: current startup context, past ApplicationReceipts, and existing web/browser/mail/Calendar tools.
- Produces: one daily acquisition result and read-mostly tracking results.

- [ ] **Step 1: Write semantic eval cases before the prompt.**

Include an unseen multi-page form, a program absent from all repository files, an already-submitted
cohort, a genuinely new cohort, an X rumor without an official page, contradictory official dates,
missing founder video, and ambiguous Submit.

- [ ] **Step 2: Run the existing skill eval harness and confirm the missing prompt fails.**
- [ ] **Step 3: Write a right-altitude daily prompt.**

It says: search broadly, follow live evidence, find one new eligible application, read the official
page, read the form, answer visible questions from current context, submit once, capture readback, and
continue tracking. It does not list form fields, providers, search queries, program numbers, scores, or
decision branches.

- [ ] **Step 4: Write the inbox prompt without acquisition or Submit authority.**
- [ ] **Step 5: Add a static test rejecting compiler language, registry files, selector syntax, provider switches, fixed queries, and fixed fit scores.**
- [ ] **Step 6: Run all semantic/static evals.**
- [ ] **Step 7: Commit `feat(fundraising): define the daily general fundraiser agent` and push.**

### Task 2: Register the prompts in the existing agent scheduler

**Files:**
- Modify: `skills/fundraiser-agent/SKILL.md`
- Create: `skills/fundraiser-agent/evals/schedule-cases.jsonl`
- Create: `docs/evidence/fundraising/fundraiser-cron-installation.md`

**Interfaces:**
- Consumes: the existing OpenClaw cron scheduler and the Task 1 prompts.
- Produces: exactly one isolated acquisition owner at 06:30 JST and one isolated read-mostly inbox owner every four hours, with no new executable, wrapper, plist generator, or loop-specific runtime.

- [ ] **Step 1: Record a read-only baseline with `openclaw cron list --json` and dedupe by stable job name.**
- [ ] **Step 2: Add schedule evals proving acquisition runs at most once per local day and inbox tracking has no Submit authority.**
- [ ] **Step 3: Register the daily prompt with the existing scheduler.**

Use `openclaw cron add --name life-manager-fundraiser-daily --cron '30 6 * * *' --tz Asia/Tokyo
--session isolated --message 'Use $fundraiser-agent to run one daily acquisition pass.' --no-deliver
--json`. Do not add a shell script, Python file, JavaScript entrypoint, plist, or `loop.toml`.

- [ ] **Step 4: Register the read-mostly inbox prompt with the same existing scheduler.**

Use `openclaw cron add --name life-manager-fundraiser-inbox --cron '17 */4 * * *' --tz Asia/Tokyo
--session isolated --message 'Use $fundraiser-agent to run one inbox and application-status pass.'
--no-deliver --json`.

- [ ] **Step 5: Read both jobs back with `openclaw cron get`, verify exact prompt/cadence/session, and store only public-safe redacted evidence.**
- [ ] **Step 6: Run each natural owner once with `openclaw cron run`; verify its run history belongs to that cron job rather than a Codex-spawned executor.**
- [ ] **Step 7: Commit only the public skill instructions, schedule evals, and redacted installation evidence; push.**

### Task 3: Reuse the existing runtime receipts for dedupe

**Files:**
- Modify: `apps/life-manager/lib/runtime-job-store.js`
- Modify: `apps/life-manager/lib/runtime-job-store.test.js`
- Modify: `skills/fundraiser-agent/prompts/daily.md`

**Interfaces:**
- Consumes: existing `lm_runtime_jobs`, effect uniqueness, immutable receipts, and reconciliation.
- Produces: generic read methods for completed effects by capability/date and prior ApplicationReceipts.

- [ ] **Step 1: Write a failing test that queries existing `fundraiser_application` effects without adding a fundraising table.**
- [ ] **Step 2: Write a failing test proving two URLs for the same receipt identity cannot create a second effect.**
- [ ] **Step 3: Run the tests and confirm RED.**
- [ ] **Step 4: Add the smallest generic runtime-store read methods needed by any loop to list its prior effects and receipts.**
- [ ] **Step 5: Use the existing effect key for `organization + program + cohort/window + account`; do not store candidates.**
- [ ] **Step 6: Make the daily prompt stop acquisition when today's receipt already shows an application effect.**
- [ ] **Step 7: Prove a new cohort has a new identity while the same cohort remains replay-zero.**
- [ ] **Step 8: Run runtime-store tests, commit `feat(runtime): expose prior effect receipts to agents`, and push.**

### Task 4: Search the live web and X every day

**Files:**
- Modify: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/evals/discovery-cases.jsonl`

**Interfaces:**
- Consumes: current Life Manager context, public web crawl, authenticated `x:anicca` browser lease, and run evidence.
- Produces: one chosen official application URL or an evidence-backed exhausted result.

- [ ] **Step 1: Add evals requiring the model to generate its own English and Japanese searches.**
- [ ] **Step 2: Require source expansion after a site returns no applicable result.**
- [ ] **Step 3: Require X leads to be verified on an official page before use.**
- [ ] **Step 4: Lease `x:anicca` read-only through the existing guard, then release it before application work.**
- [ ] **Step 5: Forbid access to x-repost publishing tools, query files, and state.**
- [ ] **Step 6: Prove DelightX and a completely unknown program follow the identical tool path.**
- [ ] **Step 7: Prove rejected candidates exist only in run evidence, not a registry/database.**
- [ ] **Step 8: Run evals, commit `feat(fundraising): discover live applications from web and X`, and push.**

### Task 5: Apply through the unfamiliar browser form

**Files:**
- Modify: `skills/fundraiser-agent/prompts/daily.md`
- Create: `skills/fundraiser-agent/evals/browser-cases.jsonl`

**Interfaces:**
- Consumes: rendered browser observations, startup context, and prior receipts.
- Produces: one ApplicationReceipt or a human/ambiguity checkpoint.

- [ ] **Step 1: Add three unrelated form fixtures with different labels, layouts, page counts, uploads, and review screens.**
- [ ] **Step 2: Require one model-chosen action followed by a fresh observation.**
- [ ] **Step 3: Require the model to answer each visible question directly from context; no intermediate question or answer artifact.**
- [ ] **Step 4: Block unverified revenue, users, legal status, visa status, and media.**
- [ ] **Step 5: Re-read the final review page, claim the existing runtime effect, and click Submit once.**
- [ ] **Step 6: Capture fresh UI evidence and confirmation mail when available.**
- [ ] **Step 7: Record timeout/navigation loss as `submit_unknown` and never retry automatically.**
- [ ] **Step 8: Scan production changes for funder names/selectors and require zero provider-specific execution code.**
- [ ] **Step 9: Run evals, commit `feat(fundraising): apply through live browser feedback`, and push.**

### Task 6: Track replies, interviews, decisions, and money

**Files:**
- Modify: `skills/fundraiser-agent/prompts/inbox.md`
- Create: `skills/fundraiser-agent/evals/inbox-cases.jsonl`

**Interfaces:**
- Consumes: Gmail provider IDs/thread IDs, Calendar, and ApplicationReceipts.
- Produces: appended tracking receipts and human ceremony handoffs.

- [ ] **Step 1: Add confirmation, rejection, interview, waitlist, unrelated-mail, duplicate-message, offer, and funding fixtures.**
- [ ] **Step 2: Match mail using provider identity, account, application evidence, and time window, never subject keywords alone.**
- [ ] **Step 3: Update the existing receipt lineage rather than create a target registry.**
- [ ] **Step 4: Create Calendar events and interview briefs automatically.**
- [ ] **Step 5: Keep attendance, KYC, binding documents, and money movement as human ceremonies.**
- [ ] **Step 6: Require executed terms plus provider/bank readback before `funded`.**
- [ ] **Step 7: Run evals, commit `feat(fundraising): track applications to funded readback`, and push.**

### Task 7: Prove open-source live operation

**Files:**
- Modify: `docs/superpowers/specs/2026-08-26-life-manager-fundraiser-agent-design.md`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- Create: `docs/evidence/fundraising/2026-08-26-fundraiser-live-acceptance.md`

**Interfaces:**
- Consumes: Tasks 1-6 and the installed release.
- Produces: natural-owner receipts, replay-zero, public-safe source, and updated SSOT.

- [ ] **Step 1: Publish/install without starting another browser or redundant executor.**
- [ ] **Step 2: Kickstart the natural acquisition owner once.**
- [ ] **Step 3: Observe a program absent from every checked-in source/program file.**
- [ ] **Step 4: Complete three unrelated live forms over natural daily passes without code changes between them.**
- [ ] **Step 5: Verify the next pass does not reapply to any prior receipt identity.**
- [ ] **Step 6: Verify Fundraiser and x-repost lease X sequentially without state/session corruption.**
- [ ] **Step 7: Verify UI/mail receipts, runtime effect history, Calendar, Telegram message IDs, and replay-zero.**
- [ ] **Step 8: Audit the public repository for secrets, personal data, private receipts, compiler/registry files, and provider-specific application code.**
- [ ] **Step 9: Publish only generic prompts, schemas, eval fixtures, scheduler installation instructions, and shared runtime changes.**
- [ ] **Step 10: Update both specs, commit, and push.**

## Self-review

- The plan contains no compiler, funder/source registry, numbered catalog, dedicated fundraising database, or dedicated MCP server.
- The model owns all search, fit, priority, answer, and browser judgment.
- Persistent data starts at ApplicationReceipt/human checkpoint, solely for dedupe and tracking.
- Existing shared runtime machinery owns claims, immutable receipts, ambiguity, and replay-zero.
- New programs require no repository changes.
- Scheduling reuses OpenClaw cron directly; no Fundraiser executable, wrapper, plist, or scheduler adapter exists.
- Every implementation task has a failing test/eval, minimal change, verification, commit, and push.
