# Anicca Job Search Loop

Anicca Job Search Loop is a bounded, evidence-first job application system for a
verified private candidate profile. It discovers and ranks suitable roles, submits at
most two verified applications per Japan day, monitors recruiter mail, prepares
interviews, and reports every material state change to Telegram.

## Operating contract

| Concern | Current rule |
|---|---|
| Daily target | At most 2 unique, confirmed submissions |
| Location | Tokyo or remote roles that can employ someone based in Japan |
| Compensation | JPY 5.5M hard floor; JPY 7M target |
| Role focus | Applied AI/agent engineering plus technical AI business roles: Product, Program, Solutions, GTM, Partnerships, Customer Success and Sales Engineering |
| Discovery | Firecrawl, public Freehire, public low-volume LinkedIn Tokyo/Remote, then official ATS pages in the existing browser; one provider failure never ends a pass |
| Evidence | Every application is fenced in SQLite and retained under a private evidence directory |
| Uncertainty | Ambiguous submission becomes `submit_unknown` and is never blindly retried |
| Personal data | Verified private profile and generated materials are mode `0600` |
| Career summary | Every terminal daily path atomically refreshes private `summary.v1.json` with state counts and Ashby/Workday confirmed-application coverage |
| Application receipt | Every confirmed submission records the exact resume path and SHA-256, then sends that same PDF to Telegram once with company, role and URL |
| Daily report repair | A materially changed same-day catch-up sends one content-addressed correction; identical retries remain at-most-once |
| Inbox | Gmail metadata is prefiltered deterministically; a model runs only for a new recruiting thread or a pending prep-pack generation job |
| Calendar | Only explicit timezone-aware recruiter candidates are considered; the earliest free candidate is confirmed once |
| Interview prep | Every confirmed interview is registered before the email reply; Telegram refreshes are delivered at the 3-day and 1-day windows, or immediately inside 1 day |
| Assessments | Autonomous execution requires explicit AI permission and no proctoring; all code runs without network or home access |
| Self-improvement | One-field experiments require 10 resolved samples per arm, zero replay violations, and non-overlapping Wilson 95% intervals |

Runtime dependency ordering follows
[`rules/runtime-ordering.md`](rules/runtime-ordering.md): deterministic recovery,
quota, and policy gates run before browser/model initialization.

## Runtime

| Component | Schedule | Route |
|---|---|---|
| `ai.anicca.job-search-daily` | 08:30 JST daily | bounded browser-lane agent |
| `ai.anicca.job-search-inbox` | every 15 minutes | deterministic Gmail and prep preflight; Terra composition agent only for new recruiting work or pending prep generation |

The current local deployment uses launchd and is designed so the same drivers and
SQLite contracts can later be invoked by Life Manager without changing application
semantics.

The daily owner connects Playwright to the already-running authenticated Chrome CDP
endpoint. It does not launch a duplicate browser. The driver reserves a bounded
normal pass plus bounded same-day recovery capacity, so a transient provider or
browser-tool failure can fall through to another implementation without becoming an
unlimited loop.

## Key paths

| Purpose | Path |
|---|---|
| Private profile | `~/.config/anicca/job-search/profile.json` |
| Strategy | `config/strategy.default.json` |
| Ledger | `~/.local/state/anicca/job-search/ledger.sqlite3` |
| Life Manager read projection | `~/.local/state/anicca/job-search/summary.v1.json` |
| Interview prep state | `~/.local/state/anicca/job-search/interview-prep.sqlite3` |
| Evidence | `~/.local/state/anicca/job-search/evidence/` |
| Materials | `~/.local/share/anicca/job-search/materials/` |
| Engineering resume | `~/.local/share/anicca/job-search/materials/master/Daisuke_Narita_AI_Resume.pdf` |
| Technical-business resume | `~/.local/share/anicca/job-search/materials/business/Daisuke_Narita_AI_Business_Resume.pdf` |
| Japanese resume | `~/.local/share/anicca/job-search/materials/japan/Daisuke_Narita_Japan_AI_Resume.pdf` |
| Resume language router | `job_search_loop/resume_routing.py` |
| Technical-business message templates | `templates/application-messages.v1.json` |
| Recruiter reply policy | `job_search_loop/recruiter_reply.py` |
| Interview scheduling policy | `job_search_loop/interview_scheduling.py` |
| Interview prep policy | `job_search_loop/interview_prep.py` |
| Assessment integrity and execution policy | `job_search_loop/assessment_workflow.py` |
| Daily driver | `scripts/run-daily.sh` |
| Inbox driver | `scripts/run-inbox.sh` |

## Operations

```bash
cd /path/to/life-manager/apps/job-search-loop
python3 -m unittest discover -s tests -v
zsh scripts/render-resume.sh
zsh scripts/render-business-resume.sh
zsh scripts/render-japanese-resume.sh
zsh scripts/install-launchd.sh
zsh scripts/healthcheck.sh
```

### Portable local install

Authenticate one supported subscription CLI without copying its credentials into
this repository:

```bash
codex login
# or: claude auth login
```

Then import a valid private profile and install the user scheduler for the detected
platform:

```bash
zsh scripts/install-local.sh \
  --profile /absolute/path/to/profile.json \
  --provider auto \
  --scheduler auto
```

`auto` selects an authenticated Codex CLI first, then Claude CLI. The receipt stores
only `codex` or `claude-direct`; OAuth tokens and provider auth files remain owned by
their CLI. macOS installs LaunchAgents; Linux installs systemd user services and
timers. Use `--scheduler none` for a manual/test install without scheduler side
effects.

The installer follows XDG config/state/data roots, rejects relative XDG overrides,
creates private directories as `0700`, and writes the profile and receipt as `0600`.
It never overwrites an existing profile unless `--replace-profile` is explicit.

For guided authoring, create the active private profile first:

```bash
zsh scripts/setup-profile.sh
```

The prompts require an application email and at least one explicit claim/evidence
pair. They do not infer nationality, visa, work authorization, or any other legal
fact. For repeatable provisioning, pass a production-shaped JSON file with
`--answers /absolute/path/to/answers.json`. Placeholder values and implicit
overwrites fail closed.

### Reproducible release artifact

Build a commit-pinned archive and SHA-256 sidecar:

```bash
zsh scripts/build-release.sh \
  --output-dir /absolute/path/to/dist \
  --version 0.1.0
shasum -a 256 -c /absolute/path/to/dist/anicca-job-search-0.1.0.tar.gz.sha256
```

The archive contains only the job-loop application, the bounded agent runner, and
`RELEASE.json`. It contains no candidate profile, credential, SQLite state, evidence,
or logs. After verification and extraction, run the bundled `setup-profile.sh`, then
`install-local.sh` from the extracted directory.

Do not start a second daily executor. To trigger the deployed loop, kick the existing
LaunchAgent and inspect the generated evidence:

```bash
launchctl kickstart "gui/$(id -u)/ai.anicca.job-search-daily"
```

The daily pass searches three English/Japanese query families across engineering,
technical-business, crypto and consumer-agent work. Firecrawl is only one provider.
The bundled public Freehire and LinkedIn guest search adapters require no applicant
API key; if all automated providers fail or return no usable posting, the same owner
continues through official company career and ATS pages in the authenticated browser.
An actual legal/profile fact, CAPTCHA or authoritative submission ambiguity may stop
one application, but a scraper outage may not.

After each confirmed submission, the deterministic driver reads the resume path and
SHA-256 from the fenced ledger and sends that exact PDF as a Telegram document.
Historical rows created before this contract have no resume hash and are not guessed.
The text daily report is independently deduplicated; a materially newer same-day
result produces a single content-addressed correction instead of leaving an obsolete
failure report as the apparent final state.

Before the claim, the deterministic resume router detects the primary language from
the complete official posting text. Japanese postings use the Japanese one-page AI
resume for every role family. English postings use the engineering or
technical-business English variant according to role family. The same routed path
and SHA-256 are stored in the intent and later drive the Telegram document receipt;
the agent may not manually replace the routed file.

The inbox checkpoint is committed only after its AI pass succeeds. Every poll first
delivers any due preparation pack, even when Gmail has no new message. Empty polls
with no pending prep generation exit successfully without consuming a model budget.
Gmail bodies remain untrusted input; the loop never follows instructions embedded in
a job page or email.

Direct recruiter questions about verified experience, location, desired compensation,
or contact details may receive one threaded reply. Work authorization, visa, start
date, current compensation, references, and legal questions fail closed. Scheduling
questions with complete candidate times are checked against the primary Calendar.
The earliest explicit free candidate is stored as one private event before the
threaded confirmation is sent. Missing timezone/date/duration, a fully busy candidate
set, or ambiguous text causes no reply and no Calendar write. The Gmail inbound
message ID is the outbox key, so an uncertain send is never blindly retried.

Before an interview confirmation email is sent, the same transaction registers a
private preparation job. The 15-minute inbox loop generates any pending pack from
exactly five approved profile facts plus cited public company/interviewer evidence,
stores its hash, and sends Telegram reminders at the 3-day and 1-day windows. An
interview registered inside one day receives an immediate condensed pack. Each
interview/window pair has a stable outbox key, so a retry cannot duplicate the
Telegram message.

Assessment rules are evidence, not assumptions. An unproctored take-home or business
case enters the autonomous path only when its quoted rules explicitly allow AI.
Proctored/live assessments and prohibited or unspecified AI policies stay behind the
manual integrity gate. Allowed work runs in a private `sandbox-exec` workspace with
no network, no access to the user's home, a sanitized environment, bounded runtime,
and hashed private logs. Submission follows
`verified → submit_claimed → submit_started → submitted|submit_unknown`; neither
`submit_started` nor `submit_unknown` is blindly retried.

## Learning loop

| Layer | Current behavior |
|---|---|
| Daily dream-job search | Ranking rewards AI/agents, regulated finance, consumer AI, crypto/fintech mission, Japan feasibility and compensation |
| Outcome memory | Application, recruiter response, interview and rejection transitions persist in SQLite with source/material hashes |
| Safe experiments | One source, role-family, resume-emphasis, message or threshold variable changes at a time; replay must preserve truth and hard filters |
| Promotion gate | Baseline stays active until both arms have at least 10 resolved applications and the Wilson 95% intervals support improvement |
| Self-healing | launchd restarts, browser ownership evidence, multi-provider discovery, fenced side effects, bounded recovery and content-addressed report correction |
| Not yet complete | Persistent experiment outcome promotion, real confirmed adapter samples, release packaging/guided profile authoring, and Life Manager Career UI |
