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
- The live read-only Earnings page at `https://work.mercor.com/earnings` was opened in the dedicated Mercor profile. It read `Your total earnings to date are $0.00`, `No payment history yet`, and `Once you receive your first payout, it will appear here`. The private read-back is `status=not_observed`, `revenue_credited=false`, and `verified_monthly_run_rate_usd=null`; no application, offer, rate estimate, or `$0.00` placeholder is counted as earnings.
- Failure fixtures now cover page drift, stale/non-Mercor tabs, transient CDP failure, ambiguous submit read-back, recovery/reset/Google `はい` screens, and authoritative successful read-back. The guard fails closed and never retries an ambiguous submit or clicks recovery UI.
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
9. [x] **Resident cadence:** wire acquisition, inbox, Calendar, earnings, guardian, and learning into the existing Job Hunter launchd route; scheduler and canonical-route tests pass.
10. [x] **Dais full pass:** run one real model-led pass at `mercor-20260822-200153-55024`; submit Data analysis once, read back the submitted page, and persist the ledger/evidence result.
11. [x] **Earnings gate:** implement the settled-only parser/schema and perform a live Earnings read-back. The current account has no payment history, so the durable result is `not_observed` with no revenue credited; the first real settled payout remains an external runtime condition for a future `$10K verified` claim.
12. [x] **Failure fixtures:** test page drift, stale tab, transient failure, ambiguous submit, recovery/reset screen, and successful read-back.
13. [ ] **Multi-operator test:** run a second redacted operator fixture with separate state, browser, ledger, and evidence; confirm no cross-operator data.
14. [ ] **Open-source release:** secret scan, fresh-install test, setup/runbook, provider docs, and one non-Dais fixture pass.
15. [ ] **Reference cleanup:** remove all production references to `profitable-claude` and confirm the canonical Life Manager runtime still passes.
16. [ ] **Deletion gate:** only after every prior read-back succeeds, obtain the final check-in and archive/delete the old repository as a separate destructive operation.
