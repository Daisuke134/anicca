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
- Japanese evaluator application is `2_of_3` in the old card projection, but the 14-minute `Domain Expert Interview` was completed; the live application card now reads `Ready to submit`. The listing still requires 5+ years of relevant Japanese language/cultural-fluency professional experience, which is not yet an exact verified fact.
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

## 10. Atomic TODO (ordered)

1. [x] Copy the Mercor provider policy and skill facade into this repository.
2. [ ] Add the Mercor provider adapter to the existing job-search runtime; keep ATS, Gmail, Calendar, ledger, and browser side effects in their existing owners.
3. [ ] Route all locales and role families through one material-variant/fact gate; remove any Japanese-only filter.
4. [ ] Resolve the Japanese evaluator's 5+ years relevant-experience fact gate; submit only if the requirement is grounded, otherwise record `needs_human`/ineligible.
5. [ ] Add a Mercor fixture to the existing Gmail→FreeBusy→Calendar idempotency tests.
6. [ ] Fix or explicitly quarantine the Summary persistence gap.
7. [ ] Run one isolated Mercor pass through the existing Job Hunter launchd route.
8. [ ] Verify application/earnings evidence, Calendar read-back, prep delivery, and Telegram reporting.
9. [ ] Remove all production references to `profitable-claude`.
10. [ ] Obtain a final deletion check-in before deleting the old repository checkout/history.
