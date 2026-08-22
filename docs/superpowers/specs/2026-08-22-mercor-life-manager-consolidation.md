# Mercor → Life Manager 統合仕様

**Status:** migration-slice / loop not live
**Canonical repository:** `https://github.com/Daisuke134/life-manager`
**Canonical checkout:** `/Users/anicca/Projects/life-manager-main`

## 1. Repository boundary

`life-manager`だけがMercorのコード、skill、spec、loop、test、releaseの正本である。`profitable-claude`は移行元の履歴であり、移行完了後はMercorのproduction sourceとして参照しない。

「1つのrepository」はsource controlを1つにする意味であり、credentials、Google session、Mercor Cookie、resume PDF、個人プロフィール、応募台帳などのprivate runtime stateをGitへ入れる意味ではない。

## 2. Canonical layout

```text
life-manager/
├── skills/
│   ├── job-hunter/                         # fact bank/materials owner
│   │   ├── SKILL.md
│   │   └── references/mercor.md            # provider-specific reference
│   └── mercor/                             # user-facing Mercor skill facade
│       ├── SKILL.md
│       └── agents/openai.yaml
├── apps/job-search-loop/                   # sole browser/application side-effect owner
│   ├── job_search_loop/                    # deterministic state, adapters, evidence
│   ├── prompts/                            # bounded agent prompts
│   ├── schemas/                            # pass/application/result contracts
│   └── tests/
├── loops/job-hunter/                       # hourly/inbox/learning cadence
│   ├── loop.toml
│   └── registry.yaml
├── runtime/agent-runner/                   # provider/model routing and validation
└── docs/superpowers/specs/                 # this migration and acceptance evidence
```

Private runtime state remains outside the repository:

```text
~/.config/anicca/job-search/profile.json
~/.local/share/anicca/job-search/materials/
~/.local/state/anicca/job-search/mercor/
```

## 3. Ownership and no-duplication contract

| Responsibility | Canonical owner |
|---|---|
| Candidate facts and approved resume variants | `skills/job-hunter/` + private profile SSOT |
| Mercor auth and provider policy | `skills/mercor/SKILL.md` + `skills/job-hunter/references/mercor.md` |
| Mercor browser, form submission, read-back, locks, evidence | `apps/job-search-loop/` |
| Hourly/inbox/learning scheduling | `loops/job-hunter/` |
| Model/provider execution | `runtime/agent-runner/` |
| Private resume, Cookie, ledger and evidence | `~/.local/state/anicca/job-search/` |

Do not create `profitable-claude`-style second executors, a second Mercor loop, or a browser script inside the skill. The skill provides policy and routing; the existing job-search runtime owns side effects.

## 4. Mercor authentication boundary

- Use ordinary Google sign-in with the Keychain credential.
- Never click a browser Google 2FA button whose accessible name is `はい`; only the user taps `はい` inside the Gmail iOS app.
- Never click account recovery, reset, registration, recovery-email, or recursive alternate-method paths.
- If recovery/reset/wait appears, record the visible URL/text and stop.
- Use a dedicated Mercor browser profile; never navigate the job-search or trusted daily-driver tab.

## 5. Global role and locale scope

Mercor is not a Japanese-only lane. The provider must route every supported locale and role family through the same Job Hunter fact gate: Japanese, English, bilingual, business operations, AI-agent evaluation, research, data/CRM, product, and other roles are eligible when the approved profile and the live listing support them. Locale selects the approved material variant; it does not restrict discovery to Japanese jobs.

## 6. Loop behavior

The existing hourly Job Hunter acquisition loop becomes the single Mercor-capable loop. It must:

1. Reconcile the oldest in-progress Mercor application before discovering new work.
2. Deduplicate by stable Mercor listing/application identifier.
3. Apply only to grounded forms using approved facts and a verified resume artifact.
4. Route interviews, assessments, CAPTCHA, unsupported free-response questions, and ambiguous attestations to `needs_human`; never impersonate a candidate interview or assessment.
5. Re-open the application list after any submit and store evidence plus the external result.
6. Record settled earnings only when the Mercor Earnings UI proves payment; views, invitations, offers, and estimates are not earnings.

### 6.4 End-to-end money state machine

An application is only the first state; it is not income. The complete flow is:

```text
DISCOVERED
  → GROUNDED_READY
  → SUBMITTED_PENDING_REVIEW
  → SELECTED_OR_REJECTED
  → CONTRACTED
  → AUTHORIZED_WORK
  → WORK_ACCEPTED
  → PAID_SETTLED
  → REVENUE_LEDGER
```

The resident loop owns discovery, grounded submission, Gmail/status reconciliation, Calendar scheduling, evidence, and settled-payout read-back. It does not impersonate a human interview/assessment or perform work when the contract prohibits AI/automation. `PAID_SETTLED` requires a real Mercor Earnings/contract payment row; the hourly rate, an offer, an invitation, a selected application, or a pending balance never advances the revenue ledger.

Current money diagnosis: the account has three `SUBMITTED_PENDING_REVIEW` applications, no observed selection/contract, and Mercor Earnings says `No payment history yet`. Therefore settled revenue is not observed, not zeroed as a fabricated success, and no `$10K` claim is valid.

### 6.1 Ready-to-submit queue

The loop may submit a new listing without human intervention when the live application page proves all of the following:

- `3 of 3 steps completed` and `100%`;
- the completed `Domain Expert Interview` is explicitly reused;
- `Submit application` is visible;
- the listing/application identifier is not already in the private application ledger.

For each wake, select at most one new ready-to-submit listing, submit it once, reopen the application result, and append one evidence row. Never resubmit `submitted_pending_review`, click `Start` on a new interview, or infer readiness from a title alone.

Current ready queue observed in Mercor before the resident pass:

1. Data analysis / quantitative readouts Evaluator — $80–$120/hour (submitted in the resident pass below)
2. General business strategy / management Evaluator — $80–$120/hour
3. Humanities / arts / culture Evaluator — $80–$120/hour
4. Media / journalism / communications Evaluator — $80–$120/hour

Japanese language / cultural fluency Evaluator and Software / AI / IT / data Evaluator are already submitted and excluded from the queue.

## 6.3 Model-led execution decision

The Mercor macro loop must be model-led rather than a large selector script. The model observes the live page, decides the next safe action from the task packet, and adapts when the page changes. Deterministic code owns only the boundaries that must not drift: operator/profile isolation, lease ownership, approved domains, application dedupe, the single irreversible submit wrapper, read-back, evidence, and ledger writes.

### OSS code evidence and adopted patterns

The implementation comparison was performed against fixed public commits:

| OSS | Fixed commit | Observed mechanism | Adoption decision |
|---|---|---|---|
| `browser-use/browser-use` | `85ddbfedf609166b2d2c76c3d80506649fee82a9` | Model-led `Agent` loop; `AgentState`; `BrowserStateSummary`; short/long browser error memory; domain-filtered `ActionRegistry`; structured output schema; failure/loop budgets | Adopt the state/error/action-boundary pattern; do not copy the whole runtime |
| `browserbase/stagehand` | `a21633d53930abc5d62b8dbd6b608995f2ccb4b1` | Narrow `observe`, `act`, and schema-validated `extract` verbs over an owned browser session; explicit session cleanup | Adopt the narrow verbs and extraction contract; keep the existing Life Manager CDP owner |

The selected call graph is:

```text
existing launchd wake
  → job-hunter loop lease
  → runtime/agent-runner (model-led Mercor prompt)
  → observe live Mercor page
  → model selects next grounded action
  → guard validates domain/state/dedupe
  → act through owned browser session
  → extract success/read-back
  → deterministic evidence + ledger append
```

Do not encode every Mercor selector, role title, or page branch in shell/Python. When a page changes, the model re-observes and returns a structured `blocked`, `needs_human`, `submitted`, or `observed_no_action` result. A bounded retry may re-observe; it may not repeat an ambiguous submit.

## 6.2 Open-source reusable macro loop

The Mercor lane is a reusable open-source macro loop for any operator, not a promise that every operator will earn $10K. Each operator supplies their own private inputs and completes identity-bound steps; the shared code owns the repeatable orchestration.

### Operator onboarding (human once per account)

1. Provide a private resume/fact profile and approve the material baseline.
2. Authenticate the operator's own Google/Mercor account in an isolated browser.
3. Complete Mercor's required profile, work authorization, payment setup, interview, and assessment steps personally.
4. Connect the operator's own Gmail and Google Calendar through the existing Job Hunter integration.
5. Set the operator's target rate, weekly capacity, locales, role families, and hard exclusions.

### Resident loop (minimal human runtime)

- `acquisition`: hourly discovery, dedupe, fact matching, ready-to-submit queue, one bounded submit.
- `inbox`: 15-minute Gmail/Mercor reconciliation, selection/contract/rejection transitions.
- `calendar`: FreeBusy, idempotent interview event, reminders, prep pack delivery.
- `work`: track only authorized human/approved work; never impersonate an interview or violate task AI-use rules.
- `earnings`: reconcile Mercor Earnings/settled payouts and calculate verified monthly run-rate.
- `guardian`: leases, browser ownership, retries, duplicate-submit protection, and evidence integrity.
- `learning`: weekly role/rate/conversion analysis without fabricating success.

### Public/private boundary

Public repository: adapters, schemas, prompts, tests, launchd templates, provider policy, and redacted fixtures. Private runtime: resume, fact ledger, Google/Mercor session, Calendar IDs, Gmail thread IDs, payment details, application ledger, evidence, and earnings. A new operator gets a fresh private state root and never receives Dais's credentials or profile.

### $10K verification contract

The loop reports `$10K verified` only after the operator has actual settled payout evidence for three consecutive monthly cycles. It must never convert an offer, application, view, estimated rate, or unworked weekly cap into revenue. The expected-hours planner uses the contract's displayed rate and weekly cap; it does not promise a result.

The contract-level work harness is implemented in `apps/job-search-loop/job_search_loop/mercor_work_harness.py`, and its private append-only/idempotent event store is `mercor_work_store.py`. It rejects invalid work transitions, requires `authorization_policy=explicitly_allowed` for `authorized_work`, requires `acceptance_status=accepted` for `accepted`, routes human-bound work to `needs_human`, and accepts a revenue record only from a `paid_settled` event with a positive amount, settled status, payment ID, and evidence reference. Runtime adapters are connected; an actual authorized paid-work receipt remains external.

## 7. Calendar and minimal-human-glue flow

Mercor interview messages enter the existing Job Hunter inbox lane. Reuse `apps/job-search-loop/job_search_loop/interview_scheduling.py` and `calendar_sync.py`; do not create a Mercor-specific Calendar writer.

1. Classify the Gmail/Mercor message and require a clear role, source thread, timezone, start, and end.
2. Read Google Calendar FreeBusy for the primary calendar.
3. Choose the earliest explicitly offered slot that is free; never invent a time.
4. Create or update one idempotent private Calendar event keyed by the source thread and normalized start time, with 3-day and 1-day reminders.
5. Register the interview-prep job and deliver grounded prep windows through the existing inbox/prep loop.
6. Human glue remains only for Gmail/Calendar authorization, ambiguous scheduling, and attending the interview or taking a human-bound assessment. The system never impersonates the interview.

## 8. Current migration state

- Mercor skill/spec exist in the migration source and have been read back.
- Canonical Life Manager repo already owns `skills/job-hunter/`, `apps/job-search-loop/`, and `loops/job-hunter/`.
- The live Mercor profile is authenticated and the resume/profile fields were verified in the browser.
- Japanese evaluator application has the 14-minute `Domain Expert Interview` completed and the live application page now reads `3 of 3 steps done`, `Your application has been submitted!`, with review expected within four weeks. Submission used the user's explicit attestation of Japanese native fluency and 24 years living in Japan; do not resubmit while selection is pending.
- Related evaluator pages for Data analysis, General business strategy, Humanities/arts/culture, and Media/journalism/communications read `3 of 3 steps completed` with `Submit application` visible and reuse the completed Domain Expert Interview. Software/AI/IT/data was the strongest next candidate and is now submitted with a four-week review window.
- The resident model-led pass at `mercor-20260822-200153-55024` inspected the already-submitted Software listing, selected Data analysis / quantitative readouts, submitted it once, reopened the result, and read back the visible submitted state. The result is recorded in the private ledger and evidence paths under `~/.local/state/anicca/job-search/mercor/`; no `needs_human` or `blocked` result was returned.
- Live enablement is now installed: the dedicated browser transport `ai.anicca.job-search-mercor-browser` is `KeepAlive`/`RunAtLoad` with CDP `127.0.0.1:9334`, and the existing `ai.anicca.job-search-mercor` LaunchAgent is registered with a 3600-second wake interval. The first recovery pass blocked while the browser was down; the next pass `mercor-20260822-204000-83882` read back `browser-owner=ready`, inspected the existing Software application, and observed the Data quality / CRM operations listing without submitting because the private fact bank did not verify its 5+ years requirement. The pass exited 0, wrote fresh evidence, and left the ledger at three submitted applications.
- Operational meaning of 24/7 is a persistent browser transport plus an hourly bounded wake, not a busy loop that clicks continuously. Each wake may submit at most one grounded listing; `observed_no_action` is a successful safe pass when no listing is fully supported by verified facts.
- The first live resident pass after enablement inspected `Data quality / CRM operations Evaluator`, but did not submit because the private facts did not verify the listing's five-year requirement. This is the expected grounded behavior; adding a role-specific fact is only allowed when the operator can truthfully evidence it.
- Pass reporting is now wired through the existing idempotent Telegram outbox. The latest pass `mercor-20260822-213818-48917` report was delivered with Telegram `message_id=28848`; it contained the status, inspected job titles, and no-action reason without resume/profile secrets.
- Current cadence read-back: generic acquisition/daily every 3600 seconds, Mercor acquisition every 3600 seconds, inbox every 900 seconds (15 minutes), learning every Monday at 09:15 Asia/Tokyo, and the dedicated Mercor browser transport KeepAlive. There is no Mercor 30-minute or 5-minute submit loop.
- The contract-level work harness and private event store are green: they cover explicitly authorized work → acceptance → paid-settled → revenue, reject missing authorization/acceptance and pending/offer payment evidence, route AI-prohibited work to `needs_human`, and persist idempotent state events without profile/resume secrets. Inbox, Calendar artifact, Earnings capture/sync, and Telegram pass wiring are connected; an actual authorized paid-work receipt remains.
- Live Earnings capture is now automated after each Mercor pass. The latest E2E pass `mercor-20260822-221009-51760` read-only captured `https://work.mercor.com/earnings`, asserted `Your total earnings to date are $0.00`, `No payment history yet`, and `Once you receive your first payout, it will appear here`, and synced `not_observed` with zero events. Telegram ACK was `message_id=28881`; no payment or setup control was clicked.
- The live read-only Earnings page at `https://work.mercor.com/earnings` was opened in the dedicated Mercor profile. It read `Your total earnings to date are $0.00`, `No payment history yet`, and `Once you receive your first payout, it will appear here`. The private read-back is `status=not_observed`, `revenue_credited=false`, and `verified_monthly_run_rate_usd=null`; no application, offer, rate estimate, or `$0.00` placeholder is counted as earnings.
- Failure fixtures now cover page drift, stale/non-Mercor tabs, transient CDP failure, ambiguous submit read-back, recovery/reset/Google `はい` screens, and authoritative successful read-back. The guard fails closed and never retries an ambiguous submit or clicks recovery UI.
- A redacted two-operator fixture now proves separate operator IDs, state roots, application ledgers, evidence files, resume paths, and CDP endpoints; no cross-operator listing or evidence is visible.
- The reproducible release artifact passed extraction and clean-home install tests with a non-Dais redacted profile; the archive excludes private state, and the tracked public tree has no private-key/token credential matches.
- A production-scope reference scan found zero `profitable-claude` or legacy absolute-path dependencies in `apps/job-search-loop`, `loops/job-hunter`, `skills/mercor`, or the Mercor provider reference; canonical runtime/launchd/job-hunter contract tests pass 17/17.
- Deletion-gate read-back found `/Users/anicca/profitable-claude` is a separate 2.0G Git repository with uncommitted changes. The redacted read-only inventory at `~/.local/state/anicca/job-search/mercor/evidence/legacy-consumer-inventory-20260822.json` contains 463 jobs total and 15 enabled `profitable_claude` jobs (5 currently loaded); a broader plist path scan finds 38 files including disabled/legacy entries. No deletion, move, unload, or process termination was performed; removing it now would break unrelated active loops. The final destructive step remains pending migration or an explicit stop plan for those consumers.
- Mercor Summary currently resets after reload and is tracked as `summary_unpersisted`.

## 9. Migration acceptance gate

Do not delete or archive the migration source until all are true:

- Mercor skill, provider reference, and this spec are committed and pushed to `Daisuke134/life-manager`.
- `apps/job-search-loop` has the Mercor adapter, provider-specific browser owner, application dedupe, result schema, and tests.
- `loops/job-hunter` has one canonical hourly route; no second executor exists.
- A real read-only pass and one authorized form submission have fresh evidence and no duplicate application.
- Private runtime state is copied to `~/.local/state/anicca/job-search/mercor/` with mode `700/600`, and no secret or private resume is committed.
- A repository-wide reference scan shows no production Mercor path still depends on `profitable-claude`.
- Only after the above read-back may `profitable-claude` be archived/deleted as a separate destructive operation.

## 10. Atomic completion sequence (one active item at a time)

Only the first unchecked item is active. Finish its evidence and read-back before starting the next item. A `needs_human` result is a durable state, not permission to skip the next independent item.

1. [x] **Canonical source:** keep skill, spec, provider reference, and runtime state under the Life Manager boundary; no private secrets in Git.
2. [x] **Canary evidence:** complete and submit Japanese Evaluator plus Software/AI/IT/data Evaluator; store fresh submitted read-back and evidence.
3. [x] **Queue discovery:** read the four `3/3 + Submit` ready listings and exclude submitted application IDs.
4. [x] **Model contract:** add a model-led `mercor_pass` prompt and structured result schema to `runtime/agent-runner`; allowed results are `submitted`, `observed_no_action`, `needs_human`, and `blocked`.
5. [x] **Provider adapter:** implement Mercor discovery/application reconciliation in `apps/job-search-loop/`; keep Gmail, Calendar, ledger, and browser ownership in existing modules.
6. [x] **Submit guard:** implement exactly one deterministic irreversible wrapper requiring `3/3 + visible Submit + ledger dedupe`, followed by mandatory post-submit read-back.
7. [x] **Operator onboarding:** add private per-operator state roots and setup for resume, account, Calendar, payment, capacity, locale, role families, and exclusions.
8. [x] **Calendar fixture:** test Gmail classification → FreeBusy → idempotent Calendar event → prep reminders with a redacted Mercor fixture.
9. [x] **Resident cadence live enablement:** install the dedicated Mercor browser transport and the existing `ai.anicca.job-search-mercor` LaunchAgent, kickstart one real pass, and read back service state plus pass evidence. The browser transport is KeepAlive, the job wake interval is 3600 seconds, and the live pass exited 0 with a grounded `observed_no_action` result and no duplicate submit.
10. [x] **Dais full pass:** run one real model-led pass at `mercor-20260822-200153-55024`; submit Data analysis once, read back the submitted page, and persist the ledger/evidence result.
11. [x] **Earnings gate:** implement the settled-only parser/schema and perform a live Earnings read-back. The current account has no payment history, so the durable result is `not_observed` with no revenue credited; the first real settled payout remains an external runtime condition for a future `$10K verified` claim.
12. [x] **Failure fixtures:** test page drift, stale tab, transient failure, ambiguous submit, recovery/reset screen, and successful read-back.
13. [x] **Multi-operator test:** run a second redacted operator fixture with separate state, browser, ledger, and evidence; confirm no cross-operator data.
14. [x] **Open-source release:** secret scan, fresh-install test, setup/runbook, provider docs, and one non-Dais fixture pass.
15. [x] **Reference cleanup:** remove all production references to `profitable-claude` and confirm the canonical Life Manager runtime still passes.
16. [x] **Pass reporting:** send every Mercor pass status, inspected job, submit/no-action reason through the idempotent Telegram outbox and record the ACK/evidence without leaking private profile or resume data.
17. [x] **Work-harness contract/store:** enforce submitted → selected → contracted → authorized_work → accepted → paid_settled → revenue_recorded transitions, with fail-closed settlement evidence, `needs_human` routing, private append-only events, and idempotent event IDs.
18. [x] **Work-harness Inbox sync:** accept optional strict `mercor_work_events` from the Inbox result, persist transitions in the private idempotent event store, and emit one Telegram receipt per event.
19. [ ] **Work-harness Calendar/Earnings wiring:** connect Calendar event artifacts and explicit authorization/acceptance evidence to the durable private work state. Calendar artifact sync, strict authorization/acceptance gates, and live Earnings capture/settled-snapshot sync are implemented; an actual paid-work receipt remains.
20. [ ] **Deletion gate:** only after every prior read-back succeeds, migrate or explicitly stop the 15 enabled old-repo jobs (and reconcile the broader 38-file plist scan), then archive/delete `/Users/anicca/profitable-claude` as a separate destructive operation. Current status: blocked by active consumers and dirty old-repo worktree; no destructive action was taken.

### 10.1 Remaining operational TODO after the live loop install

These are runtime milestones, not additional submit clicks:

1. **Selection/inbox reconciliation:** let the 15-minute inbox lane classify Mercor selection, rejection, and contract messages; persist each transition and evidence.
2. **Contract/calendar handoff:** for an explicit interview offer, use FreeBusy and the existing idempotent Calendar/prep flow; the user attends any human-bound interview or assessment.
3. **Authorized work:** only after a contract explicitly permits the tool/model, track the actual completed work and acceptance; otherwise route the task to `needs_human`.
4. **Settled payout:** read back the first real paid/settled Mercor row and calculate the trailing-30-day verified amount; do not count pending or estimated balances.
5. **Revenue proof:** require three consecutive settled monthly cycles before reporting `$10K verified`; until then the revenue ledger remains `not_observed` when no payout evidence exists.
6. **Legacy cleanup:** separately migrate/stop the old-repo consumers before deleting `profitable-claude`; this is not a reason to disable the Mercor loop.
