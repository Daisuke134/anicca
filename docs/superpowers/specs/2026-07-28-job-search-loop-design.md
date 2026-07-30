# Autonomous Job Search Loop Design

**Date:** 2026-07-28
**Last updated:** 2026-07-30
**Owner:** Daisuke Narita
**Status:** Local acquisition and inbox loops are live from the canonical Life
Manager checkout; persistent learning orchestration, operations guardianship and
the Life Manager Career surface remain in progress.
**Done when:** `Daisuke134/life-manager` is the only versioned source and the
resident system can discover, qualify, tailor and submit up to two truthful eligible
applications per Japan day; reconcile every later Gmail message; manage scheduling,
assessments, interview preparation, follow-up, offers and final outcomes; report
every material event at most once; heal safe operational failures; and promote or
roll back only verified evidence-backed strategy changes without routine human
prompting.

## 1. Outcome

Build a local-first job application operating system around the useful parts of
`MadsLorentzen/ai-job-search`, without treating job descriptions as instructions and
without fabricating candidate claims.

The loop optimizes for interviews, not raw submission count:

| Objective | Rule |
|---|---|
| Daily application target | 2 unique, eligible, high-fit applications per Japan day |
| Location | Tokyo on-site/hybrid, Japan-remote, or global remote that accepts Japan-based workers |
| Compensation | Prefer JPY 7M–10M+; hard reject known compensation below JPY 5.5M |
| Role families | Applied AI/agent/GenAI engineering; AI product and technical program management; solutions/consulting; AI business development and partnerships; technical account management, customer success and sales engineering; agentic fintech/crypto/consumer AI |
| Hard exclusions | Citizenship or clearance requirements the candidate cannot meet; relocation-only roles outside Japan; already-applied roles; material skill fabrication |
| Truthful zero | If fewer than two eligible jobs exist, submit the eligible count and report the shortfall; do not lower hard filters or claim success |

### 1.1 `JOB-CANONICAL-MERGE-1`

This completed canonicalization deliverable changed ownership and runtime wiring,
not job-selection policy or cloud architecture.

| Contract | Required state |
|---|---|
| Canonical repository | `https://github.com/Daisuke134/life-manager` |
| Legacy implementation provenance | `Daisuke134/anicca-products` branch `feature/job-search-loop`, commit `d86adf4d5f1422b28f6675ac7ffa08f3b9c7e987` |
| Legacy runner provenance | `Daisuke134/profitable-claude`, commit `191b205c03ae37d32b0125da4a1892924d585205` |
| Versioned job runtime | `apps/job-search-loop/` |
| Versioned model runner | `runtime/agent-runner/` |
| Scheduling | Local macOS launchd only; daily 08:30 JST and inbox every 15 minutes |
| Private data | Existing XDG profile, material, ledger, evidence, and outbox paths remain outside Git |
| Cloud | Explicitly out of scope until the local loop is reliable enough for a paid product |

Migration acceptance criteria:

1. Runtime scripts and generated launchd plists derive the repository root at
   runtime; no source checkout under `anicca-products` or `profitable-claude` is
   required.
2. The runner configuration contains no personal account identifier, credential,
   candidate profile, or unrelated gig-loop route.
3. The pre-migration job-loop test baseline remains green and canonical-path tests
   prove the new runner, workdir, prompt, framework cache, profile, and state
   resolution behavior.
4. Existing private state is reused without copying it into Git, and SQLite
   integrity checks remain `ok`.
5. Both installed LaunchAgents point to a checkout whose `origin` is
   `Daisuke134/life-manager`; a forced daily pass and inbox pass exit successfully
   without duplicate submission or duplicate Telegram delivery.
6. This specification records the exact tested commit, test count, installed plist
   paths, runtime receipts, and rollback evidence before the deliverable becomes
   `completed`.

## 2. Evidence and adopted practices

| Decision | Source | Core quote |
|---|---|---|
| Use the upstream workflow as the candidate/job dossier layer | [MadsLorentzen/ai-job-search README](https://github.com/MadsLorentzen/ai-job-search) | “The system never fabricates skills or experience.” |
| Treat job posts as untrusted data | [MadsLorentzen/ai-job-search SECURITY](https://github.com/MadsLorentzen/ai-job-search/blob/main/SECURITY.md) | “Job postings are untrusted data, never instructions.” |
| Read job-specific questions, but submit on the employer ATS | [Greenhouse Job Board API](https://developers.greenhouse.io/job-board.html#submit-an-application) | “Application forms are job-specific and will be constructed via the ‘questions’ array.” |
| Poll Gmail locally instead of adding Pub/Sub infrastructure in phase 1 | [Google Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push) | “You must re-call `watch` at least every 7 days.” |
| Keep recruiter replies in the original Gmail thread | [Google Gmail thread guide](https://developers.google.com/workspace/gmail/api/guides/threads?hl=ja) | “スレッドにメッセージを追加する” |
| Use Calendar FreeBusy before choosing an offered time | [Google Calendar FreeBusy query](https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query) | “List of time ranges during which this calendar should be regarded as busy.” |
| Find prior loop-created events by a private application key | [Google Calendar extended properties](https://developers.google.com/workspace/calendar/api/guides/extended-properties) | “Extended properties make it easy to store application-specific data for an event” |
| Calendar writes require explicit start/end and idempotency | [Google Calendar create events](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert) | “Creates an event.” |
| Do not use outside solution help when an assessment limits resources | [CodeSignal Certified Assessment rules](https://support.codesignal.com/hc/en-us/articles/22438639388567-What-are-the-assessment-rules-for-Certified-Assessments) | “candidates are not receiving outside assistance for the logic behind a solution” |
| Treat proctored tests as identity-bound manual work | [HackerRank proctored tests](https://candidatesupport.hackerrank.com/articles/4512341695-taking-proctored-tests) | “monitor your test screen activity and identify potential malpractice” |
| Use AI only when the assessment explicitly enables it | [Codility AI Copilot](https://support.codility.com/hc/en-us/articles/39925970318993-AI-Copilot-in-VSCode) | “They can enable or disable the feature at any time” |
| Scope the MUFG claim to contribution, not sole ownership | [Salesforce Japan MUFG announcement](https://www.salesforce.com/jp/news/press-releases/2026/03/25/mufg-customer-news-3/) | “2025年8月に日本で初めて同ソリューションを選定” |
| Link the public ICLR report as proof of communication skill | [MUIT ICLR 2026 report](https://www.youtube.com/watch?v=biHAQ6aSQuc) | “International Conference on Learning Representations 2026参加レポート 後編” |
| Use the correct public product portfolio URL | [Dais’s products](https://aniccaai.com/dais) | “Dais’s products” |
| Treat customer-facing AI roles as technical-business targets | [Productboard AI Customer Success Manager](https://www.productboard.com/careers/open-positions/ai-customer-success-manager/am9icG9zdDqqRtrsE0AKy8Jnu_ClB4B2/) | “work directly with product and engineering teams” |
| Grade externally verified outcomes, not an agent's narration | [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | “the outcome is whether a reservation exists in the environment’s SQL database.” |
| Continuously connect evaluations to traces | [Microsoft Foundry — Continuous agent evaluation](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/continuous-evaluation-agents) | “Evaluations are also connected to traces” for “detailed debugging and root cause analysis.” |
| Test both internal health and user-visible behavior | [Google SRE — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) | Black-box monitoring is “Testing externally visible behavior as a user would see it.” |
| Keep operational alerts low-noise | [Google SRE — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) | “Effective alerting systems have good signal and very low noise.” |
| Govern, map, measure and manage AI risk as one lifecycle | [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) | Suggestions align to the four AI RMF functions “Govern, Map, Measure, Manage.” |

The Greenhouse application submission API is employer-authenticated. The applicant
loop therefore uses public APIs/pages for discovery and question inspection, then
performs the actual side effect through the company-hosted ATS form in an isolated
browser profile.

## 3. Candidate truth ledger

The private profile is the sole source of candidate claims. Every resume bullet,
cover-letter claim, and form answer stores a `fact_id` reference. Missing facts remain
missing; the model may improve wording but may not infer dates, headcount, ownership,
compensation, work authorization, or quantitative impact.

| Fact ID | Approved claim | Evidence class |
|---|---|---|
| `muit_role_2025` | MUIT / Mitsubishi UFJ Information Technology, 2025-04–present | user statement |
| `muit_agent_crm` | Works on deploying agents into a bank CRM environment | user statement |
| `muit_genie_logs` | Automated analysis of agent output logs with Databricks Genie Code | user statement |
| `muit_rm_summary` | Prompt-tuned agents that summarize company information for relationship managers | user statement |
| `mufg_agentforce` | Contributed to MUFG’s Japan-first Agentforce for Financial Services deployment; never claim sole ownership | user statement + Salesforce public announcement |
| `iclr_2026` | Attended ICLR 2026 in Rio, shared learnings internally, and appeared in the public MUIT paper-report video | user statement + public video |
| `naist_2024_2026` | NAIST, 2024-04–2026-04; EEG and machine-learning research on mind-wandering detection | user statement + existing resumes |
| `atr_research` | Conducted and presented mind-wandering research at ATR | user statement + existing resumes |
| `agent_club` | Founded a weekly lab/graduate-school session on Claude Code, Codex, Cursor, and AI-agent research workflows | user statement |
| `anicca_consumer` | Built Swift/iOS consumer products and worked on consumer growth; Anicca reached USD 100 MRR | user statement; metric is candidate-asserted |
| `life_manager` | Builds Life Manager, a consumer agent for financial, physical, and mental health workflows | user statement + public product page |
| `a10_marketing` | Managed a JPY 20M campaign budget, reduced CPA by 10%, and achieved record paid acquisition | existing English resume |
| `languages` | TOEFL iBT 96, Duolingo English Test 140, Spanish DELE B1 | existing English resume |

Private contact fields, legal answers, phone number, address, work authorization,
demographics, and generated application materials are never committed. Runtime paths:

```text
~/.config/anicca/job-search/profile.json
~/.local/state/anicca/job-search/
~/.local/share/anicca/job-search/materials/
```

## 4. Architecture

```text
launchd
  ├─ daily-pass (08:30 JST, catch-up on wake)
  │    ├─ discover: company ATS + public search
  │    ├─ normalize/dedupe
  │    ├─ qualify and rank
  │    ├─ detect official posting language
  │    │    ├─ Japanese → Japanese AI resume
  │    │    └─ English → engineering/business English resume
  │    ├─ tailor from truth ledger
  │    ├─ browser claim/fence/submit
  │    ├─ Telegram exact submitted-resume PDF
  │    └─ Telegram daily report
  ├─ inbox-pass (every 15 minutes)
  │    ├─ Gmail reconcile
  │    ├─ stage/outcome transition
  │    ├─ Calendar idempotent insert/update
  │    ├─ 3-day and 1-day prep packs
  │    └─ Telegram event report
  ├─ learning-pass (weekly, only with sufficient resolved outcomes)
  │    ├─ attribute outcomes to one strategy generation
  │    ├─ replay safety suite
  │    ├─ compare one changed variable
  │    └─ promote, keep inconclusive, or roll back
  └─ guardian-pass (frequent, deterministic)
       ├─ scheduler/run freshness and integrity
       ├─ bounded pre-side-effect recovery
       ├─ provider/browser fallback health
       └─ deduplicated remediation or Telegram alert

immutable evidence → materialized SQLite state → verifier → summary.v2
       ↑                                                    ↓
       └──────── strategy generation / rollback ─ Life Manager Career
```

### 4.1 Repository and runtime split

| Area | Location | Responsibility |
|---|---|---|
| Versioned implementation | `apps/job-search-loop/` | deterministic core, adapters, prompts, schemas, tests, launchd templates |
| Versioned model runner | `runtime/agent-runner/` | provider routing, schema validation, bounded fallback, token budget |
| Upstream framework | pinned fork/checkout under `~/.local/share/anicca/job-search/framework` | candidate profile, job dossier, tailoring conventions |
| Private runtime state | `~/.local/state/anicca/job-search` | ledger, traces, evidence, locks, outbox |
| Private materials | `~/.local/share/anicca/job-search/materials` | master resume, tailored resumes, cover letters, prep packs |
| Current local projection | private `summary.v1.json` | application counts and Ashby/Workday proof progress |
| Life Manager bridge | versioned `summary.v2.json` schema | read-only career timeline, action queue, learning and operational health; no browser side-effect ownership |

### 4.2 Model routing

Deterministic code owns filtering, idempotency, transitions, and side effects.
The canonical `runtime/agent-runner` owns model execution:

| Task | Route |
|---|---|
| Job extraction, scoring explanation, tailoring | `composition-agent` → GPT-5.6 Terra medium, Claude fallback |
| Repeated inbox classification | `repeatable-agent` → GPT-5.6 Luna medium, Claude fallback |
| Browser ATS completion | `browser-lane-agent` → GPT-5.6 Terra medium, Claude fallback |
| Weekly strategy experiment | `high-value-agent` → GPT-5.6 Luna medium, Claude fallback |

All model outputs must validate against JSON Schema. A valid but schema-invalid response
fails closed and does not silently switch providers.

### 4.3 Browser policy

- Use a dedicated CloakBrowser profile and CDP port, separate from gig work.
- Search engines and LinkedIn may provide leads; submissions occur on the employer ATS.
- Never bypass CAPTCHA, misrepresent identity, invent form answers, or accept legal terms
  that are not ordinary application acknowledgements.
- Before a submit click, persist an immutable intent containing canonical job URL,
  company, title, material hashes, answer hashes, and a fencing token.
- After the click, record one of `submitted`, `submit_unknown`, or `not_submitted`.
- `submit_unknown` is never automatically retried. Inbox confirmation or authoritative
  ATS reread may resolve it.

### 4.4 ATS resilience contract

The first ATS resilience increment is `JOB-ATS-RESILIENCE-10A`. It fixes the
observed failure class where an Ashby page committed and rendered its application
surface, but waiting for `domcontentloaded` timed out and the loop stopped before
inspecting fields. A read-only probe against the existing CDP owner confirmed that
both the BJAK Ashby application and a Tokyo Workday posting expose their required
user-facing controls after navigation commit.

| Decision | Source | Core quote |
|---|---|---|
| Navigate to commit, then wait for a semantic application surface | [Playwright actionability](https://playwright.dev/docs/actionability) | “It auto-waits for all the relevant checks to pass and only then performs the requested action.” |
| Prefer role, label, and visible-text evidence over generated CSS classes | [Playwright locators](https://playwright.dev/docs/locators) | “To make tests resilient, we recommend prioritizing user-facing attributes and explicit contracts such as page.getByRole().” |
| Inspect every attached frame while keeping main-frame controls first | [Playwright frames](https://playwright.dev/docs/frames) | “Each page has a main frame and page-level interactions … are assumed to operate in the main frame.” |

Three approaches were considered:

| Approach | Decision | Reason |
|---|---|---|
| Deterministic ATS classifier + snapshot evaluator + replay fixtures | Adopt | Converts browser observations into a testable contract without owning the submit side effect |
| Prompt-only navigation advice | Reject | Cannot prove the regression would be caught or that the agent used the advice |
| Fully hard-coded form filler per ATS | Defer | Brittle before legal answers are complete and before real per-adapter fixtures establish the stable surface |

`job_search_loop.ats` owns only provider detection and pre-submit readiness. It
accepts a versioned, redacted snapshot containing navigation-commit state, frame
URLs, and user-facing control metadata. It returns:

```text
provider: ashby | workday | generic
ready: boolean
claim_ready: boolean
surface: ashby_application | workday_job | workday_apply_choice |
         workday_account_create | workday_application |
         generic_application | none
frame_index: integer | null
wait_until: commit
blockers: string[]
```

The evaluator never clicks, fills, uploads, claims a ledger slot, or interprets a
CAPTCHA. An invisible reCAPTCHA frame is recorded but is not itself proof of a
visible challenge. The browser executor must persist the snapshot mode 0600, run the
evaluator, and continue only when `ready=true`. `Ledger.claim_submission` requires
the exact snapshot path and SHA-256, rereads the file, verifies the hash, reruns the
production evaluator, and confirms that its canonical URL matches the application.
The model cannot satisfy this boundary by merely claiming readiness in its output.
A visible CAPTCHA or identity challenge still follows the existing fail-closed
policy.

Ashby readiness requires the main-frame application controls, including email,
resume upload, and `Submit Application`. Workday navigation readiness accepts either
a job surface with an `Apply` control or the post-click application surface, but
`workday_job` is not claim-ready: the executor must click the ordinary Apply
navigation control and recapture the application form first. A committed page with
no recognized surface remains `not_submitted`; a click with ambiguous outcome
remains `submit_unknown`.

`JOB-ATS-RESILIENCE-10A` is complete when:

1. sanitized Ashby and Workday snapshots replay through the same production
   evaluator;
2. the former Ashby timeout shape (`navigation_committed=true`) evaluates ready
   without requiring `domcontentloaded`;
3. missing controls and malformed snapshots fail closed;
4. a missing, changed, non-ready, or wrong-job snapshot cannot claim a submission;
5. the daily browser prompt passes the verified snapshot path/hash to the claim;
6. the full job-loop suite remains green.

Order 10 remains `in_progress` after 10A. It becomes `completed` only after one real,
confirmed application per adapter is recorded without inferred legal answers.

### 4.5 Workday surface progression

`JOB-ATS-RESILIENCE-10B` separates browser progress from permission to reserve a
submission slot. A real read-only flow on the public CrowdStrike Workday site exposed
the following sequence:

```text
workday_job
  → Apply
  → workday_apply_choice
  → Apply Manually
  → workday_account_create
  → authenticated application steps
  → workday_application
```

| Decision | Source | Core quote |
|---|---|---|
| Model the Apply choice as a separate surface | [CrowdStrike Workday application](https://crowdstrike.wd5.myworkdayjobs.com/crowdstrikecareers/job/Japan---Tokyo/Regional-Sales-Engineer---AIDR_R29264-1) | “Autofill with Resume” / “Apply Manually” / “Use My Last Application” |
| Model account creation as a separate, non-claimable surface | [CrowdStrike Workday Create Account](https://crowdstrike.wd5.myworkdayjobs.com/en-US/crowdstrikecareers/job/Japan---Tokyo/Regional-Sales-Engineer---AIDR_R29264-1/apply/applyManually) | “Email Address” / “Password” / “Verify New Password” / “Create Account” |
| Keep actions semantic and auto-waited | [Playwright locators](https://playwright.dev/docs/locators) | “We recommend prioritizing role locators to locate elements, as it is the closest way to how users and assistive technology perceive the page.” |

`evaluate_snapshot` adds `claim_ready`. Its meaning is independent of `ready`:

| Surface | `ready` | `claim_ready` | Next action |
|---|---:|---:|---|
| `workday_job` | true | false | Click `Apply` |
| `workday_apply_choice` | true | false | Prefer `Apply Manually`; do not upload before material routing |
| `workday_account_create` | true | false | Use only an approved private identity/credential path |
| `workday_sign_in` | true | false | Use the existing private account; never expose credentials |
| `workday_application` | true | true | Claim only on the final submit-bearing application surface |
| `ashby_application` / `generic_application` | true | true | Existing claim rules apply |
| `none` | false | false | Stop before claim |

The Ledger accepts only `claim_ready=true`. It does not encode Workday-specific
surface names; the evaluator owns that policy. This prevents future navigation-only
surfaces from accidentally consuming quota.

10B does not create a Workday account or answer application questions. The private
profile currently contains no verified nationality, citizenship, visa, or work
authorization scalar, so account/application side effects remain owned by the real
loop after private facts exist. No legal value is inferred from name, residence,
language, or employer.

`JOB-ATS-RESILIENCE-10B` is complete when:

1. sanitized real-shape Workday Apply-choice and Create-Account fixtures replay;
2. both surfaces return `ready=true`, `claim_ready=false`;
3. Ashby/generic application fixtures return `claim_ready=true`;
4. Ledger rejects every ready-but-not-claimable surface without allocating a slot;
5. the daily prompt follows the Workday progression and never treats account creation
   as an application submission;
6. a read-only existing-CDP replay reaches Create Account with zero input, account
   creation, upload, claim, or submit side effects;
7. all tests and CI pass.

Order 10 remains `in_progress` after 10B. The real confirmed-application gate is
unchanged.

### 4.5.1 Durable ATS progress projection

`JOB-ATS-RESILIENCE-10I` makes the unchanged real-application gate observable.
The ledger stays provider-neutral: `summary.v1.json` derives `ashby`, `workday`, or
`generic` from each canonical application URL at read time. Top-level counts use
current lifecycle states; per-adapter progress uses the durable submission outcome
when one exists, so a confirmed application remains confirmed after it advances to
interview or another later state. The projection exposes no company, title, URL,
email, or candidate facts.

| Decision | Source | Core quote |
|---|---|---|
| Replace the projection atomically from a same-directory temporary file | [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace) | “the renaming will be an atomic operation” |
| Aggregate persisted rows rather than model narration | [SQLite SELECT](https://www.sqlite.org/lang_select.html) | “A simple SELECT statement is an aggregate query if it contains either a GROUP BY clause or one or more aggregate functions” |
| Keep the read contract object-shaped and versioned | [JSON Schema object reference](https://json-schema.org/understanding-json-schema/reference/object) | “Objects are the mapping type in JSON. They map ‘keys’ to ‘values’.” |

Every terminal daily path refreshes
`~/.local/state/anicca/job-search/summary.v1.json` with mode `0600`. Its
`ats_progress.complete` is true only when both required adapters, Ashby and Workday,
have at least one current `submitted` application. `submit_unknown` is reported but
never counts as confirmed. Order 10 therefore remains `in_progress` while external
real-application evidence is missing, but the remaining gap is now machine-readable
for the local loop and the future Life Manager Career organ.

10I merged in PR #1346 (`96adde721`, CI `30460492034`) with 168 job-loop
and 9 runner tests. The existing launchd daily run advanced 9→10 and exited 0;
Telegram report `4429` truthfully reported zero submissions and two pre-submit
blocks without inferring legal answers. The live mode-`0600` projection contains
2 `submitted`, 1 `submit_unknown`, and 2 `not_submitted`; both required adapter
confirmations remain false because the two confirmed applications are generic ATS
hosts. The live run also exposed a separate budget defect: a 24,576-token admission
reservation allowed a 93,420-token provider-reported charge, taking the daily total
from 231,212 to 324,632 against a 262,144 configured limit. The next pass blocks,
but strict pre-spend enforcement remains a numbered follow-up rather than being
misreported as solved by 10I.

### 4.5.2 Conservative pre-spend budget admission

`JOB-BUDGET-HARD-CAP-10J` fixes the budget defect observed by the 10I live pass.
The ledger already blocks when `daily_consumed + reservation > daily_limit` and
truthfully replaces a reservation with provider-reported usage at settlement. The
defect was the caller's 24,576-token task estimate: it was not an upper bound for a
browser pass whose configured limit was 98,304.

| Decision | Source | Core quote |
|---|---|---|
| Use the live overrun as the regression fixture | [`2026-07-29-order10i-live-summary.json`](../../evidence/job-search-loop/2026-07-29-order10i-live-summary.json) | “Admission used a reservation smaller than the possible provider-reported charge” |
| Reserve before the external side effect | [AlgoPay SDK](https://github.com/Algodev-Studio/algopay-sdk/blob/fd95a38b156ad1fcb6eda31c02896dd66498503a/python/src/algopay/client.py) | `reservation_tokens = await guards_chain.reserve(context)` |
| Treat a reservation as secured capacity | [Stripe manual capture](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method) | “決済のオーソリにより、顧客の支払い方法で金額が確保されて保証されます。” |

When token budgeting is enabled, each provider attempt now reserves the full
configured per-pass limit before launch. The smaller task-class reservation remains
an unbudgeted planning estimate. Settlement still replaces the hold with actual
provider-reported charge, but a later fallback cannot launch unless the remaining
pass and daily pools can again cover the full pass maximum. This intentionally
prefers a hard pre-spend stop over an unbounded fallback.

10J merged in PR #1350 (`e3bc44685`, CI `30462362148`) with 168 job-loop
and 10 runner tests plus the OSS boundary. The post-merge production LaunchAgent
advanced daily run 10→11 with exit 0 and stopped before provider selection:
`attempt_count=0`, no attempt artifacts, and no settlement or usage row. The
budget ledger added exactly one blocked 98,304-token reservation against the
already-consumed 324,632 tokens. Application counts remained 2 submitted /
1 submit-unknown / 2 not-submitted, both SQLite integrity checks stayed `ok`,
and the mode-0600 projection remained current. This closes the strict
pre-spend defect; it does not satisfy Order 10's real confirmed Ashby and
Workday application gate.

### 4.5.3 Late authoritative confirmation reconciliation

`JOB-CONFIRMATION-RECONCILE-10K` closes a different uncertainty gap without
weakening the no-retry fence. A submit click whose immediate browser result is
ambiguous remains `submit_unknown` and is never clicked again. The 15-minute inbox
driver instead treats a later official application-received email as an asynchronous
completion event.

| Decision | Source | Core quote |
|---|---|---|
| Reconcile from a later completion event instead of repeating the client action | [Stripe — Verify payment status](https://docs.stripe.com/payments/payment-intents/verifying-status) | “クライアント側でフルフィルメントを開始するのではなく、Webhook を使用して `payment_intent.succeeded` イベントを監視し、その完了を非同期で処理します。” |
| Use the Gmail message ID as the dedupe key | [Gmail API — Message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages) | “The immutable ID of the message.” |
| Make receipt insertion and every state mutation one transaction | [AWS Builders' Library — Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | “the process that combines recording the idempotent token and all mutating operations related to servicing the request must meet the properties for an atomic, consistent, isolated, and durable (ACID) operation.” |

Before any inbox model call, the deterministic reconciler searches recent explicit
confirmation subjects and reads candidate threads with untrusted-content wrapping
and URL removal. It accepts only a message after the submit intent whose confirmation
text, company, role and official ATS sender-domain family match exactly one uncertain
application. In one SQLite transaction it inserts the immutable-message receipt and
promotes the application, intent, exact attempt and daily slot to `submitted`, then
appends the transition event. A duplicate receipt is a no-op; a spoof, old message,
missing ground or multi-match changes neither ledger nor seen checkpoint.

The inbox driver immediately refreshes `summary.v1.json` and invokes the existing
content-addressed resume delivery, so a reconciled application sends the exact
recorded PDF to Telegram once. Six focused tests plus the full 174 job-loop and
10 runner suites pass. A real-Gmail shadow run against an SQLite backup checked one
broad confirmation candidate, reconciled zero, reported one exact-match block, and
left the production-shaped 2 submitted / 1 submit-unknown / 2 not-submitted counts
unchanged. No BJAK receipt currently exists, so Order 10 remains `in_progress`
until the external receipt or another real confirmed Ashby application arrives.

10K merged in PR #1352 (`852d18a14`, CI `30464923726`). The post-merge
production inbox LaunchAgent advanced run 24→25 with exit 0. It checked one broad
Gmail candidate, made zero promotions, inserted zero confirmation receipts,
launched no provider and sent no Telegram document. The seen checkpoint and
12-row Telegram outbox were byte-time unchanged; application counts remained
2 submitted / 1 submit-unknown / 2 not-submitted. The mode-0600 projection
refreshed to 2026-07-30 and both ledger/preparation integrity checks remained
`ok`. This proves fail-closed production wiring but does not fabricate the still
absent BJAK receipt.

### 4.5.4 Message-level Gmail checkpoint

`JOB-INBOX-MESSAGE-CHECKPOINT-10L` fixes a follow-up loss mode in the recurring
inbox. The original checkpoint stored a processed Gmail thread ID forever, but a
thread is a conversation container and later recruiter, assessment or interview
messages retain that same thread ID.

| Decision | Source | Core quote |
|---|---|---|
| Dedupe the immutable message rather than its conversation | [Gmail API — Message](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages) | “The immutable ID of the message.” |
| Expand a thread into its individual members | [Gmail API — Thread](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads) | “A collection of messages representing a conversation.” / “The list of messages in the thread.” |
| Bootstrap current state before consuming later deltas | [Gmail API — Synchronize clients](https://developers.google.com/workspace/gmail/api/guides/sync) | “Full synchronization is required the first time” and partial synchronization returns history newer than `startHistoryId`. |

The deterministic scan now expands each bounded recruiting thread through sanitized,
untrusted-content-wrapped Gmail reads. Candidate evidence contains only immutable
message/thread mappings. A result may acknowledge only message IDs that are an exact
subset of that scan, and its thread IDs must equal the unique mapped threads in
first-message order. Omitted messages retry; a later message in an acknowledged
thread remains visible.

The private v1 checkpoint migrates using its existing file mtime. Messages in the
three legacy threads at or before that boundary become bootstrap message IDs while
the legacy boundary remains recorded for old messages not present in the 14-day
window. A real-Gmail shadow full sync produced 3 bootstrap messages, 0 candidates,
and a mode-0600 v2 checkpoint with all three legacy boundaries preserved. Production
state was not mutated. The full 176 job-loop and 10 runner suites, OSS boundary,
PII scan and shell syntax pass.

10L merged in PR #1355 (`162b4750c`, CI `30466877218`), where all seven
reported checks passed. The production rollout initially remained on canonical
checkout `b0ea0f458` and checkpoint v1. The exact failed provider attempt then
proved prompt transport was already correct and isolated the remaining blocker:
Codex returned HTTP 400 `invalid_json_schema` because `uniqueItems` was not
permitted for `processed_thread_ids`. An older global stderr line about
`--prompt-stdin` was unrelated to that attempt.

After 10M merged, the canonical checkout fast-forwarded to descendant
`384d03a39`. A forced existing Inbox LaunchAgent run advanced its counter to 5
and exited 0. It atomically migrated the private mode-0600 production checkpoint
from v1 to v2 with 3 immutable message IDs and all 3 legacy thread boundaries,
found 0 new candidates and replayed 0 historical messages. The application
ledger remained integrity `ok` at 2 submitted / 1 submit-unknown /
2 not-submitted, and interview-preparation integrity remained `ok`.

10L live closeout is complete only when all of the following are evidenced:

1. the canonical runtime checkout includes `162b4750c` or a descendant;
2. Codex receives a supported Structured Outputs schema while deterministic
   validation retains the stricter local contract;
3. a forced real inbox run exits 0 without replaying the three legacy messages;
4. production state atomically migrates to v2 with the three bootstrap message IDs;
5. a later message in any already-seen thread remains eligible for processing;
6. ledger and interview-preparation integrity remain `ok`, and the closeout
   evidence is merged into this specification.

Conditions 1–4 and 6 are now complete. Condition 5 is implemented and covered by
deterministic tests, but remains `implemented_waiting_external_e2e` until a real
later recruiter message arrives in one of the already-seen production threads.
That external wait does not block the independent confirmed-application work in
Order 10.

### 4.5.5 Provider schema compatibility

`JOB-CODEX-SCHEMA-COMPAT-10M` closes the live 10L blocker without weakening
deterministic safety. OpenAI Structured Outputs accepts a documented subset of
JSON Schema. Its supported array constraints are `minItems` and `maxItems`; a
strict request with an unsupported schema returns an error.

Source: [OpenAI Structured Outputs — Supported schemas](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas):
“Structured Outputs supports a subset of the JSON Schema language.”

The canonical runner therefore writes a private, per-attempt Codex schema copy
that recursively omits only the observed unsupported `uniqueItems` keyword.
The committed source schema is unchanged and remains the authority for local
post-provider validation. Duplicate message or thread IDs therefore still fail
the original schema and the deterministic inbox acknowledgement checks; only
the provider-facing constrained-generation hint is narrowed.

10M is complete when:

1. a RED test proves Codex would otherwise receive the original unsupported schema;
2. the Codex command receives a mode-0600 compatible copy without `uniqueItems`;
3. the original schema remains byte-logically strict for local validation;
4. focused, full, PII, OSS-boundary and shell checks pass;
5. a real inbox LaunchAgent run returns a schema-valid result or another truthful
   terminal state, then migrates the production checkpoint without replay.

10M is complete. PR #1359 merged as `384d03a39` after all checks passed in CI
run `30471441379`; 176 job-loop tests and 11 runner tests pass. A real bounded
Codex diagnostic used `gpt-5.6-terra`, exited 0 on its first attempt and produced
a result that passed the original local schema. Its private mode-0600 provider
copy contained no `uniqueItems`, while the committed Inbox schema retained both
strict occurrences. The provider reported 10,894 charged tokens for this
diagnostic.

The post-merge Inbox LaunchAgent run did not invoke a provider because the v2
bootstrap correctly produced no new candidate. It returned the truthful
`no_new_recruiting_email` state, preserved all 3 legacy boundaries, replayed no
message and left all application/Telegram counts unchanged. The runner
diagnostic plus this real scheduled run jointly prove provider compatibility and
production migration without fabricating a recruiting email.


### 4.6 Portable local installation

`JOB-PORTABLE-LOCAL-12A` is the first Order 12 increment. It turns the checked-out
application into a user-owned local install without copying Daisuke's profile,
credentials, or absolute paths.

The install contract is:

```text
verified user-supplied profile
  → private XDG config/state/data roots
  → authenticated BYO subscription provider selection
  → platform scheduler render
  → scheduler activation
  → deterministic install receipt
```

Private configuration follows the XDG Base Directory Specification. Relative XDG
overrides fail closed instead of being interpreted relative to an arbitrary launch
directory. Directories are mode `0700`; copied profiles and install receipts are mode
`0600`. Existing profiles are never overwritten unless the operator supplies the
explicit replacement flag.

Provider authentication stays provider-owned. The installer checks `codex login
status` and `claude auth status`; it records only the selected provider name and never
copies OAuth tokens, API keys, or provider auth files. `auto` chooses the first
authenticated provider in deterministic order (`codex`, then `claude-direct`).
Runtime entrypoints export that selection through `AGENT_RUNNER_PROVIDER`.

Scheduler ownership is platform-specific but application semantics stay shared:

| Platform | User scheduler | Daily | Inbox |
|---|---|---|---|
| macOS | launchd LaunchAgents | 08:30 Asia/Tokyo | every 15 minutes |
| Linux | systemd user timers | 08:30 Asia/Tokyo, persistent | every 15 minutes |

The portable installer accepts an explicit `none` scheduler for test/local manual
runs. Platform auto-detection supports only Darwin and Linux and fails closed on
unknown systems.

Sources:

- XDG Base Directory Specification,
  https://specifications.freedesktop.org/basedir-spec/latest/:
  “There is a single base directory relative to which user-specific state data
  should be written.”
- systemd.timer,
  https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html:
  “For each timer file, a matching unit file must exist, describing the unit to
  activate when the timer elapses.”
- Apple Daemons and Services Programming Guide,
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html:
  “In general, a daemon should not care whether a user is logged in, and user
  agents should be used to provide per-user functionality.”

`JOB-PORTABLE-LOCAL-12A` is complete when:

1. a clean temporary HOME installs from a user-supplied valid profile;
2. provider preflight accepts authenticated Codex or Claude and rejects missing auth;
3. private XDG roots and files have exact `0700`/`0600` modes;
4. macOS plists and Linux user service/timer units contain only rendered checkout
   and private-state paths;
5. a second install preserves the profile unless replacement is explicit;
6. scheduler commands are verified through fake launchctl/systemctl adapters and a
   `none` E2E install executes without external side effects;
7. focused, full, and CI suites pass.

Order 12 remains `in_progress` after 12A. Distribution packaging, a guided profile
authoring UI, and a clean-machine install from a release artifact remain.

`JOB-PORTABLE-RELEASE-12B` closes those remaining Order 12 gates. The guided setup
accepts either terminal prompts or a versioned answers JSON, copies no prior
candidate, rejects placeholder values, validates through the production profile
contract, and atomically writes one mode-`0600` profile. Legal or work-authorization
facts exist only when the user explicitly supplies their claim and evidence; the
wizard never derives them from name, residence, language, or employer.

Release artifacts are built from one Git commit, not the mutable working tree. They
contain only `apps/job-search-loop`, `runtime/agent-runner`, and a generated
`RELEASE.json`. Archive entries have sorted paths, normalized owner/group/time
metadata, and retained executable bits. Each `.tar.gz` is accompanied by a
SHA-256 file whose digest is verified before extraction in the clean-HOME E2E.

Sources:

- Git `archive`, https://git-scm.com/docs/git-archive:
  “Creates an archive of the specified format containing the tree structure for the
  named tree.”
- Reproducible Builds archive metadata,
  https://reproducible-builds.org/docs/archives/:
  “Most archive formats record metadata that will capture details about the build
  environment if no care is taken.”
- Python `argparse`, https://docs.python.org/3/library/argparse.html:
  “The argparse module makes it easy to write user-friendly command-line
  interfaces.”

`JOB-PORTABLE-RELEASE-12B` is complete when:

1. interactive and answers-file profile setup both produce a production-valid,
   private profile without placeholder or inferred facts;
2. existing profiles fail closed unless explicit replacement is supplied;
3. two builds of the same commit/version have the same SHA-256;
4. an archive inventory contains the two required runtime roots, generated release
   metadata, no private state, and no Daisuke profile;
5. the checksum is verified, the archive is extracted into a clean temporary
   machine root, and its bundled `install-local.sh --scheduler none` succeeds with
   a fake authenticated provider;
6. focused, full, and CI suites pass.

Order 12 becomes `completed` after 12B evidence is merged and reflected in the
canonical checkout.

### 4.7 Autonomous control plane

The target is a closed operating loop, not a chat session that waits for the user to
say “run again.” Four independent drivers share durable contracts:

| Driver | Trigger | Owns | Must never own |
|---|---|---|---|
| Acquisition | 08:30 JST daily, catch-up after wake | discovery, qualification, tailoring, two-slot submission budget, daily report | Gmail acknowledgement or strategy promotion |
| Follow-through | every 15 minutes | confirmation reconciliation, recruiter replies, Calendar, assessments, prep, stage/outcome updates | blind submit retry or offer acceptance |
| Learning | weekly eligibility check and after newly resolved outcomes | assignment, attribution, replay, comparison, promotion/rollback receipt | candidate facts, hard filters, side effects |
| Guardian | frequent deterministic check | freshness, integrity, stale pre-side-effect leases, safe kick/retry, remediation queue | code rewriting or retry after an uncertain external side effect |

Normal operation needs no human prompt. Human attention is reserved for identity- or
judgment-bound work:

| Autonomous by default | Human-only boundary |
|---|---|
| Search, rank, tailor, submit within pre-approved policy, reconcile, factual replies, offered-slot scheduling, reminders, prep and follow-up | Missing private/legal fact; real CAPTCHA or identity check; proctored/live or AI-prohibited assessment; attending an interview; choosing, negotiating final authority for, accepting or declining an offer |

Self-improvement means bounded data/config promotion, not recursive source-code
editing. The loop may change exactly one versioned strategy field through the
verified experiment protocol. It may not edit its own executable code, weaken truth
or privacy rules, expand permissions, change spending limits, or deploy a new
runtime. Repeated code-level defects become content-addressed remediation items for
the versioned development flow.

The verifier is independent of the model that performed the work. It checks
authoritative external state: ATS/Gmail receipts, Calendar rereads, Telegram ACKs,
material hashes, application transitions and SQLite integrity. A transcript saying
“applied” is never success without the corresponding outcome evidence.

Guardian recovery follows the side-effect fence:

```text
before external side effect
  → expired lease may be reclaimed
after navigation/send/submit starts
  → never blind-retry; reconcile authoritative state or remain unknown
integrity failure
  → stop affected side effects, rebuild projections from append-only events,
    verify, then resume
provider failure
  → exhaust configured free/authenticated fallbacks and official browser sources
repeated non-recoverable failure
  → one deduplicated Telegram alert plus durable remediation item
```

The local control plane remains the experimental playground. Cloud execution reuses
the same schemas, state machines, verifier and promotion gates; it replaces launchd,
private filesystem state and local OAuth transports with per-tenant managed queues,
encrypted storage and user-scoped OAuth.

## 5. State and side-effect contracts

### 5.1 Application state machine

```text
discovered
  → qualified | rejected
qualified
  → materials_ready | rejected
materials_ready
  → submit_claimed
submit_claimed
  → submitted | submit_unknown | not_submitted
submitted
  → recruiter_contact | screening | assessment | interview | rejected | withdrawn | offer
offer
  → negotiating → accepted | declined
accepted
  → started | withdrawn
```

Transitions append events; they do not rewrite history. The materialized state is
rebuildable from the event log. Canonical identity is:

```text
sha256(normalized_company + normalized_title + canonical_job_url)
```

### 5.2 Daily quota

The daily pass claims at most `2 - confirmed_submissions_today`. A second launch,
crash recovery, or model retry sees the prior claim and cannot exceed two confirmed
submissions. `submit_unknown` consumes a temporary quota slot until reconciled to
avoid duplicate applications.

### 5.3 Gmail and Calendar

The authenticated, privately configured `gog` account is the phase-1 Gmail and
Calendar transport. The inbox cursor records Gmail message/thread IDs and query
watermarks. Classifications are `confirmation`, `recruiter`, `assessment`,
`interview`, `rejection`, `offer`, or `irrelevant`.

An interview event key is derived from Gmail thread ID plus normalized start time.
Calendar writes use that key plus a stable hashed thread key in private metadata and
are reread before retry. Only recruiter-provided candidates with explicit timezone,
start, end, and source span are eligible. FreeBusy selects the earliest
non-conflicting candidate. The event is created before the threaded confirmation is
sent; a changed time updates the existing event rather than creating another. The
same confirmation path registers a private preparation job before sending the email.

The 15-minute inbox loop checks prep delivery before its no-work exit, so a due pack
is delivered even when Gmail has no new message. A pending generation job forces the
composition pass even without new mail. Generated packs are stored with their
SHA-256, and Telegram delivery uses one stable outbox key per interview and delivery
window.

Prep behavior:

| Time to interview | Action |
|---|---|
| More than 3 days | Generate and send a 3-day plan when the threshold is crossed |
| 1–3 days | Generate 3-day pack immediately, then 1-day refresh |
| Less than 1 day | Generate one immediate condensed pack |

Every pack includes role/company thesis, likely interviewer interests from public
evidence, five candidate stories grounded in `fact_id`s, technical/domain questions,
questions to ask, and logistics.

### 5.4 Assessments and take-homes

Every assessment manifest retains the Gmail IDs, HTTPS source, timezone-aware
deadline, deadline source span, rules source span, assessment type, proctoring flag,
and deterministic AI-policy classification. Only unproctored take-homes and business
cases whose quoted rules explicitly allow AI enter autonomous execution. Proctored,
live, explicitly prohibited, and unspecified-policy work remains behind a manual
integrity gate.

Allowed work runs in a private workspace through macOS `sandbox-exec`: network and
home reads are denied, writes are limited to the workspace, the environment is
sanitized, execution is time-bounded, and stdout/stderr are stored mode 0600 with
SHA-256 hashes. The durable state machine is:

```text
detected → prepared → executing → verified
                     ↘ execution_failed → executing
verified → submit_claimed → submit_started → submitted
                                         ↘ submit_unknown
```

`submit_started` and `submit_unknown` are terminal for automatic retry. Only an
authoritative employer receipt can produce `submitted`.

### 5.5 Telegram delivery

Copy the proven gig-loop outbox contract: `pending → claimed → send_started → sent`,
with unique event keys, lease fencing, payload hashes, and no blind retry from
`send_started`. The report locale comes from the private profile; application
materials and employer communication independently follow the official posting
language.

Telegram is the phase-1 proactive interface:

| Moment | Message contract |
|---|---|
| Confirmed application | company, role, official URL, confirmed state, fit thesis, selected resume name/hash; send that exact PDF as a document |
| Daily completion | best verified dream-job lead, discovered/qualified/submitted/unknown counts, blockers, fallbacks used, selected model route and next scheduled action |
| Recruiter or assessment event | classification, durable action taken, deadline/rules evidence and only the remaining human-only action |
| Interview scheduled | company/role, Calendar time/timezone, source message, confirmation state and preparation schedule |
| 3-day / 1-day / immediate prep | cited company thesis, likely interests, exactly five grounded stories, likely questions, questions to ask and logistics |
| Offer/result | verified compensation/work-mode facts, unresolved terms, whole-life comparison and the one human decision required |
| Weekly learning | baseline/candidate field, samples, funnel outcomes, replay result, confidence intervals and promote/inconclusive/rollback decision |
| Operational health | only after bounded recovery fails or an uncertain side effect needs attention; include failure class, last good receipt and next automatic retry/reconciliation |

Every event uses a stable content-addressed outbox key. A changed same-day result may
send one correction; an identical run remains silent. Life Manager consumes the same
event stream and `summary.v2`, so Telegram and the local dashboard cannot disagree.

## 6. Ranking

The deterministic score is 0–100:

| Dimension | Weight |
|---|---:|
| AI/agent role and demonstrated skill match | 30 |
| Enterprise/financial-services/Databricks/Salesforce leverage | 20 |
| Consumer AI/product/Swift/growth leverage | 15 |
| Location and Japan-remote feasibility | 15 |
| Compensation | 10 |
| Mission interest: AI, fintech, crypto, consumer agents | 10 |

Rules:

- `75+`: eligible for autonomous application.
- `65–74`: retain for weekly review/learning, do not auto-submit.
- `<65`: reject.
- Unknown compensation earns neutral points; known compensation below the hard floor
  is rejected.
- A model may explain a score but cannot change deterministic hard filters.

## 7. Resume and material policy

The default English resume is one ATS-friendly page, single column, text-first:

1. Headline: Applied AI / Agent Engineer bridging regulated enterprise deployment and
   consumer AI products.
2. MUIT experience with scoped Agentforce, Databricks, CRM, and RM-agent bullets.
3. Anicca/Life Manager product and growth experience.
4. NAIST/ATR research and weekly agent-practice community leadership.
5. Selected public communication: ICLR 2026 MUIT report link.
6. Education, languages, and selected earlier growth work.

Each tailored resume changes ordering and emphasis, not facts. PDFs are rendered and
text-extracted in verification so ATS-visible text is checked before submission.

The technical-business variant is also one ATS-friendly page. It keeps the same truth
ledger while changing the headline and order to emphasize regulated-enterprise
delivery, translating AI capabilities into user workflows, stakeholder alignment,
product ownership, customer adoption, GTM/growth, and public communication. It must
not invent formal PM, sales quota, people-management, or revenue ownership.

The Japanese variant is a one-page Japanese 職務経歴書 with fourteen grounded points
covering MUIT/MUFG, Databricks, Agentforce, Anicca/Life Manager, NAIST/ATR,
agent-community leadership, ICLR communication, growth, education, and languages.
The complete official posting text, not a person's name or presumed nationality,
determines language: primarily Japanese postings use the Japanese PDF; English
postings use the engineering or technical-business English PDF. The router returns
the only permitted path and SHA-256 for the submission intent and Telegram receipt.

## 8. Self-improvement harness

### 8.1 Current truth

The repository contains a resident deterministic one-field learning driver with
Wilson 95% intervals and an immutable outcome-attribution store. Strategy
generations are content-addressed, candidate lineage permits exactly one declared
field change, a held-out safety manifest is replayed before prospective traffic,
stable canonical job keys select baseline versus candidate, and authoritative funnel
outcomes rebuild a deterministic generation/stage projection. Promotion,
inconclusive closure and safety/failure rollback insert an immutable hashed decision
in the same transaction that compare-and-swaps the active-generation pointer. Gmail
submission confirmation is wired to the confirmed-application outcome.

The weekly driver is implemented and its live CLI path is verified. It becomes the
canonical resident LaunchAgent only after 11C merges and the canonical installer
re-renders the local scheduler. The guardian, lifecycle closure and `summary.v2`
drivers remain absent.

Live state measured on 2026-07-30:

| Evidence | State |
|---|---|
| Daily LaunchAgent | idle after exit 0; 08:30 JST schedule |
| Inbox LaunchAgent | idle after exit 0; 900-second schedule |
| Learning pass | real ledger run returned `inconclusive / insufficient_resolved_applications`, baseline=0 and candidate=0 resolved, replay violations=0; receipt `175d3b7be5db06f88dbdc9aaf9428dfbda3fe65245a497a1f377b6271255564c`; Telegram ACK `4530`; identical retry reused the same single outbox row and ACK |
| Ledger | integrity `ok`; 2 submitted / 1 submit-unknown / 2 not-submitted |
| Interview preparation | integrity `ok`; 0 registered / 0 pending |
| ATS proof objective | Ashby confirmed=0; Workday confirmed=0 |
| Attribution migration | integrity `ok`; 5/5 existing applications assigned to one explicit `legacy_unavailable` generation; application-state counts unchanged; 0 external outcomes and 0 projection rows before future evidence |
| Learning driver | 203 job-loop tests cover replay, deterministic two-arm assignment, insufficient/overlap decisions, Wilson promotion, immediate safety/three-failure rollback, pointer-race fencing, immutable receipts, weekly launchd/systemd rendering and at-most-once Telegram delivery; canonical scheduler installation waits for merge |

The engineering program must therefore describe the system as
`acquisition_live + follow_through_live + attribution_live +
learning_driver_implemented_pending_canonical_install`, never as fully self-healing.

### 8.2 Outcome and attribution model

Every application receives one immutable `strategy_generation_id` and the exact
values of source, query family, rank configuration, role family, material variant,
message variant, model route and prompt/material hashes. Later Gmail, Calendar and
ATS evidence resolves the funnel:

```text
verified lead
  → confirmed application
  → recruiter response
  → screen
  → interview round
  → offer
  → accepted/declined
  → started
```

Each outcome retains its external receipt and timestamp. Silence becomes a resolved
negative only after a versioned observation window; it is not treated as rejection
early. A model may classify evidence, but deterministic code owns attribution,
resolution and metric calculation.

The primary measurable objective during search is verified interview conversion.
Offer and accepted-offer utility supersede it once samples exist. Recruiter response
is an early indicator; submission count is capacity, never the optimization target.

### 8.3 Bounded experiment lifecycle

The loop changes exactly one strategy field per candidate generation:

| Field | Primary measurement |
|---|---|
| Discovery source/query family | qualified leads and confirmed applications per bounded search cost |
| Role family allocation | interview conversion |
| Resume emphasis | interview conversion by material variant |
| Optional application-message structure | recruiter response, then interview conversion |
| Score threshold within the safe range | interview yield with zero hard-filter regressions |
| Model route for a fixed task | verified success, latency and token cost without safety regression |

The resident learning driver:

1. freezes a baseline generation and proposes one falsifiable field change;
2. replays baseline and candidate on a held-out historical set;
3. rejects any truth-ledger, hard-filter, privacy, duplicate or side-effect-fence
   regression;
4. assigns eligible future applications deterministically between the two arms and
   persists the assignment before materials or submission;
5. joins only authoritative resolved outcomes to their original generation;
6. evaluates when both arms contain at least 10 resolved applications;
7. promotes only when the candidate's Wilson 95% lower bound exceeds the baseline's
   upper bound and safety violations remain zero;
8. otherwise records `inconclusive` and keeps the baseline;
9. immediately rolls back a candidate generation after any verified safety
   violation or three consecutive candidate-only deterministic execution failures;
10. emits one hashed decision receipt and a Telegram/Life Manager learning report.

Promotion atomically advances one active-generation pointer. Previous generations,
assignments and receipts remain immutable, so a rollback is a pointer change rather
than destructive history rewriting. The verifier recomputes every result from
outcomes and hashes; it never accepts the optimizer's prose as proof.

### 8.4 Dream-job and whole-life objective

The loop does not promise that anyone will get a particular job. It maximizes the
probability of a truthful, suitable offer and helps the user make the final decision.
Eligibility remains lexicographic: truth, legal feasibility and hard exclusions are
checked before any score optimization.

Among eligible roles, Life Manager evaluates one evidence-backed whole-life utility:

| Organ | Job evidence used |
|---|---|
| Financial | compensation range, employment type, benefits, currency, location and known commute cost |
| Physical | work mode, commute, travel and schedule demands against explicit user preferences |
| Mental | mission interest, role content, learning opportunity and explicitly evidenced culture/workload signals |
| Career | AI/agent depth, regulated-enterprise leverage, consumer-product ownership, crypto/fintech interest and future option value |

Unknowns remain visible unknowns. The system never diagnoses health, infers stress or
culture from stereotypes, or trades away a hard constraint for a high aggregate
score. After a user starts a role, optional 30/60/90-day Life Manager check-ins may
compare the predicted utility with lived financial, physical and mental outcomes;
those observations improve future preference weights only with explicit user
consent.

### 8.5 Local Life Manager experience

Locally, the loop owns side effects and Life Manager is the truthful read/control
surface:

```text
08:30  discover → verify → apply up to two → Telegram receipt + exact PDFs
every 15 min  reconcile Gmail → act → Calendar/prep → event message
weekly  join outcomes → evaluate one experiment → promote/keep/rollback
always  guardian checks freshness/integrity and repairs safe failures

summary.v2
  ├─ Today: dream-job lead, applications and next automatic action
  ├─ Pipeline: every role from discovered through final result
  ├─ Interviews: Calendar, round, prep windows and cited prep pack
  ├─ Decisions: blockers and the minimal human-only action
  ├─ Learning: active strategy, experiment samples and verified decisions
  └─ Health: last good runs, integrity, recovery and low-noise alerts
```

The user may pause, resume or change goals from Life Manager, but does not need to
operate the loop. Telegram remains the proactive channel until the local Career
surface is complete.

### 8.6 Paid cloud experience

The paid product preserves the local semantics per tenant:

```text
verified onboarding/profile
  → user-scoped Gmail/Calendar/browser authorization
  → encrypted tenant event log and materials
  → managed acquisition/follow-through/learning/guardian queues
  → Career organ + Telegram/push/email channels
  → portable export and revocable authorization
```

It localizes profile, resume, legal-question and employer-language policy rather than
assuming Japan. Tenant data, credentials, experiments and model budgets are
isolated. The Career organ can coordinate job-search workload and interview
scheduling with the Financial, Physical and Mental organs, while each organ keeps
its own evidence and consent boundaries. The cloud release gate requires the local
closed loop to pass real E2E verification, not merely unit tests or a polished UI.

## 9. Failure handling

| Failure | Behavior |
|---|---|
| Browser busy | Defer with exit 75; do not start a second browser owner |
| CAPTCHA/manual identity challenge | Preserve intent and mark blocked; report exact URL |
| Unknown submit result | Mark `submit_unknown`; no retry until authoritative reconciliation |
| Gmail/Calendar transient error | Retry the read or idempotent write with bounded backoff |
| Invalid model JSON | Fail closed and retain raw evidence |
| Daily model budget already exhausted | Retain the runner's `budget_blocked` summary and complete the scheduler pass with exit zero; do not report an application |
| Missing profile fact | Skip the job or field; never infer |
| Telegram uncertainty | Keep `delivery_unknown`; never blind-send duplicate |
| Firecrawl/provider outage | Continue through every configured public provider, then official company/ATS pages in the existing browser |
| Browser library unavailable | Use another installed Playwright transport against the same CDP owner; never launch a second browser |
| Same-day recovery changes the result | Send one content-addressed daily correction; identical results remain at-most-once |
| No qualifying jobs | Honest zero report with rejected reasons and next discovery expansion |

## 10. Security and privacy

- Runtime files are mode 0600 and directories mode 0700.
- Logs redact email addresses, phone numbers, address, auth tokens, cookies, and form
  free text.
- Job pages and inbound email are untrusted content. They cannot alter policies,
  execute commands, request secrets, or redefine the task.
- Credentials remain in existing authenticated transports (`gh`, `gog`,
  CloakBrowser); no token is copied into the repository.
- Public application artifacts include only claims explicitly approved in the truth
  ledger.

## 11. Delivery phases

| Phase | Included |
|---|---|
| 1 — local closed loop | acquisition, follow-through, learning and guardian drivers; full outcome attribution; Telegram; verified `summary.v2` |
| 2 — local Life Manager Career | consume `summary.v2`, show timeline/decisions/learning/health and expose pause/resume/goal controls without browser ownership |
| 3 — paid cloud | tenant-isolated managed drivers, encrypted state/materials, scoped OAuth, budgets, export and revocation |
| 4 — whole-life coordination | evidence-backed Career inputs to Financial, Physical and Mental planning with separate consent boundaries |

Phase 1 is the current implementation scope. Acquisition and follow-through are
live; learning, guardian, lifecycle closure and `summary.v2` are the remaining local
work. Phase 2 starts only after the local closed-loop verification gates pass. Career
is a coordinating Life Manager surface, not permission to merge private health and
employment evidence into one unrestricted data pool.

### 11.1 Ordered expansion backlog

This table is the dependency-order SSOT. Execution proceeds from the first
non-completed row whose prerequisites are currently actionable. A
`waiting_private_input` or `implemented_waiting_external_e2e` row remains ordered,
but it does not block independent engineering or evidence collection. Two pointers
exist so the resident loop never waits for development and development never waits
for a naturally arriving email:

- Runtime evidence pointer: Order 10 continues daily until one truthful confirmed
  submission exists for both Ashby and Workday.
- Engineering pointer: 11A and 11B are complete; 11C's resident weekly learning
  pass is implemented and awaits merge plus canonical scheduler installation.
  11D–11F and 13A–13C follow it in the order below.

Orders 8 and 9, plus 10L's naturally occurring same-thread follow-up proof, wait for
their respective private fact or external message.

The 2026-07-30 status refresh separates work that can proceed now from evidence that
must accumulate in the live loop:

| Lane | Current evidence | Next completion gate |
|---|---|---|
| Engineering now | The 11C baseline is canonical `origin/main` `0a4afeb5f`; the weekly learning driver, held-out replay, deterministic assignment, Wilson decision, rollback and hashed reporting are implemented with 203 passing job-loop tests and one real inconclusive receipt/Telegram ACK | Merge 11C, install/kick the canonical LaunchAgent, rerun healthcheck, then advance to `JOB-GUARDIAN-PASS-11D` |
| Resident runtime | The installed acquisition and inbox LaunchAgents are healthy (`last_exit=0`) on the 08:30 JST and 900-second schedules; ledger and interview-prep integrity are `ok`; applications remain 2 `submitted`, 1 `submit_unknown`, 2 `not_submitted` | Keep running Order 10 until the projection truthfully contains one confirmed Ashby and one confirmed Workday submission; current confirmed adapters are 0/2 |
| Private/external wait | No verified nationality/work-visa facts, real interview email, or naturally occurring later same-thread recruiting message has arrived | Close Order 8, Order 9 and the 10L E2E gate only when their authoritative input exists; none blocks 11B engineering |

| Order | Deliverable | Status | Completion evidence |
|---:|---|---|---|
| 0 | `JOB-CANONICAL-MERGE-1`: make Life Manager the only versioned source and preserve the live local loop | `completed` | PR #1273; 114 job-loop + 7 runner tests; all five CI checks passed in run `30444708546`; both canonical LaunchAgents last exit 0; 08:30 JST/900s schedules; three SQLite integrity checks `ok`; application and Telegram counts unchanged through cutover |
| 1 | Technical-business resume bundle | `completed` | 53 tests; private A4 one-page PDF; ATS extraction and visual inspection; role-based resume routing |
| 2 | Role-specific application messages for Product, GTM, Partnerships and Customer Success | `completed` | Four strict templates; real-profile generation; fact/source validation; 59 tests |
| 3 | Recruiter question auto-reply | `completed` | 68 tests; approved-answer and fail-closed policy; at-most-once outbox; real two-message same-thread Gmail round trip with private evidence |
| 4 | Interview slot selection and confirmation | `completed` | 79 tests; explicit timezone/source validation; real busy-slot skip, private Calendar event, same-thread Gmail reply and retry-idempotency E2E; all test artifacts cleaned |
| 5 | Assessment and take-home workflow | `completed` | 89 tests; quoted rule/deadline manifest; real sandbox denial of network/home access; private hashed evidence; fenced unknown-submission retry block |
| 6 | No-give-up runtime reliability | `completed` | 104 tests; real Firecrawl-credit failure recovered through Freehire + LinkedIn Tokyo/Remote with 30 usable candidates; real daily owner connected to Chrome CDP and inspected official ATS pages; Node Playwright failure fell through to installed Python Playwright; Inbox prompt transport exits successfully; exact submitted-resume path/hash delivery is enforced; historical material aliases recovered the exact LayerX and Ex-ture PDFs and real Telegram document ACKs 4378/4379; same-day corrected report ACK 4377 |
| 7 | Bilingual resume and official-posting language routing | `completed` | 107 tests; fourteen grounded Japanese points; A4 one-page Japanese PDF; extracted-text and visual inspection; real CLI selected the Japanese PDF for Japanese text and technical-business English PDF for English text; routed path/hash remains the Telegram receipt source |
| 8 | Verified nationality and Japan work-visa answers | `waiting_private_input` | Add the two legal facts to the private profile, then rerun the current BJAK AI Finance Agent application without inference |
| 9 | Recurring interview preparation and real interview-email E2E | `implemented_waiting_external_e2e` | Persistent registration; 3-day/1-day/immediate windows; real Telegram immediate delivery plus second-tick dedupe; forced production launchd no-mail pass and private DB healthcheck; final real recruiter-email E2E waits for an interview message |
| 10 | ATS resilience for Ashby, Workday and other blocked forms | `in_progress` | 10A merged in PR #1288; 10B merged in PR #1291/#1293 with real existing-CDP job→choice→account replay. 10C merged in PR #1306 (`34002214a`, CI `30451149945`): definite pre-click failures safely reopen with fresh evidence/new fences; the real ledger migrated with integrity `ok`, unchanged 2 submitted / 1 not-submitted applications, 3 attempts and 1 retryable. 10D merged in PR #1310 (`10dafba7a`, CI `30452160572`): strong per-tenant private credentials and secret-free receipts; the real CrowdStrike tenant created once then reused without rotation. 10E merged in PR #1316 (`828c4d7b1`, CI `30453061715`): deterministic inbox detection accepts exactly one HTTPS activation URL from `@myworkday.com` only when its exact host is already credentialed, stores only its hash, and fences navigation at most once; 161 job-loop + 7 runner tests pass. Live daily 6→7 and inbox 13→15 both exited 0; no new verification email arrived, historical seen mail was not reopened, and healthcheck integrity remained `ok`. The daily retry safely moved BJAK from definite pre-click failure to terminal `submit_unknown` after a real submit click lacked confirmation, with Telegram report ACK 4414. 10F merged in PR #1322 (`b17f838cd`, CI `30454763988`) with 163 job-loop + 9 runner tests: a pre-navigation `claimed` row is a 900-second lease and may recover with a new fence after a crash, while the old fence fails and every state at or after `navigation_started` remains terminal. Live inbox 15→16 exited 0 with no new mail or false-positive historical replay; integrity remained `ok`. 10G merged in PR #1326 (`aa81e7dff`, CI `30455795192`) with 165 job-loop + 9 runner tests: only schema-valid processed thread IDs that are an exact subset of the current scan are atomically acknowledged; unknown, duplicate, count-mismatched, missing-result, and omitted IDs remain unacknowledged for retry. Live inbox 16→17 exited 0, no-work left the mode-0600 three-thread seen checkpoint unchanged, and integrity remained `ok`. 10H merged in PR #1331 (`6bc07d1ce`, CI `30456681640`) with 166 job-loop + 9 runner tests: only runner exit 75 paired with the current `budget_blocked` summary becomes a healthy scheduled wait before any result resolution or seen acknowledgement; every other failure propagates. Live inbox 17→18 exited 0 and left seen-state mtime unchanged; integrity remained `ok`. Live daily catch-up 7→9 then completed with exit 0 and Telegram ACKs 4421/4425: no confirmed submission, one new BJAK AI Finance Agent stayed `not_submitted` before click because nationality is absent and its explicit three-year minimum is unmet; ledger is integrity `ok` at 2 submitted / 1 submit-unknown / 1 not-submitted. 10I merged in PR #1346 (`96adde721`, CI `30460492034`) with 168+9 tests; live daily 9→10 exited 0, Telegram 4429 reported zero submissions/two truthful pre-submit blocks, and the mode-0600 projection shows generic submitted=2, Ashby confirmed=0, Workday confirmed=0. The run proved the old reservation could admit a provider charge above the daily cap. 10J merged in PR #1350 (`e3bc44685`, CI `30462362148`) with 168+10 tests; live daily 10→11 exited 0 before provider selection, wrote exactly one blocked full-pass reservation and no attempt/settlement artifacts, kept counts at 2 submitted / 1 submit-unknown / 2 not-submitted, and passed both integrity checks. 10K merged in PR #1352 (`852d18a14`, CI `30464923726`) with 174+10 tests; live inbox 24→25 exited 0, checked one real Gmail candidate, made zero false promotions, launched no provider, changed neither seen checkpoint nor 12-row Telegram outbox, refreshed the projection to 2026-07-30, and passed both integrity checks. 10L merged in PR #1355 (`162b4750c`, CI `30466877218`) with 176+10 tests and seven passing checks. 10M merged in PR #1359 (`384d03a39`, CI `30471441379`) with 176+11 tests: Codex receives a private compatible schema copy while the original strict schema still validates the result. A real first-attempt `gpt-5.6-terra` diagnostic returned schema-valid output; canonical production then advanced Inbox run 5 with exit 0 and migrated checkpoint v1→v2 with 3 bootstrap message IDs, 3 legacy boundaries and no replay. Ledger/preparation integrity stayed `ok`; counts remain 2 submitted / 1 submit-unknown / 2 not-submitted, Ashby confirmed=0 and Workday confirmed=0. Continue until one real confirmed application exists for both Ashby and Workday; 10L's real same-thread future-message proof remains an independent external wait |
| 11 | Closed-loop Dream Job objective, self-improvement and self-healing | `in_progress` | 11A completed in PR #1364 (final CI `30473862095`). 11B adds immutable attribution and outcomes. 11C implements the resident weekly learning driver, deterministic two-arm assignment, held-out replay, Wilson promotion, immediate rollback, compare-and-swap pointer and hashed Telegram report; its real first pass remained truthfully inconclusive at 0/0 resolved with replay violations=0 and ACK `4530`, without changing the five application states. Guardian, lifecycle closure and `summary.v2` remain in 11D–11F |
| 12 | Portable local OSS distribution | `completed` | 12A merged in PR #1296; 12B merged in PR #1302 (`a58f1838`, CI `30449915191`): guided interactive/JSON profile authoring with placeholder/overwrite/legal-inference fences; reproducible 105-entry merge-commit tar.gz + SHA-256 `f334202a`; extracted-artifact clean-HOME install; 149 job-loop + 7 runner tests; canonical health exit 0 and both SQLite integrity checks `ok` without scheduler reinstall |
| 13 | Life Manager Career organ and paid multi-tenant service | `pending` | 13A local Career surface consumes `summary.v2`; 13B moves the proven drivers to isolated cloud tenants; 13C integrates evidence-backed Financial/Physical/Mental job utility without merging consent boundaries |

### 11.2 Autonomy closure increments

This is the implementation-order SSOT after the 2026-07-30 status refresh. The
active engineering task is always the first `pending_actionable` row; later rows do
not start merely because their design is already written:

| Increment | Status | Done when |
|---|---|---|
| `JOB-AUTONOMY-CONTRACT-11A` | `completed` | PR #1364 / final CI `30473862095`; this specification states current truth, four resident drivers, verifier boundary, Telegram/Life Manager UX, human-only boundaries, local→cloud contract and the complete dependency order |
| `JOB-OUTCOME-ATTRIBUTION-11B` | `completed` | PR #1374 / merge `683ba9562` / final CI `30502556044`; immutable content-addressed generations and DB-enforced immutable assignments/outcomes persist; one external receipt may prove multiple stages only for its bound application; negative silence requires a versioned observation policy; Gmail submission confirmation is attributed; 191 job-loop and 11 runner tests pass; the redacted CLI migrated the live 5-row ledger with unchanged state counts, zero unassigned rows and integrity `ok`; projection rebuild is deterministic |
| `JOB-LEARNING-PASS-11C` | `implemented_pending_merge` | Baseline `origin/main` `0a4afeb5f`; 203 job-loop + 11 runner tests pass. Sunday 09:15 JST launchd and persistent systemd drivers replay eight safety cases, deterministically assign future canonical job keys, evaluate authoritative interview outcomes, atomically promote/close/rollback with pointer-race fencing, and send one content-addressed Telegram report. The live ledger stayed integrity `ok` with unchanged 2 submitted / 1 submit-unknown / 2 not-submitted counts; its first 0/0-sample decision was correctly inconclusive, receipt `175d3b7be5db06f88dbdc9aaf9428dfbda3fe65245a497a1f377b6271255564c`, Telegram ACK `4530`; canonical installation remains before `completed` |
| `JOB-GUARDIAN-PASS-11D` | `pending_after_11C` | A deterministic scheduled guardian checks launchd/timer freshness, DB integrity, provider/browser health and leases; repairs only pre-side-effect failures; deduplicates alerts and persists remediation |
| `JOB-LIFECYCLE-CLOSE-11E` | `pending_after_11D` | Follow-up cadence, every interview round, offers, negotiation support and accepted/declined/started outcomes are durable; only final identity/judgment actions require the user |
| `JOB-CAREER-SUMMARY-11F` | `pending_after_11E` | Versioned `summary.v2` exposes Today, Pipeline, Interviews, Decisions, Learning and Health; its counts are rebuilt from the same events and match Telegram receipts |
| `LIFE-CAREER-LOCAL-13A` | `pending_after_11F` | The local Life Manager Career surface reads `summary.v2`, shows the full timeline and provides pause/resume/goal controls without browser ownership |
| `LIFE-CAREER-CLOUD-13B` | `pending_after_local_e2e` | Per-tenant queues, encrypted state/materials, scoped OAuth, budgets and export/revocation reproduce the verified local semantics |
| `LIFE-WHOLE-HEALTH-13C` | `pending_after_13B` | Career evidence informs Financial, Physical and Mental planning with explicit consent, visible unknowns and no medical or employment guarantee |

## 12. Verification

Completion requires:

1. Unit and integration tests for normalization, hard filters, scoring, quotas,
   transitions, claims, Gmail classification, Calendar idempotency, Telegram outbox,
   and self-improvement promotion.
2. Resume PDF render plus extracted-text verification.
3. LaunchAgent validation and a forced catch-up run.
4. Real Gmail read and Calendar test-event create/reread/delete in the authenticated
   account.
5. Real Telegram delivery with outbox evidence.
6. Real browser evidence for the first eligible ATS application. The final report
   distinguishes `submitted`, `submit_unknown`, and `blocked`; dry-run output does not
   count as completion.
7. Outcome-oriented evals grade authoritative ATS/Gmail/Calendar/Telegram/database
   state and retain the complete trace; model narration alone cannot pass.
8. A replay suite proves every candidate strategy preserves truth, hard filters,
   privacy, idempotency and side-effect fences before prospective assignment.
9. One live experiment reaches a real `promote` or `inconclusive` decision from the
   required resolved samples, or a real `rollback` from a verified safety/failure
   trigger; independent recomputation matches its receipt.
10. Guardian fault injection proves safe lease recovery before a side effect,
    non-retry after submit/send/navigation starts, projection rebuild after a forced
    integrity fault, and one deduplicated alert after bounded recovery fails.
11. A seven-day local soak completes scheduled acquisition, inbox, learning-
    eligibility and guardian passes without manual commands except declared
    human-only boundaries; every unexpected stale/error state becomes a durable
    recovery or remediation receipt.
12. `summary.v2`, Telegram receipts and rebuilt event-log projections agree on
    application, interview, offer, experiment and health state.
13. The paid cloud gate additionally proves tenant isolation, scoped OAuth
    revocation, encrypted backup/restore, per-tenant budgets and portable export
    against the same behavioral suite.
