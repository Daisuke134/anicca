# Autonomous Job Search Loop Design

**Date:** 2026-07-28  
**Owner:** Daisuke Narita  
**Status:** Phase 1 live from the canonical Life Manager checkout; `JOB-CANONICAL-MERGE-1` completed
**Done when:** `Daisuke134/life-manager` is the only versioned source of the local job-search runtime and can discover, qualify, tailor, and submit up to two eligible applications per Japan day; reconcile Gmail; create interview calendar events and preparation packs; send an at-most-once Telegram report; and promote only evidence-backed strategy changes.

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

This is the current atomic deliverable. It changes ownership and runtime wiring,
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
  └─ inbox-pass (every 15 minutes)
       ├─ Gmail reconcile
       ├─ stage/outcome transition
       ├─ Calendar idempotent insert/update
       ├─ 3-day and 1-day prep packs
       └─ Telegram event report

immutable JSONL evidence → materialized SQLite state → Life Manager summary contract
```

### 4.1 Repository and runtime split

| Area | Location | Responsibility |
|---|---|---|
| Versioned implementation | `apps/job-search-loop/` | deterministic core, adapters, prompts, schemas, tests, launchd templates |
| Versioned model runner | `runtime/agent-runner/` | provider routing, schema validation, bounded fallback, token budget |
| Upstream framework | pinned fork/checkout under `~/.local/share/anicca/job-search/framework` | candidate profile, job dossier, tailoring conventions |
| Private runtime state | `~/.local/state/anicca/job-search` | ledger, traces, evidence, locks, outbox |
| Private materials | `~/.local/share/anicca/job-search/materials` | master resume, tailored resumes, cover letters, prep packs |
| Future Life Manager bridge | versioned `summary.v1.json` schema | read-only career-organ summary; no phase-1 panel mutation |

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
`send_started`. Daily reports show discovered, qualified, submitted, unknown,
responses, interviews, errors, selected model route, and links to each applied role.

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

The loop improves one bounded strategy variable per weekly generation:

| Input | Measurement |
|---|---|
| Discovery source | qualified and submitted jobs per source |
| Role family | recruiter response and interview conversion |
| Resume emphasis | response rate by material variant |
| Cover-letter structure | response rate where letters are optional/required |
| Score threshold | eligible yield without hard-filter violations |

Promotion protocol:

1. Preserve generation config, prompts, model route, material hashes, and outcomes.
2. Propose one change with a falsifiable expected effect.
3. Replay on a held-out set of historical jobs; reject any truth-ledger or hard-filter
   regression.
4. Run the candidate generation prospectively.
5. Promote only after at least 10 resolved applications and a better response-rate
   lower bound; before that, keep the baseline and record evidence as inconclusive.
6. A verifier compares every claimed improvement step to real hashes, replay results,
   and ledger transitions. Unverified claims become a durable remediation item.

The primary optimization metric is interview conversion. Recruiter response is an
early indicator, not a substitute for interview conversion.

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
| 1 — local autonomous loop | resume refresh, discovery, rank, two/day submit, Gmail reconciliation, Calendar, prep packs, Telegram, launchd, evidence |
| 2 — Life Manager surface | consume `summary.v1.json`, add Career organ/timeline, expose pause/goal controls without owning browser side effects |

Phase 1 is the current implementation scope. It produces the stable summary contract
needed by phase 2, but does not force a fifth Life Manager organ into the current
four-organ scoring model.

### 11.1 Ordered expansion backlog

This table is the execution-order SSOT. Work proceeds from the first non-completed
row; its status changes in the same commit as implementation evidence.

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
| 10 | ATS resilience for Ashby, Workday and other blocked forms | `in_progress` | 10A merged in PR #1288; 10B merged in PR #1291 (`1ff642fd`, CI `30447613983`) and closeout PR #1293, then live-verified at canonical `2e75c720` (daily/inbox runs 4/8, exits 0, ledger integrity `ok`) with 131 job-loop + 7 runner tests and real existing-CDP job→choice→account replay (19/23/28 redacted controls, zero input/account/upload/claim/submit side effects); order completes only after one real confirmed application per adapter |
| 11 | Dream Job objective and evidence-backed strategy promotion | `waiting_samples` | Deliver one verified best-fit lead per day; persist role/source/message experiment assignment and outcomes; promote one-field changes only after at least 10 resolved applications per arm and Wilson-interval proof |
| 12 | Portable local OSS distribution | `in_progress` | 12A merged in PR #1296; 12B locally verified with guided interactive/JSON profile authoring, placeholder/overwrite/legal-inference fences, reproducible commit-tree tar.gz + SHA-256 (105 entries at implementation commit `4d080089e`), extracted-artifact clean-HOME install, 149 job-loop + 7 runner tests; completes after 12B CI/merge and canonical reflection |
| 13 | Life Manager Career organ | `pending` | Career timeline, dream-job goal, learning evidence and pause/resume controls consuming `summary.v1.json` |

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
