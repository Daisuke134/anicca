# Life Manager Open-Source Money Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close one real Upwork email-signup/login → job → proposal → negotiation → contract →
delivery → received-payment loop first, then generalize the proven receipts into the local-first
open-source portfolio agent and add remaining markets one at a time.

**Architecture:** The active slice is Upwork only. It uses the dedicated CloakBrowser profile,
normal owner email/password authentication, Upwork-scoped state and the smallest existing durable
effect primitives needed for the first live path. Coconala continues independently and contributes
neither runtime state nor capacity to Upwork. Cross-market Portfolio CEO and Skill Factory work
resumes only after Upwork receives one real payment.

**Tech Stack:** Python 3.13+, standard-library SQLite/JSON, existing CloakBrowser CDP helpers,
approved provider APIs, existing launchd release system, pytest with plugin autoload disabled.

**Spec:** `docs/superpowers/specs/2026-08-22-life-manager-gig-economy-loop-design.md`

## Global constraints

- Execute exactly one task at a time and commit/push after its verification passes.
- Until the first Upwork payment, mutate and measure Upwork only; do not operate on Coconala.
- Use normal owner email/password signup/login for Upwork. DO NOT use Google, Apple or social login.
- Create an Upwork account only if the owner email has no existing account; never create a duplicate.
- Upwork capacity counts active Upwork contracts only. Never read Coconala projects as Upwork capacity.
- Upwork acquisition spend is permanently USD 0 for this loop: never buy Connects, upgrade, boost or open billing. Submit only from granted/returned Connects or zero-Connect invitations.
- Observe the authenticated Upwork UI/API first, then refine selectors and payloads from receipts.
- Complete the zero-spend bootstrap across onboarding rewards, invitations, direct offers and one
  bounded Project Catalog service, then submit from free capacity before adding general abstractions.
- Do not move the current `skills/earn/gig/TODO.md` production-repair cursor.
- Do not add a scheduler, workflow service, browser harness, vector DB or second ledger.
- Tests cover only money loss, duplicate external effects, data loss, authentication leakage and the
  current live path. Do not expand a broad TDD matrix before the first live Upwork receipt.
- All provider mutations require authorization receipt → immutable intent → reconcile → at most one
  effect → authoritative readback → canonical receipt.
- Dais's special approval is recorded privately per account/action/transport. It enables matching
  Upwork/Coconala actions; it does not become a universal public default.
- Public provider templates remain `unknown`; credentials and approval evidence remain outside Git.
- No blind retry, synthetic success, fake payment, estimated revenue or missing-evidence-as-zero.
- Paid work and deadline protection outrank new acquisition and experiments.
- A market advances only after the preceding live receipt gate closes.
- Exactly-once means one logical effect identity with zero blind retry; it does not claim a remote
  provider transaction is atomic with local SQLite.

## Locked interfaces

Executors keep these names and value sets consistent across tasks:

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

class AuthorizationState(StrEnum):
    APPROVED_API = "approved_api"
    APPROVED_BROWSER = "approved_browser"
    APPROVED_ASSISTED = "approved_assisted"
    DENIED = "denied"
    UNKNOWN = "unknown"

class MarketStage(StrEnum):
    RESEARCH = "research"
    AUTHORIZED = "authorized"
    READ = "read"
    SALE = "sale"
    CONTRACT = "contract"
    DELIVERY = "delivery"
    PAYMENT = "payment"
    REPEATABLE = "repeatable"
    ACTIVE = "active"
    ASSISTED = "assisted"
    DENIED = "denied"
    UNPROFITABLE = "unprofitable"

@dataclass(frozen=True)
class EffectIntent:
    provider: str
    account_key: str
    resource_id: str
    action: str
    payload_hash: str
    authorization_hash: str
    effect_key: str

@dataclass(frozen=True)
class ProviderReceipt:
    provider: str
    action: str
    effect_key: str
    provider_receipt_id: str
    authoritative_state: str
    observed_at: str
    evidence_hash: str

class ProviderAdapter(Protocol):
    def discover(self) -> list["Opportunity"]: ...
    def inspect(self, opportunity_id: str) -> "OpportunityDetail": ...
    def plan_effect(self, action: str, payload: dict) -> EffectIntent: ...
    def reconcile(self, intent: EffectIntent) -> "ProviderState": ...
    def execute(self, intent: EffectIntent) -> "TransportAck": ...
    def readback(self, intent: EffectIntent) -> ProviderReceipt: ...
    def list_projects(self) -> list["ProjectState"]: ...
    def list_payments(self) -> list["PaymentState"]: ...
```

Provider-specific modules may define transport payloads, but they may not rename or weaken these
kernel identities.

## Phase A — Preserve and expose the existing kernel

### Task 0: Record the production baseline

**Files:**
- Create: `docs/superpowers/evidence/gig-expansion-baseline.md`

**Interfaces:** Produces the Coconala source/release identities, active repair cursor, browser owner,
four configured lane-owner identities with their live observed states, state paths and focused test
commands used by every later task.

- [x] Record `origin/main`, current release symlink target, four configured owner identities plus
  their observed launchd/process states, and the active
  `skills/earn/gig/TODO.md` item without changing them.
- [x] Record `df -k /`, current disk-guard result and private runtime directories without copying
  their contents.
- [x] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
  skills/earn/gig/tests/test_application_direct_reconcile.py
  skills/earn/gig/tests/test_storefront_direct.py`.
- [x] Write exact pass/fail counts and command output summary into the evidence file.
- [x] Commit with `docs(gig): record expansion baseline` and push.

### Task 1: Define the action-level authorization receipt

**Files:**
- Create: `skills/earn/gig/scripts/provider_authorization.py`
- Create: `skills/earn/gig/config/provider-capabilities.public.json`
- Create: `skills/earn/gig/tests/test_provider_authorization.py`

**Interfaces:** Produces `AuthorizationReceipt` and
`authorize(provider, account, action, transport, now) -> AuthorizationDecision`.

- [x] Write failing tests asserting missing, expired, wrong-account and wrong-action evidence returns
  `unknown`, while an exact unexpired special approval returns `approved_browser`.
- [x] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
  skills/earn/gig/tests/test_provider_authorization.py`; confirm import/test failure.
- [x] Implement strict JSON parsing for `approved_api`, `approved_browser`, `approved_assisted`,
  `denied`, `unknown`; reject extra keys and invalid timestamps.
- [x] Seed every public provider/action as `unknown`; keep private receipts in
  `~/.config/anicca/gig/authorizations.json` mode `600`.
- [x] Run the focused test plus `python3 -m json.tool` on the public config; commit/push.

### Task 2: Define the provider adapter contract

**Files:**
- Create: `skills/earn/gig/scripts/provider_adapter.py`
- Create: `skills/earn/gig/tests/test_provider_adapter.py`

**Interfaces:** Produces immutable `Opportunity`, `EffectIntent`, `ProviderReceipt`, `ProjectState`,
`PaymentState` and the eight adapter operations from the design.

- [x] Write a failing contract test with a minimal fake adapter; assert provider IDs, currency,
  source hash and observed timestamp are mandatory.
- [x] Run the focused test and confirm the types are absent.
- [x] Implement frozen dataclasses and a runtime contract validator using only the standard library.
- [x] Assert `execute()` output cannot be converted to success without `readback()` returning the
  matching provider/action/effect key.
- [x] Run focused tests and commit/push as `feat(gig): define provider adapter contract`.

### Task 3: Bind authorization to the existing effect fence

**Files:**
- Modify: `skills/earn/gig/scripts/application_effect_fence.py`
- Modify: `skills/earn/gig/scripts/connector_outbox.py`
- Create: `skills/earn/gig/tests/test_provider_effect_authorization.py`

**Interfaces:** Consumes `AuthorizationDecision`; persists `authorization_hash` on every new-provider
intent while preserving all existing Coconala effect keys.

- [x] Write failing tests for missing/revoked authorization, changed authorization hash, duplicate
  intent and lost-ACK reconciliation.
- [x] Capture existing Coconala fixture effect keys byte-for-byte before implementation.
- [x] Add the authorization hash only to the provider-generic path; do not migrate or rewrite
  Coconala history.
- [x] Prove a changed receipt cannot reuse an old effect, and a same receipt/payload replay performs
  zero effects.
- [x] Run both new tests and existing application reconcile tests; commit/push.

### Task 4: Add Market Factory durable state

**Files:**
- Create: `skills/earn/gig/scripts/market_factory.py`
- Create: `skills/earn/gig/tests/test_market_factory.py`

**Interfaces:** Produces `advance_market(provider, evidence) -> MarketStage` with stages
`research, authorized, read, sale, contract, delivery, payment, repeatable, active, assisted,
denied, unprofitable`.

- [x] Write failing transition tests; direct `research → sale`, payment without delivery and active
  without three independent payments must fail.
- [x] Run the test to observe the missing implementation.
- [x] Store stages and evidence hashes in the existing SQLite database; add no service or scheduler.
- [x] Make every transition monotonic except explicit `paused/reverted`; repeat input is idempotent.
- [x] Run focused tests and commit/push.

### Task 5: Add the typed human-ceremony queue

**Files:**
- Create: `skills/earn/gig/scripts/human_ceremony.py`
- Create: `skills/earn/gig/tests/test_human_ceremony.py`

**Interfaces:** Produces `request_ceremony(kind, provider_state, resume_predicate)` for identity,
financial, physical capture and client-reserved acts only.

- [x] Write failing tests that reject vague requests, missing provider resume evidence and tasks the
  agent can execute under authorization.
- [x] Implement a durable bounded record with deadline, provider URL, exact act and resume predicate.
- [x] Prove another provider lane remains runnable while one ceremony is pending.
- [x] Prove completion requires authoritative changed provider state or a bound artifact hash.
- [x] Run focused tests and commit/push.

### Task 6: Add local onboarding and capability inventory

**Files:**
- Create: `skills/earn/gig/scripts/money_loop_onboarding.py`
- Create: `skills/earn/gig/tests/test_money_loop_onboarding.py`
- Create: `skills/earn/gig/install.sh`

**Interfaces:** Produces a private owner profile, Skill inventory, per-provider browser profile,
authorization matrix, spend/capacity bounds and onboarding receipt.

- [x] Write a failing isolated-home test proving install leaks no credential, customer data, private
  authorization evidence or original operator path into tracked files.
- [x] Implement owner-only directories, explicit provider selection and safe `unknown` defaults.
- [x] Collect minimum margin, spend/Connects cap, concurrent-job cap and human-minute value; reject
  negative or non-numeric bounds.
- [x] Run one read-only local capability inventory with no marketplace mutation.
- [x] Run isolated-home tests and commit/push.

## Phase B — Upwork first complete autonomous adapter

### Phase B immediate execution SSOT

No later task may jump ahead of the first incomplete row:

| Order | Atomic outcome | Completion evidence |
|---:|---|---|
| U1 | Resolve existing-account vs signup using the owner email | **DONE:** owner confirmed no account; new freelancer signup completed with normal email flow |
| U2 | Complete normal email/password signup or login | **DONE:** verification email completed; fresh password login returned the same identity twice |
| U3 | Complete factual freelancer profile needed to apply | **DONE:** published profile `~01f5fe272d6df34084`; Online, >30 hrs/week, 40% complete |
| U4 | Observe real job-search, detail and proposal surfaces | **DONE:** search/detail/proposal-entry receipt; 0 effects, Connects gate identified |
| U5 | Discover live jobs twice | **DONE:** two recency reads returned the same ten job IDs; 0 effects |
| U6 | Exercise qualification on one observed job | **DONE, PARKED:** technical/margin qualification proved on `~022091070478975551162`; 50+ proposals and 26 Connects make it unsuitable as the first target |
| U7 | Exercise immutable proposal freezing | **DONE, PARKED:** payload `9fab22a2…10d19` retained for later requalification; zero marketplace effects |
| U8 | Add the required factual Employment History item | **DONE:** official employment readback matches owner evidence; Find Work progressbar is 70% |
| U9 | Publish three reusable proofs and complete optional profile items | **DONE:** three public project IDs and bound hashes, factual A10 Lab history, public EEG/ML Other Experience readback, and official `100% completed` |
| U10 | Discover and qualify a first-job candidate | **DONE:** usability-test job `~022091106411892491962`; $15, 10–15 proposals, zero interviews, payment/phone verified, and all student/age/English/recording gates match owner evidence |
| U11 | Resolve application capacity for that candidate | **DONE:** official proposal surface requires 7 Connects; balance/history, offers, invites and proposals are 0, no reward banner is exposed, and the only buy offer is 100 for $15 plus tax |
| U12 | Freeze one tailored first-job proposal | **DONE:** immutable payload `c37eed9c…c68e926` contains the $15 terms, cover letter, five factual screening answers, no attachments, and zero unsupported claims |
| U13 | Activate every zero-spend acquisition path | **IN PROGRESS:** the bounded Project Catalog service is approved, visible and monitored; inspect remaining factual free-reward tasks, monitor invitations/direct offers, retain three sealed public-job candidates and reconcile all official states into one inventory |
| U14 | Close the first zero-spend acquisition effect | Accept one qualified invitation/direct offer or Project Catalog order, or submit the best sealed public-job proposal when granted/returned Connects cover its exact cost; never purchase capacity; verify official IDs and balance readback |
| U15 | Replay immediately | Same proposal ID; zero new proposal and zero additional Connects |
| U16 | Poll and answer the resulting thread | Official story/message IDs and no duplicate reply |
| U17 | Negotiate and accept profitable terms | Offer ID, exact terms hash and active contract ID |
| U18 | Fulfill and independently verify the work | Artifact hash and independent verifier PASS |
| U19 | Deliver once | Official submission ID/state and replay with zero duplicate delivery |
| U20 | Reconcile money and review | Received transaction, fee, costs, payout and honest review evidence |
| U21 | Repeat on three independent paid jobs | Three contract/payment/review IDs and complete per-job economics |

Later implementation tasks are renumbered only when their first incomplete outcome becomes active.
All cross-market tasks remain frozen until the first received Upwork payment closes.

U3 closure evidence: factual profile `~01f5fe272d6df34084` is published with the authentic owner
photo, Status Online and More than 30 hrs/week. The official completion meter is 40%, identity is
Unverified and Connects is 0. Observe the real search, detail and proposal entry next to determine
which of those states is an actual submission gate. Live totals remain 0 applications, 0
conversations, 0 contracts and USD 0 received revenue.

U4 observed query `AI automation Python`, 315 result pages and ten stable job IDs. Detail job
`~022091070238314681977` exposed title, description, skills, budget, client verification/history,
activity and Connects fields. Its entry button is `Buy Connects to apply`: 18 required versus 0
available. No proposal, Connects spend or payment occurred. U5 is now the first incomplete outcome.

U5 repeated the same `AI automation Python` recency discovery twice. Both reads returned the same
ordered ten job IDs, including `~022091072411475953338`, `~022091070478975551162` and
`~022091070238314681977`. Saved jobs remained 0; proposals, messages, Connects spend and payments
remained 0. U6 is now the first incomplete outcome and must qualify one of these live jobs against
the installed Skills and Upwork-only delivery capacity.

U6 selected `~022091070478975551162`, a fixed-price $3,000 multi-tenant product-similarity and
feedback-reranking API. Live detail evidence showed 26 Connects, 50+ proposals, 0 interviews,
payment and phone verification, a 75% client hire rate and $2.1K client spend. The conservative
qualification reserves $300 fee, $3.90 Connects, $300 risk and $1,350 labor value, leaving expected
net $1,046.10. Installed `earn/upwork-ai-api-delivery` explicitly covers the job's summarization,
image-analysis, classification, AI integration, API, multi-tenant ranking and feedback-reranking
capabilities. Independently hashed `test-contract` verifies API and state invariants; job-required
capability subsets and both Skill hashes are bound to the retained full-scope observation. Current
Upwork capacity is 0 of 3. This proved the qualifier's technical and margin contracts but not
first-contract probability; 50+ proposals, 26 Connects, broad scope and a 40%-complete new profile
violate the corrected first-job bootstrap gate. The candidate is parked.

U7 froze a $3,000, 21-day proposal with three milestones: $600 ranking contract/acceptance dataset,
$1,400 tenant-isolated similarity API and $1,000 feedback-reranking verified handoff. The exact body
binds `multi-tenanted`, `visual appearance`, `user feedback` and `HTTP/JSON API` from the observed
scope. Unsupported claims and attachments are both empty. Payload hash is
`9fab22a29ea169632f30c3d1a22597c1091ecb97a2897c987ac788ce1d110d19`. The payload remains a
valid effect-fence fixture and later requalification candidate, not the first live submission.
Marketplace effects remain zero.

The observed purchase entry offers 100 Connects for $15 plus tax, but it is no longer a pending
gate. U8 first adds Upwork's required factual Employment History item and records the new baseline.
U9 has published all three proofs as projects `2091143267699150848`, `2091143845069127680`, and
`2091144398831636480`. GitHub web linking had no credential/session, so U9 used the factual A10 Lab
Marketing Intern history instead; official completion now reads 95%. It next adds one truthful Other
Experience item; official completion now reads 100%. The unfinished Project Catalog item remains a
private draft and returns as a zero-spend inbound bootstrap task. U10 searches and qualifies the first paid-job candidate; U11 records
the exact proposal Connects requirement and resolves only the capacity needed for that candidate.
Project Catalog publishing is not required for public applications, but is required as a separate
zero-Connect inbound acquisition path. Purchased Connects,
Freelancer Plus, Availability Badge and boosts stay disabled without separate authorization.
Application, Connects-spend and payment effects remain zero. U13 continues now: it refreshes the
existing candidate and prepares at least two independent backups instead of waiting passively for a
non-guaranteed free Connects refill. The same wake also reconciles every existing application and
records whether it is submitted, viewed, messaged/interviewing, offered, contracted, declined,
archived, job-closed, platform-removed or unknown. Missing from one page never means stopped.

U13 atomic order:

1. **DONE:** Implement the production CloakBrowser provider entrypoint for the dedicated `gig-upwork`
   profile. Live hidden-target readback persisted Connects 0/no transactions, Offers 0, Invites 0,
   Active proposals 0, Submitted proposals 0 and the working-style account task; 38 focused tests
   pass. The SHA-fixed five-minute launchd label completed two wakes with exit 0, stable evidence
   hashes, zero stderr and no external marketplace effect.
2. **DONE:** the working-style assessment is completed from the actual Life Manager operating
   principles rather than invented personal history. Upwork's official result exposes `Accountable
   for outcomes` and `Detail-oriented` as `Shown on profile`, with retake eligibility after August
   22, 2027; Connects History remains 0, so no reward is invented. The provider now reads the
   durable assessment-results page on every wake and lets that official completion override the
   stale Find Work `Take the working style assessment` banner. Fourteen focused tests and the live
   result receipt prove `account_tasks=[]` and `working_style.completed=true`.
3. **DONE:** the bounded service `You will get a Python script integrating one documented REST API
   endpoint` is approved and visible at
   `https://www.upwork.com/services/product/development-it-a-python-script-integrating-one-documented-rest-api-endpoint-2091146976410620036`.
   The official dashboard reads Approved 1, Under Review 0, Drafts 0, Views 0 and Orders 0. Its owned
   1600x1200 gallery image, one required client-input question, three delivery steps, $75 price,
   three-day delivery, one revision and one-project concurrency cap are persisted. The five-minute
   provider now fail-closed reads the Catalog inventory alongside Connects, invites, offers and
   proposals; seven focused tests and a live four-page E2E pass. Immutable release `d6c28857e`
   completed a production launchd wake with exit 0 and persisted the same official zero-order state.
4. **DONE:** the authenticated six-page read joins official-link-derived stable inventories for
   invitations, proposal/offers, active contracts, message rooms and unread room IDs. The one-time
   Messages anti-circumvention acknowledgement is completed in Upwork; no message was sent. Current
   official readback is empty arrays for every entity class, zero invitations/offers/proposals/
   contracts, and `earnings_available_usd_minor=0`. The provider refuses a missing empty-state or a
   positive row without a stable official href; nine focused tests and the live E2E pass.
5. **DONE:** official proposal links are persisted separately as offer, active, submitted and
   fail-visible unclassified stable-ID arrays. Current official Active 0 and Submitted 0 readback
   produces empty arrays for both without inventing an application effect.
6. **DONE:** the public candidate config drives official detail reads on every five-minute wake and
   records `open`, `closed`, `removed` or fail-visible `unknown` only from Upwork markers. Live E2E
   reads primary `~022091106411892491962` open/7 Connects, parked
   `~022091070478975551162` open/26 Connects, and historical
   `~022091070238314681977` closed with `This job is no longer available`; every row carries its own
   evidence SHA-256. Eleven focused tests pass.
7. **DONE:** a mode-600, flocked JSONL ledger records each `closed` or `removed` transition with
   deterministic event ID, prior/next state, official reason, observation times and receipt hash.
   Ledger fsync precedes atomic state replacement, so a crash cannot silently lose the event; replay
   uses the same source observation identity and cannot duplicate it. Two live nine-page reads
   produced one 367-byte closed event on the first pass and `appended=0` with identical ledger
   SHA-256 on the second. Thirteen focused tests pass.
8. **DONE:** candidate `~022091106411892491962` still exposes the official 7-Connect proposal entry,
   so it remains in the ready queue rather than being falsely retired. Balance remains 0 and no
   proposal effect occurred.
9. **DONE:** repeated authenticated searches rejected already-hired, oversized, geographically
   incompatible and unsupported-experience jobs, then produced three currently open sealed
   candidates: usability test `~022091106411892491962` (7 Connects), Telegram/Sheets/Gemini
   workflow `~022091182433542935908` (11 Connects), and Neuroflow authentication repair
   `~022091170260597544595` (9 Connects after Upwork changed the earlier live value of 7). Each
   official detail receipt shows a proposal entry and
   Available Connects 0; none was submitted. Every ready public row carries the SHA-256 of its
   factual, job-specific private proposal; the three private payloads contain no unsupported claim,
   recompute to their recorded hashes, and are stored in a mode-700 directory as mode-600 files.
   Fourteen focused provider tests pass and the receipt-backed parser returns three `open` rows.
10. **DONE:** the production five-minute read opens official Connects History and currently returns
    balance 0 with `No Connects transactions.` Therefore granted, returned and consumed Connects are
    all observed as zero, not inferred as a future refill. The loop keeps purchase, membership,
    boost, billing, withdrawal and public-job submission disabled; only a later official positive
    history/balance read or a zero-Connect invitation/direct offer can unlock an acquisition effect.
11. **DONE:** two consecutive production launchd reconciliations completed with exit 0 at official
    observations `2026-08-22T16:51:09.769019+00:00` and
    `2026-08-22T16:52:45.538216+00:00`. Across both runs the mode-600 transition ledger stayed
    394 bytes with SHA-256 `e49adcc6ac3bd4db201c5275520458f8c5b7d819b2d8212bb8295ecb7b3d576b`,
    total transitions stayed 1, and each run appended 0. Balance, submitted proposals, invitations,
    offers, active proposals and earnings all stayed 0; the three sealed jobs stayed open at
    7/11/9 Connects with identical proposal hashes. An earlier attempt exited 120 while a concurrent
    release expansion exhausted disk headroom; it wrote neither state nor ledger effect. Replaying
    after that producer stopped proved recovery without a duplicate marketplace or ledger effect.

U14 atomic order:

Connects bootstrap truth, in plain language:

1. A Connect is an Upwork application ticket. A public job chooses its own ticket price. Seeing
   `7 Connects` on a job means applying costs seven tickets; it does not mean seven applications
   were already sent.
2. The current account has zero tickets and an empty official Connects History. Therefore it has
   sent zero proposals and spent zero tickets. The loop must never infer an application from a job's
   displayed price.
3. There is no general class of beginner public jobs that costs zero Connects. Public proposals use
   Connects. The verified zero-Connect acquisition paths are a client invitation, a Direct Offer,
   and a client purchase of an approved Project Catalog project.
4. Upwork may award free Connects for eligible onboarding tasks, selected monthly offers, talent
   badges, some interviews, and temporary experiments. None is guaranteed to every new account.
   The only usable balance is the positive amount actually read from official Connects History.
5. The zero-spend bootstrap is therefore two parallel lanes: keep the profile and approved Catalog
   project attractive enough to generate free inbound work, while checking official Connects
   History every five minutes. When free tickets appear, spend only the exact required amount on the
   strongest fresh, narrow, provable public job. Never purchase Connects, membership, boosts or a
   badge under this policy.
6. Beginner case studies do not reveal a hidden free-public-job category: successful zero-cash
   starts use awarded/free Connects selectively or receive an invitation. Their reusable lesson is
   narrow positioning, matching external proof, fresh low-competition jobs and a short specific
   proposal—not mass application.

Sources: Upwork Help, "Understanding and using Connects",
https://support.upwork.com/hc/en-us/articles/211062898-Understanding-and-using-Connects;
Upwork Help, "How to respond to an invitation to apply on Upwork",
https://support.upwork.com/hc/en-us/articles/211063018-How-to-respond-to-an-invitation-to-apply-on-Upwork;
Upwork Help, "How direct offers from clients work on Upwork",
https://support.upwork.com/hc/en-us/articles/30113729524499-How-direct-offers-from-clients-work-on-Upwork;
Leverage Proposals, "How to Get Your First Upwork Job",
https://leverageproposals.com/guides/how-to-get-first-job-on-upwork.

1. **DONE:** the observer now selects a public-job action only when the official free balance covers
   that live job's exact Connects cost. It then requires the private proposal directory to be mode
   700, the exact job file to be mode 600, and its provider, job ID, official URL identity, source
   hash, status, Connects, unsupported-claim list and canonical JSONL SHA-256 to match the public/live
   row. Balance 0 returns before private payload access. Focused tests pass 16/16; an isolated
   balance-7 validation against the real private SSOT selected `~022091106411892491962`, required 7
   Connects and matched its sealed hash without browser or marketplace effect. Production release
   `220a6ebbc` then completed its launchd wake with exit 0 at
   `2026-08-22T17:07:32.599713+00:00`: balance 0 produced `waiting_free_capacity`, public submit
   permission false, and zero proposals, invitations, offers, earnings or transition append.
2. **CODE COMPLETE / LIVE POSITIVE-CAPACITY READBACK PENDING:** the click-free preflight contract now requires the live apply URL, job ID,
   exact Connects, bid, delivery, cover letter, ordered screening answers, attachments, enabled
   submit label and zero validation errors to match the sealed payload. It returns only job ID,
   Connects and an evidence hash, never proposal copy. Focused provider/preflight tests pass 21/21.
   The OSS comparison fixed `MSarfarazMeyo/upwork-auto-apply-bot` at commit
   `e2bfc46dcfdf81b303cae7745102725457286e3`; its real entrypoint confirms apply URL
   `/ab/proposals/job/{id}/apply/#/`, `.cover-letter-area textarea`,
   `.fe-proposal-job-questions textarea`, duration combobox and footer primary button. Its automatic
   Connects refill, generic default answers and duplicate-as-success behavior are rejected. The
   `swindon/upwork-proposals-chrome-extension` commit
   `13e80c143f1c3aa5fbbad3407b8552c790a5f70d` supplies job-title/description selector fallbacks but
   has no submit/readback path. Production commit `ff86c9e09` adds the hidden-target fill using
   native setters plus `input`/`change` events for bid, duration, cover letter and exact screening
   questions. A real isolated Chrome-for-Testing apply-page fixture proves all sealed values are
   present while the submit button remains unclicked; the combined provider/preflight suite passes
   22/22. Release `485eab85ad8f` contains that commit. The production five-minute loop then completed
   an official read at `2026-08-22T17:25:20.808350+00:00`: balance 0, submitted proposals 0,
   invitations 0, offers 0, available earnings USD 0 and `waiting_free_capacity`. The three live
   ready rows require 7/14/9 Connects, so the balance gate correctly prevented private payload access,
   form fill, click, purchase or any marketplace effect. A positive live Upwork form read remains
   pending until Upwork supplies free capacity that covers an exact live job cost.
3. **CODE COMPLETE / FIRST LIVE EFFECT PENDING:** after a positive official balance selects a sealed
   job, the same hidden target now fills the exact form, requires its live `Available Connects` to
   cover the exact job cost, validates the click-free preflight, and calls the shared durable provider
   fence before the only submit expression can run. A denied or replayed fence produces zero clicks.
   A click requires an official non-job proposal URL/ID, then a fresh Connects History read whose
   balance is exactly `pre - required`; missing IDs, wrong deltas and timeouts remain
   `reconcile_unknown` and are never blindly retried. The private authorization resolves exactly one
   active Upwork propose account and the existing daily-driver profile; no new browser, queue or
   service was added. The focused browser/fence/legacy crash matrix passes 51/51. Production release
   `4c14d4e45` completed its five-minute wake with exit 0 at
   `2026-08-22T17:43:25.669314+00:00`: balance 0, proposals 0, invitations 0, offers 0, available
   earnings USD 0, `waiting_free_capacity`, provider-effect rows 0 and transition appends 0. The
   shared outbox is now forced to mode 600 before it can store sealed proposal content. The only
   remaining proof for this public-job effect is a real free-capacity event followed by one official
   proposal ID and its exact Connects delta. Invitations/direct offers remain separate zero-Connect
   acquisition effects.
4. **DETECTION COMPLETE / FIRST LIVE INBOUND PENDING:** the five-minute observer now routes a stable
   direct offer before an invitation, an invitation before a public-job proposal, and a positive
   Catalog order count before `waiting_free_capacity`. Offer and invitation packets require an exact
   official Upwork HTTPS URL containing the stable resource ID. A positive Catalog count without an
   order ID is fail-visible as `catalog_order_identity_pending`, never treated as an executable
   title-based identity. In the same wake, an offer/invitation packet opens its official detail URL
   read-only and marks it `actionable` only when the matching accept/proposal control and decline
   control both exist; missing controls remain `unknown`. Focused inbound/provider tests pass 23/23.
   An actionable detail is sealed as a mode-600 private packet inside a mode-700 local queue; the
   public state exposes only its SHA-256 and never the client text. Release `db40a86c8` completed a
   zero-inbound wake at `2026-08-22T17:55:40.995152+00:00` with exit 0 and private packet files 0→0,
   proving empty inventory cannot create model work or an external effect.
   Production release `adb317892` completed with exit 0 at
   `2026-08-22T17:51:55.687566+00:00`: invitations 0, offers 0, Catalog orders 0, public proposals 0,
   earnings USD 0 and provider-effect rows 0. Next, when an invitation is actionable, bind its exact
   official detail evidence to a zero-Connect sealed proposal payload through the existing
   `application-intent-planner` before reusing the U14-3 preflight/fence/official-ID path.
5. **CODE COMPLETE / FIRST LIVE INVITATION PENDING:** an actionable invitation packet now enters the
   existing provider-agnostic `application-intent-planner` through its stdin/schema/evidence
   contract. The schema permits only truthful submit/skip decisions; mechanical validation rebinds
   job ID, official URL and detail evidence, requires Connects 0, bounded price/delivery, exact
   screening answers, no unsupported claims and no attachments, then seals submit decisions in a
   separate mode-700/600 store. A successful runner summary is reused by packet hash, preventing a
   model call on every five-minute replay. The invitation browser enters through the official
   accept/send-proposal control, rejects any positive Connects amount, fills the exact sealed form,
   and reuses the same durable effect, single-click, proposal-ID and exact zero-Connect-delta path as
   public proposals. Direct offers do not enter this planner and remain at `terms_gate_pending`.
   The unified planner/browser/crash suite passes 53/53. Production release `73a0979ec` completed
   with exit 0 at `2026-08-22T18:07:39.554042+00:00`: invitations 0, planner files 0, sealed inbound
   proposals 0, provider-effect rows 0, marketplace proposals 0 and earnings USD 0. The remaining
   invitation proof is one real inbound followed by one official proposal ID; the next independent
   zero-Connect effect is direct-offer terms qualification and exact contract acceptance readback.
6. **TERMS GATE COMPLETE / FIRST LIVE DIRECT OFFER PENDING:** an actionable Direct Offer now enters
   a separate schema-bound decision through the existing `application-intent-planner`; it does not
   require or create a proposal. The exact offer ID, official URL and detail evidence hash must bind
   mechanically. `accept_ready` requires a nonempty feasible scope, positive amount/rate, explicit
   ISO deadline, an enabled accept state, no off-platform payment/contact, no synchronous or physical
   requirement, and payment protection. Fixed-price additionally requires a funded milestone that
   covers the full accepted amount; hourly additionally requires verified billing and a positive
   weekly hour limit. Missing negotiable terms become `request_changes`; unsafe or infeasible work
   becomes `decline`; neither produces an executable offer. Schema validation and the focused
   proposal/inbound/browser/effect matrix pass 52/52. Release `dfcc24217` completed a production
   five-minute wake with exit 0 at `2026-08-22T18:17:02.699584+00:00`: Connects 0, proposals 0,
   invitations 0, offers 0, earnings USD 0, Direct Offer evidence files 0 and private inbound packets
   0. Therefore an empty inbox created no model call and no marketplace effect. The next atomic item
   is the durable single-click Direct Offer acceptance effect plus official active-contract readback.
7. **CODE COMPLETE / FIRST LIVE DIRECT OFFER PENDING:** an `accept_ready` decision now resolves the
   exact private `accept_offer` browser authorization, hashes the complete bound decision, validates
   the live offer URL/title/scope/amount/deadline/payment-protection markers and enabled exact
   `Accept offer` control, then durably changes the shared provider-effect row to
   `reconcile_pending` before the only click expression. A replay can never start a second click.
   Verification requires an official Upwork `/workroom/{contract_id}` readback; a missing or
   ambiguous contract ID stays `reconcile_unknown` and is never blindly retried. The same existing
   connector outbox and browser profile are reused; no new service or executor exists. The focused
   offer/proposal/inbound/browser/effect matrix passes 60/60. Release `e8ee5a7db` completed a
   production five-minute wake with exit 0 at `2026-08-22T18:24:49.980181+00:00`: Connects 0,
   invitations 0, offers 0, submitted proposals 0, active contracts 0, earnings USD 0, private offer
   evidence 0 and `accept_offer` effect rows 0→0. Therefore empty inventory generated no click or
   durable mutation. One real Direct Offer is still required for the official contract-ID proof.

### Task 7: Record Upwork's private action matrix

**Files:**
- Create: `skills/earn/gig/config/upwork-actions.public.json`
- Create: `skills/earn/gig/tests/test_upwork_authorization.py`

**Interfaces:** Declares search, inspect, propose, message, accept offer, deliver milestone, read
payments and read payouts; private receipts determine API/browser transport.

- [x] Write a failing test requiring every named action and denying an unlisted action.
- [x] Add safe public `unknown` entries with official evidence URLs and terms retrieval hashes.
- [x] Record Dais's special approval privately for only its actual account/actions/transports.
- [x] Run authorization readback without printing account IDs, credentials or evidence content.
- [x] Run focused tests and commit/push the public template only.

### Task 8: Bootstrap and authenticate the owner Upwork account by email

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_transport.py`
- Create: `skills/earn/gig/tests/test_upwork_transport.py`

**Interfaces:** Produces one authenticated dedicated Upwork browser identity plus
`UpworkTransport.for_action(action)`. Account bootstrap uses only the owner's normal email/password
flow; API credentials may be connected after the live browser identity exists.

- [x] Write failing tests for API preference, approved browser fallback, expired authorization and
  zero transport.
- [x] Implement bounded OAuth2 token handling and existing CloakBrowser profile lookup without
  logging tokens/cookies.
- [x] Ensure API and browser share one logical effect identity.
- [ ] Read the owner email and existing credential facts from private SSOT without printing them.
- [ ] Open Upwork's email flow directly; DO NOT click Google, Apple or another social provider.
- [ ] Detect whether that email already owns an account; signup only when absent, otherwise login.
- [ ] Complete email verification from the owned mailbox when requested and persist new credentials
  to the private credential SSOT before closing the page.
- [ ] Complete only the factual minimum freelancer profile required to browse and apply.
- [ ] Run a real authenticated read-only identity probe and retain a redacted private receipt.
- [x] Run focused tests and commit/push.

Current evidence: no authenticated Upwork identity exists. The dedicated profile is on Upwork Login
and the previous Google session is expired. That route is rejected by the updated design and MUST NOT
be resumed. The next action is the normal owner email flow. The private special-approval receipt is
authorization evidence only; it is not authentication evidence.

### Task 9: Discover and normalize Upwork jobs

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_adapter.py`
- Create: `skills/earn/gig/tests/test_upwork_discovery.py`

**Interfaces:** Implements `discover()` and `inspect()` returning canonical opportunities.

- [x] Write fixture tests requiring job ID, URL, title, full scope, skills, currency, budget/rate,
  client evidence, activity, Connects cost and observed timestamp.
- [x] Reject partial rows, deleted jobs, stale identities and unsupported currencies.
- [x] Implement bounded cursor pagination through the selected authorized transport.
- [ ] Run one live discovery twice; assert stable IDs and zero proposal/message effects.
- [x] Run focused tests and commit/push.

Implementation evidence: Upwork's official [GraphQL API documentation](https://www.upwork.com/developer/documentation/graphql/api/docs/index.html)
is the provider schema authority. Code comparison used the official Python SDK at
`upwork/python-upwork-oauth2@9bee35b` for the GraphQL POST boundary,
`tryAGI/Upwork@7346170` for `pagination.after/first`, `pageInfo.endCursor/hasNextPage`, money,
client and activity shapes, and `furkankoykiran/upwork-mcp@9ed7b44` only to cross-check the
Connects field. The MCP formatter and its non-advancing search pagination were not copied.
The live-twice checkbox remains open because Task 8 has not yet produced an authenticated email-flow
identity. Fixture replay proves only normalization behavior; it is not live-market evidence.

### Task 10: Qualify jobs against installed Skills and capacity

**Files:**
- Create: `skills/earn/gig/scripts/opportunity_qualifier.py`
- Create: `skills/earn/gig/tests/test_opportunity_qualifier.py`

**Interfaces:** Produces `Qualification(eligible, workflow, expected_net, risks, evidence)`.

- [x] Write failing tests for missing Skill, impossible deadline, capacity exhaustion, negative
  expected net, unverifiable deliverable and false profile claim.
- [x] Reuse the installed Skill registry and **Upwork-only** active-contract capacity; do not read
  Coconala projects or talkroom states.
- [x] Calculate expected net from observed budget/rate, fee, Connects, tool cost and risk reserve.
- [x] Require a concrete workflow and independent verifier before `eligible=true`.
- [x] Run focused tests and commit/push.

Task 10 code evidence: qualification binds installed builder/verifier Skill hashes, owner bounds and
conservative gross/fee/Connects/tool/risk/labor economics. Its previous live canary incorrectly used
Coconala project state as Upwork capacity; that result is void and the Upwork-only capacity checkbox
is reopened. The next qualifier revision scopes every project read by `provider == "upwork"` and
starts at zero until an official Upwork contract receipt exists.
Upwork fee and Connects costs remain observed inputs rather than hard-coded policy because current
official values can vary. Sources: Upwork Help, "Learn about the Freelancer Service Fee",
https://support.upwork.com/hc/en-us/articles/211062538-Learn-about-the-Freelancer-Service-Fee;
Upwork Help, "Understanding and using Connects",
https://support.upwork.com/hc/en-us/articles/211062898-Understanding-and-using-Connects. OSS comparison:
`ABerger94/ai-native-opportunities@17cda3d0b5bd7fc7cb0017dad6eff23075c430fd` informed the
required/missing-skill split; its arbitrary weighted resume-keyword score was rejected because it
does not prove an installed workflow, capacity, economics or independent verification.

### Task 11: Generate evidence-bound Upwork proposals

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_proposal.py`
- Create: `skills/earn/gig/tests/test_upwork_proposal.py`

**Interfaces:** Produces immutable proposal payload with job evidence, price, milestones, delivery
workflow, claims evidence and payload hash.

- [x] Write failing tests for generic copy, unsupported claims, absent scope reference, price outside
  bounds and missing deliverability proof.
- [x] Generate one tailored proposal from official job facts and factual owner assets only.
- [x] Bind price and milestone dates to the qualification/capacity receipt.
- [x] Freeze the exact body and attachments before creating an effect intent.
- [x] Run focused tests and commit/push.

Task 11 evidence: the pure sealer consumes the canonical `UpworkOpportunity` produced by Task 9
and the eligible `Qualification` produced by Task 10. It rejects generic copy, missing or fabricated
scope references, unsupported profile claims, bids outside the observed job range, fixed-price
milestones whose amounts do not sum to the bid or whose dates exceed the qualified deadline, absent
independent verification, and mismatched/ineligible qualification. The frozen payload binds the job
source hash, qualification hash, exact cover letter, claim receipts, terms, milestones, builder and
verifier before Task 12 creates any effect intent. Task 10 evidence now also includes evaluated time,
qualified deadline and capacity cap, closing the downstream binding gap found during this task.
Twenty-three focused Task 10/11 fixture tests pass. The prior `qualification_ineligible` live claim
based on Coconala capacity is void; Task U6 must be rerun with Upwork-only capacity after authenticated
discovery. Marketplace effects remain zero. Upwork Help states that a proposal
sets hourly/fixed terms, project-or-milestone payment, duration and cover letter:
https://support.upwork.com/hc/en-us/articles/211062998-How-to-submit-a-proposal-on-Upwork.
Upwork Help also says fixed milestones should agree amounts, deliverables and deadlines before work:
https://support.upwork.com/hc/en-us/articles/211068218-How-to-use-milestones-in-fixed-price-jobs.
OSS comparison: `vivekanandtech/upwork-proposal-automation@496a388a52e2fc158ec88387008f3caff481d2b2`
contributed the useful pattern of opening from an exact job detail and carrying job fields into the
proposal record. Its free-form hard-coded profile claims, Airtable write and Slack notification were
rejected: they do not bind qualification, factual assets, pricing, milestones or an immutable effect
identity.

### Task 12: Submit one Upwork proposal exactly once

**Files:**
- Modify: `skills/earn/gig/scripts/connector_outbox.py`
- Modify: `skills/earn/gig/scripts/providers/upwork_adapter.py`
- Create: `skills/earn/gig/tests/test_upwork_proposal_effect.py`

**Interfaces:** Implements `plan_effect(propose)`, `reconcile()`, `execute()` and `readback()`.

- [x] Write a failing crash matrix: before effect, lost ACK, provider timeout, success readback and
  repeated tick.
- [x] Persist authorization hash, job ID, proposal payload hash and Connects pre-state before effect.
- [ ] Execute one authorized proposal through API or CloakBrowser.
- [x] Require proposal ID plus Connects post-state; on uncertainty enter `reconcile_unknown`.
- [ ] Replay the same tick, assert zero new proposal and zero additional Connects; commit/push.

Task 12 kernel evidence: the outbox commits authorization, job, canonical payload, Connects pre-state
and evidence hash before any provider call. A compare-and-set allows only one concurrent executor to
submit; the loser returns without an effect. The executor re-hashes the entire durable proposal before
the CAS, so altered cover letter, bid or milestones cannot pass by retaining an embedded hash string.
Lost acknowledgements and timeouts enter `reconcile_unknown`; only matching proposal ID, job ID,
payload hash, submitted state and Connects post-state verify the effect. Forty-one focused proposal,
authorization, discovery and sealer tests pass, including two-worker concurrency and durable
cover-letter/bid tampering. Fresh adversarial review reports no blocker/high. Live submission and live
replay remain open behind the separately recorded $15 plus tax Connects purchase approval gate.

### Task 13: Collect Upwork conversations and offers

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_inbox.py`
- Create: `skills/earn/gig/tests/test_upwork_inbox.py`

**Interfaces:** Produces stable message/story, room, offer and contract identities.

- [x] Write focused tests for changed-head detection, duplicate events, edited terms and stale room
  state.
- [x] Implement bounded polling using the existing outbox identity pattern.
- [x] Persist buyer message before semantic work and bind it to job/proposal IDs.
- [x] Normalize offer amount, fee, milestones, deadline and current contract state.
- [x] Run a live read-only inbox reconciliation and focused tests; commit/push.

Task 13 code and zero-inventory evidence: each official room is opened read-only, bounded to twenty
per wake, and its normalized private head is stored in a mode-600 JSONL ledger under a mode-700
directory before Task 14 semantic work. Stable official links bind job, proposal and contract IDs;
missing links remain explicit empty arrays. Offer and contract heads normalize observed USD amounts,
fee basis points, milestones, ISO deadline and state without inventing absent fields. The event ID is
the provider/kind/resource/head hash, so the same head appends zero, a changed head advances the
revision, and a stale old head cannot duplicate. Public state exposes only IDs, revision and hashes,
never message copy. The related proposal/offer/contract/browser matrix passes 66/66. Production
descendant release `2b49386c1` containing `b2e9c2ac6` completed with exit 0 at
`2026-08-22T18:31:43.266441+00:00`: official rooms 0, unread rooms 0, offers 0, active contracts 0,
earnings USD 0 and `inbox_reconciliation={observed:0,appended:0,heads:[]}`; the private inbox ledger
remained absent. A real client head is still required for positive message/story-ID evidence.

### Task 14: Negotiate and message exactly once

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_negotiate.py`
- Create: `skills/earn/gig/scripts/providers/upwork_message_browser.py`
- Create: `skills/earn/gig/scripts/providers/upwork_message_effect.py`
- Create: `skills/earn/gig/tests/test_upwork_negotiate.py`
- Create: `skills/earn/gig/tests/test_upwork_message_effect.py`
- Modify: `skills/earn/gig/scripts/providers/upwork_browser_provider.py`

**Interfaces:** Produces accept, counter, clarify or decline decision and message intent.

- [x] Write focused tests for scope expansion, price below floor, impossible deadline, conflicting
  terms, near-duplicate reply and expired message identity.
- [x] Reuse the existing freshness, duplicate and immutable private-intent behavior.
- [x] Generate a decision from current official thread and capacity evidence.
- [x] Implement a durable one-click message effect that accepts success only after a new outgoing
  DOM story/message ID with the exact sealed body appears.
- [x] Prove replay cannot start a second click; run the related 84-test matrix and commit/push.
- [ ] Execute one real authorized client message and read back its official story/message ID.
- [ ] Replay that same live event and prove zero duplicate message.

Task 14 decision evidence: only a newly appended official `message_room` head enters the existing
`application-intent-planner`. The schema permits `accept_terms`, `counter`, `clarify`, `decline` or
`no_reply` and mechanically rebinds room URL/ID, event ID, head hash and revision. The same wake's
official active-contract count is checked against the private concurrent-job cap; accept/counter
requires explicit scope, positive price, nonnegative cost, exact recomputed margin at or above the
private floor, and a non-expired ISO deadline. A 0.92 similarity gate rejects near-duplicate prior
sealed replies. Each validated decision is immutable by source event in a mode-700/600 store and is
reused on replay without another model call. No message transport is called in this slice. The
related negotiation/inbox/browser/effect matrix passes 75/75. Release `e4284beaa` completed a
production wake with exit 0 at `2026-08-22T18:40:41.432545+00:00`: rooms 0,
`negotiation_intents=[]`, planner evidence files 0, sealed negotiation files 0, Upwork message effect
rows 0 and earnings USD 0.

Task 14 message-effect evidence: the browser preflight binds the current room URL and SHA-256 of the
normalized official room text before filling the exact sealed body. It requires one visible input,
one enabled Send control and no validation error, persists all pre-existing message IDs behind the
shared durable provider-effect fence, then permits one click. Success requires a newly appearing
outgoing element whose normalized body is exact and whose stable `data-id`, `data-message-id` or
`data-story-id` is present; click, elapsed time or URL alone never count. Replay cannot cross the
durable fence again. The related negotiation/inbox/browser/effect matrix passes 84/84. The code is
in main commit `b229a1822` and immutable production current
`6e95717c620e8aa66f18b420ba570f8833618097`; the deployed message-effect file SHA-256 is
`2c1f197094808fb0b1466fb7adbddc1fc47e0e269ada988a63ad5234215ec4a9`.
Production still has rooms 0, `negotiation_intents=[]`, Upwork message-effect rows 0 and earnings USD
0, so no live story/message ID or live replay is claimed. A current-release wake was requested but
the local Codex execution context failed the launchd preflight with `blocked_control_plane`
(`manager_not_aqua`, unreadable `gui/501`); the scheduled state remained at
`2026-08-22T18:46:29.413515+00:00`. The next Task 14 effect therefore remains event-driven: the first
real client head authorizes the message, then the same wake must capture the official ID and replay
proof. Until then the next buildable atomic item is Task 15's contract workspace/terms gate; it must
not fabricate an inbound room to force Task 14 positive evidence.

### Task 15: Accept an Upwork offer safely

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_contract.py`
- Create: `skills/earn/gig/tests/test_upwork_contract.py`

**Interfaces:** Produces canonical contract state and one acceptance effect.

- [ ] Write failing tests for terms differing from the accepted negotiation, capacity race, missing
  funding/milestone evidence and duplicate acceptance.
- [ ] Re-read official offer immediately before the effect.
- [ ] Persist offer terms hash and capacity reservation atomically.
- [ ] Execute one authorized acceptance and require active contract ID/state.
- [ ] Replay with no additional effect; run tests and commit/push.

### Task 16: Create an immutable project workspace

**Files:**
- Create: `skills/earn/gig/scripts/project_workspace.py`
- Create: `skills/earn/gig/tests/test_project_workspace.py`

**Interfaces:** Produces owner-only project directory, source manifest, workflow version, deadline,
artifact manifest and client-data policy.

- [ ] Write failing tests for path traversal, shared-client directory, missing contract scope and
  secret copied to public/log paths.
- [ ] Create one workspace from canonical contract data; mode all private state owner-only.
- [ ] Bind inputs and workflow version by SHA-256; preserve revisions rather than overwriting.
- [ ] Project canonical lifecycle events into `project_ledger.py`.
- [ ] Run focused tests and commit/push.

### Task 17: Execute the contracted Skill workflow

**Files:**
- Create: `skills/earn/gig/scripts/workflow_executor.py`
- Create: `skills/earn/gig/tests/test_workflow_executor.py`

**Interfaces:** Produces artifact versions, provenance, cost, elapsed time and execution receipt.

- [ ] Write failing tests for uninstalled Skill, changed contract scope, expired deadline budget,
  missing output and secret leakage.
- [ ] Execute only the workflow frozen at qualification/contract acceptance.
- [ ] Checkpoint each completed step and resume without repeating completed external effects.
- [ ] Record model/tool cost and artifact hashes in the private ledger.
- [ ] Run focused tests and commit/push.

### Task 18: Independently verify deliverables

**Files:**
- Create: `skills/earn/gig/scripts/deliverable_verifier.py`
- Create: `skills/earn/gig/tests/test_deliverable_verifier.py`

**Interfaces:** Returns `PASS`, `REVISE`, `BLOCKED` with contract clause, artifact hash and evidence.

- [ ] Write failing tests rejecting self-approval, wrong artifact hash, missing contract criterion,
  unsupported factual claim and private-data leak.
- [ ] Run deterministic validators before model review.
- [ ] Use an independent review context bound to exact contract and artifact hashes.
- [ ] Permit delivery intent only from `PASS`; route `REVISE` back to Task 17.
- [ ] Run focused tests and commit/push.

### Task 19: Deliver an Upwork milestone exactly once

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_delivery.py`
- Create: `skills/earn/gig/tests/test_upwork_delivery.py`

**Interfaces:** Produces submission ID/state and binds it to contract, milestone and artifact hashes.

- [ ] Write the lost-ACK/repeated-tick/changed-artifact failing matrix.
- [ ] Persist delivery intent only after independent `PASS` and fresh contract readback.
- [ ] Execute one authorized milestone submission with frozen message/files.
- [ ] Require official submission ID and `Submitted` state; reconcile before any resubmission.
- [ ] Replay with zero duplicate delivery; run tests and commit/push.

### Task 20: Process Upwork revisions

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_revision.py`
- Create: `skills/earn/gig/tests/test_upwork_revision.py`

**Interfaces:** Normalizes revision request, in-scope decision, new artifact version and resubmission.

- [ ] Write failing tests for duplicate request, out-of-scope work, changed deadline and overwritten
  original artifact.
- [ ] Bind revision to provider message/milestone identity.
- [ ] Route in-scope work through Tasks 17–19; route scope changes through negotiation.
- [ ] Record revision time/cost for economics.
- [ ] Run focused tests and commit/push.

### Task 21: Reconcile Upwork payment, fee and payout

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_finance.py`
- Create: `skills/earn/gig/tests/test_upwork_finance.py`

**Interfaces:** Implements `list_payments()` returning gross, fee, refund/chargeback, released state,
payout availability and provider transaction IDs.

- [ ] Write failing tests separating pending balance, released payment, available payout, refund,
  chargeback and missing source window.
- [ ] Normalize official transaction IDs and forbid one transaction in two accounting periods.
- [ ] Join payment to contract, delivery and actual execution cost.
- [ ] Recognize revenue only from complete released/received evidence; retain missing fields as
  `unknown`.
- [ ] Reconcile the first live payment and commit/push after focused tests pass.

### Task 22: Close the Upwork three-job repeatability gate

**Files:**
- Create: `skills/earn/gig/tests/test_upwork_repeatability_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

**Interfaces:** Advances Upwork from `payment` to `repeatable/active`.

- [ ] Write a failing gate for fewer than three independent contract/payment IDs, any duplicate
  effect, incomplete cost, late unhandled delivery or open reconciliation.
- [ ] Run three natural paid Upwork paths through Tasks 9–21; do not synthesize receipts.
- [ ] Reconcile every effect and payment from current provider state.
- [ ] Advance only when all three paths pass; otherwise persist the exact failed entity/stage.
- [ ] Run gate tests and commit/push.

## Phase C — Fiverr second complete adapter

### Task 23: Record Fiverr authorization and authenticated transport

**Files:**
- Create: `skills/earn/gig/config/fiverr-actions.public.json`
- Create: `skills/earn/gig/scripts/providers/fiverr_transport.py`
- Create: `skills/earn/gig/tests/test_fiverr_transport.py`

**Interfaces:** Covers Gig read/write, inquiry/message, custom offer, order, delivery, revision,
earnings and payout actions.

- [ ] Write failing tests for exact action coverage, safe public defaults and approved browser/API
  selection.
- [ ] Record account-specific approval privately; never treat Personal Assistant eligibility as
  general external authorization.
- [ ] Reuse the isolated CloakBrowser provider profile and shared effect identity.
- [ ] Run authenticated read-only profile/catalogue readback.
- [ ] Run tests and commit/push public code/config only.

### Task 24: Build and publish a Fiverr Gig canary

**Files:**
- Create: `skills/earn/gig/scripts/providers/fiverr_catalogue.py`
- Create: `skills/earn/gig/tests/test_fiverr_catalogue.py`

**Interfaces:** Produces factual Gig title, packages, price, FAQ, requirements, assets and official
Gig ID/state.

- [ ] Write failing tests for unfulfillable package, unsupported claim, price below margin, missing
  requirements and duplicate publication.
- [ ] Generate one catalogue entry from installed Skills and independent verifier coverage.
- [ ] Persist publication intent and execute one authorized publish/update effect.
- [ ] Require official Gig ID, visible state and exact package readback.
- [ ] Replay with zero duplicate Gig; run tests and commit/push.

### Task 25: Handle Fiverr inquiries and custom offers

**Files:**
- Create: `skills/earn/gig/scripts/providers/fiverr_inbox.py`
- Create: `skills/earn/gig/tests/test_fiverr_inbox.py`

**Interfaces:** Normalizes conversation identity and executes reply/custom-offer effects.

- [ ] Write failing tests for first auto-reply, Personal Assistant handoff, duplicate message,
  unclear requirements and custom offer outside bounds.
- [ ] Persist inquiry before semantic work and choose official assistant or direct authorized effect
  from current capability.
- [ ] Generate tailored qualification/reply and one bounded custom offer.
- [ ] Require message and offer IDs through official page readback.
- [ ] Replay with no duplicates; run tests and commit/push.

### Task 26: Normalize Fiverr orders and capacity

**Files:**
- Create: `skills/earn/gig/scripts/providers/fiverr_order.py`
- Create: `skills/earn/gig/tests/test_fiverr_order.py`

**Interfaces:** Produces canonical project state from order, requirements, delivery date and revision
terms.

- [ ] Write failing tests for incomplete requirements, conflicting package, capacity overflow,
  cancelled order and changed delivery deadline.
- [ ] Reserve capacity only after official active-order readback.
- [ ] Create the same immutable project workspace used by Upwork.
- [ ] Route requirements gaps through one durable buyer message.
- [ ] Run tests and commit/push.

### Task 27: Fulfill, verify, deliver and revise Fiverr orders

**Files:**
- Create: `skills/earn/gig/scripts/providers/fiverr_delivery.py`
- Create: `skills/earn/gig/tests/test_fiverr_delivery.py`

**Interfaces:** Uses common workflow/QA; returns official delivery/revision state.

- [ ] Write failing tests for placeholder delivery, partial unauthorized delivery, duplicate
  delivery, changed artifact and out-of-scope revision.
- [ ] Run Tasks 17–18 against the Fiverr order workspace.
- [ ] Persist one delivery intent and require official delivered state/readback.
- [ ] Version revisions and account for their cost without overwriting prior artifacts.
- [ ] Replay with zero duplicate delivery; run tests and commit/push.

### Task 28: Reconcile Fiverr earnings and close its first-payment gate

**Files:**
- Create: `skills/earn/gig/scripts/providers/fiverr_finance.py`
- Create: `skills/earn/gig/tests/test_fiverr_finance.py`

**Interfaces:** Produces order-bound gross, provider fee, cleared earnings, withdrawal and payout
states.

- [ ] Write failing tests separating completed order, clearing period, withdrawable balance,
  withdrawal and unknown payout.
- [ ] Join official earnings to order/delivery and actual execution/revision cost.
- [ ] Recognize only cleared/received revenue according to the canonical accounting contract.
- [ ] Close the first-payment gate with a real receipt, then repeat until the same three-job gate as
  Upwork passes.
- [ ] Run tests and commit/push.

## Phase D — Extract the reusable Market Factory after two markets

### Task 29: Prove kernel parity and remove provider branching

**Files:**
- Create: `skills/earn/gig/tests/test_two_market_kernel_parity.py`
- Modify: `skills/earn/gig/scripts/provider_adapter.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

**Interfaces:** Makes Upwork and Fiverr pass one shared contract suite.

- [ ] Write parity assertions for discover, sale, conversation, contract/order, workspace, QA,
  delivery, payment and replay.
- [ ] Identify every provider conditional outside `scripts/providers/`; move only transport/state
  normalization behind the adapter contract.
- [ ] Preserve Coconala behavior and effect keys.
- [ ] Run Coconala, Upwork and Fiverr focused suites together.
- [ ] Commit/push only after all three paths pass.

### Task 30: Create a provider adapter template and conformance suite

**Files:**
- Create: `skills/earn/gig/scripts/providers/template_adapter.py`
- Create: `skills/earn/gig/tests/provider_contract.py`
- Create: `skills/earn/gig/tests/test_template_adapter.py`

**Interfaces:** Lets every subsequent provider supply transport/normalization while inheriting
authorization, intent, QA, finance and replay checks.

- [ ] Write a template fixture containing opportunity, message, project, delivery and payment states.
- [ ] Require all eight adapter operations and explicit unsupported actions.
- [ ] Make the conformance suite fail any success without provider identity/readback.
- [ ] Prove the template uses no live credentials and performs zero effects.
- [ ] Run tests and commit/push.

### Task 31: Implement single-market probe and selection

**Files:**
- Create: `skills/earn/gig/scripts/next_market_selector.py`
- Create: `skills/earn/gig/tests/test_next_market_selector.py`

**Interfaces:** Selects one next market from authorization, observed demand, expected net, human
minutes and account risk; default tie order is LinkedIn, Mercor, Welocalize, TELUS, uTest, Prolific,
Outlier, Babel.

- [ ] Write failing tests for deterministic ties, denied actions, negative margin, unknown evidence
  and an already-active market.
- [ ] Implement pure scoring from receipts; no model opinion or estimated social-post earnings.
- [ ] Select exactly one candidate and lock it until `active/assisted/denied/unprofitable`.
- [ ] Prove all other unbuilt markets remain effect-off.
- [ ] Run tests and commit/push.

## Phase E — Add every remaining market one at a time

### Task 32: Add LinkedIn lead discovery

**Files:**
- Create: `skills/earn/gig/scripts/providers/linkedin_adapter.py`
- Create: `skills/earn/gig/tests/test_linkedin_adapter.py`

**Interfaces:** Produces lead/company/job identities and approved outreach capability.

- [ ] Record action-level API/browser authorization and safe public defaults.
- [ ] Write fixtures for duplicate leads, stale jobs and unsupported outreach.
- [ ] Run one authenticated read-only lead receipt.
- [ ] If outreach is approved, send one canary message and require message/thread readback.
- [ ] Attribute any resulting contract/payment to the original lead; test and commit/push.

### Task 33: Close LinkedIn's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_linkedin_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require one complete lead→conversation→contract→payment chain for `active`.
- [ ] Mark `assisted` only when an irreducible ceremony is evidenced.
- [ ] Mark `denied` or `unprofitable` from authorization/economics evidence, not inconvenience.
- [ ] Reconcile all effects before unlocking the next market.
- [ ] Run gate tests and commit/push.

### Task 34: Add Mercor role matching and account workflow

**Files:**
- Create: `skills/earn/gig/scripts/providers/mercor_adapter.py`
- Create: `skills/earn/gig/tests/test_mercor_adapter.py`

- [ ] Record action-level authorization for profile, applications, scheduling, interview and
  post-match work.
- [ ] Write tests forbidding fabricated credentials and automating an interview outside approval.
- [ ] Implement role matching, factual profile assets and authorized application/readback.
- [ ] Represent required identity/interview as a typed ceremony; resume from official state.
- [ ] Trace the first matched work/payment or terminal disposition; test and commit/push.

### Task 35: Close Mercor's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_mercor_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require provider role/application/project/payment identities.
- [ ] Account for interview/human minutes separately from agent work.
- [ ] Verify no ceremony is silently counted as autonomous success.
- [ ] Reconcile and set `active/assisted/denied/unprofitable`.
- [ ] Run tests and commit/push.

### Task 36: Add Welocalize project adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/welocalize_adapter.py`
- Create: `skills/earn/gig/tests/test_welocalize_adapter.py`

- [ ] Resolve authorization per project/task type rather than account-wide.
- [ ] Write fixtures for locale, rubric, source confidentiality, deadline and pay unit.
- [ ] Implement authorized discovery, claim, locale workflow, QA, submission and readback.
- [ ] Reconcile the first payment with task IDs and actual cost/human minutes.
- [ ] Run conformance tests and commit/push.

### Task 37: Close Welocalize's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_welocalize_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require a complete authorized project receipt path or explicit terminal evidence.
- [ ] Reject cross-project reuse of customer data or authorization.
- [ ] Compare verified net per agent and human minute.
- [ ] Set terminal disposition and unlock the next market.
- [ ] Run tests and commit/push.

### Task 38: Add TELUS Digital project adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/telus_adapter.py`
- Create: `skills/earn/gig/tests/test_telus_adapter.py`

- [ ] Record authorization per role/project/action and identity requirement.
- [ ] Write tests separating agent preparation/administration from required human judgment.
- [ ] Implement authorized discovery, task scheduling, evidence collection, submission and readback.
- [ ] Use typed ceremonies only for required human acts and record their minutes.
- [ ] Reconcile first payment or terminal disposition; test and commit/push.

### Task 39: Close TELUS Digital's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_telus_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require task, submission and payment receipts for active/assisted status.
- [ ] Reject revenue attribution when required human judgment was omitted or fabricated.
- [ ] Calculate verified net per scarce human minute.
- [ ] Set terminal disposition and reconcile all effects.
- [ ] Run tests and commit/push.

### Task 40: Add uTest confidential-cycle adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/utest_adapter.py`
- Create: `skills/earn/gig/tests/test_utest_adapter.py`

- [ ] Record cycle-specific authorization, devices, scope and confidentiality.
- [ ] Write tests for customer-data isolation, duplicate bug submission and missing reproduction.
- [ ] Implement authorized cycle discovery, test execution orchestration, bug-report QA, submission
  and readback.
- [ ] Keep each customer in an isolated owner-only workspace.
- [ ] Reconcile first payment or terminal disposition; test and commit/push.

### Task 41: Close uTest's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_utest_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require cycle, bug/task, acceptance and payment identities.
- [ ] Verify public fixtures/logs contain no client content.
- [ ] Attribute rejected bugs and human device minutes as cost.
- [ ] Set terminal disposition after full reconciliation.
- [ ] Run tests and commit/push.

### Task 42: Add Prolific study-specific adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/prolific_adapter.py`
- Create: `skills/earn/gig/tests/test_prolific_adapter.py`

- [ ] Resolve AI/automation authorization independently for every study.
- [ ] Write tests excluding unauthorized studies and preventing one submission per participant from
  duplicating.
- [ ] Implement authorized study discovery, eligibility, completion workflow, submission/readback.
- [ ] Include attention/human requirements and expected hourly net in qualification.
- [ ] Reconcile first payment or terminal disposition; test and commit/push.

### Task 43: Close Prolific's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_prolific_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require study permission, submission and payment IDs.
- [ ] Prove unauthorized studies caused zero effects.
- [ ] Calculate net after time/tool cost and rejection risk.
- [ ] Set terminal disposition and reconcile.
- [ ] Run tests and commit/push.

### Task 44: Add Outlier project-specific adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/outlier_adapter.py`
- Create: `skills/earn/gig/tests/test_outlier_adapter.py`

- [ ] Resolve authorization per project and exact automation action.
- [ ] Write tests for rubric version, provenance, prohibited assistance and duplicate task submit.
- [ ] Implement authorized task claim, rubric-bound workflow, QA, submission and readback.
- [ ] Preserve all source/output provenance privately.
- [ ] Reconcile first payment or terminal disposition; test and commit/push.

### Task 45: Close Outlier's market disposition

**Files:**
- Create: `skills/earn/gig/tests/test_outlier_market_gate.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require project permission, task, accepted submission and payment IDs.
- [ ] Reject global authorization inferred from one project.
- [ ] Attribute rework/rejection and human minutes as cost.
- [ ] Set terminal disposition and reconcile.
- [ ] Run tests and commit/push.

### Task 46: Add Babel Audio capture adapter

**Files:**
- Create: `skills/earn/gig/scripts/providers/babel_audio_adapter.py`
- Create: `skills/earn/gig/tests/test_babel_audio_adapter.py`

- [ ] Record action authorization and exact human voice/capture requirement.
- [ ] Write tests for wrong speaker/session, missing consent, bad audio QA and duplicate upload.
- [ ] Implement discovery, scheduling, typed physical-capture ceremony, audio validation, authorized
  upload and readback.
- [ ] Bind source artifact, consent, submission and payment identities without committing audio.
- [ ] Reconcile first payment or terminal disposition; test and commit/push.

### Task 47: Close Babel Audio and the ten-market queue

**Files:**
- Create: `skills/earn/gig/tests/test_all_market_dispositions.py`
- Modify: `skills/earn/gig/scripts/market_factory.py`

- [ ] Require every named market to be `active`, `assisted`, `denied` or `unprofitable`; no silent
  `research` remains.
- [ ] Require all mutation-capable lanes to pass conformance and duplicate-replay tests.
- [ ] Require assisted lanes to report exact human minutes and resume receipts.
- [ ] Reconcile all open effects before closing the queue.
- [ ] Run the all-market test and commit/push.

## Phase F — General self-improving portfolio agent

### Task 48: Define immutable Skill bundles

**Files:**
- Create: `skills/earn/gig/scripts/skill_bundle.py`
- Create: `skills/earn/gig/tests/test_skill_bundle.py`

**Interfaces:** Loads `SKILL.md`, `skill.manifest.json`, `workflow.json`, tests and version hash.

- [ ] Write failing tests for missing files, mutable version, undeclared tool/effect, absolute path
  and secret-bearing fixture.
- [ ] Implement strict bundle validation and content hash.
- [ ] Index existing Gig Skills without copying them.
- [ ] Prove the same bundle is immutable and a changed bundle receives a new version.
- [ ] Run tests and commit/push.

### Task 49: Compose existing Skills before generating code

**Files:**
- Create: `skills/earn/gig/scripts/skill_composer.py`
- Create: `skills/earn/gig/tests/test_skill_composer.py`

**Interfaces:** Produces a workflow from installed Skill inputs/outputs or an evidence-bound
`CapabilityGap`.

- [ ] Write tests where composition succeeds, type mismatch fails and no installed Skill closes the
  gap.
- [ ] Select the shortest valid workflow with declared verifier coverage.
- [ ] Require observed opportunity or failure evidence before emitting a gap.
- [ ] Do not scaffold code from a speculative gap.
- [ ] Run tests and commit/push.

### Task 50: Add Skill replay and sandbox evaluation

**Files:**
- Create: `skills/earn/gig/scripts/skill_replay.py`
- Create: `skills/earn/gig/tests/test_skill_replay.py`

**Interfaces:** Returns `ReplayPassed/Rejected` from redacted fixtures with all effects disabled.

- [ ] Write failing tests for attempted effect, nondeterministic receipt, missing cost and changed
  expected artifact.
- [ ] Replay historical provider/work states in an isolated temporary home.
- [ ] Compare artifact, provider intent and accounting projections to expected hashes.
- [ ] Reject any bundle that touches live credentials or transports.
- [ ] Run tests and commit/push.

### Task 51: Add Skill canary, pause and rollback

**Files:**
- Create: `skills/earn/gig/scripts/skill_promotion.py`
- Create: `skills/earn/gig/tests/test_skill_promotion.py`

**Interfaces:** Implements `Proposed → ReplayPassed → Canary → Active/Paused/Reverted/Retired`.

- [ ] Write tests for direct activation, inconclusive pause, guardrail rollback and rollback-window
  expiry.
- [ ] Permit one canary effect/account at a time and persist prior version.
- [ ] Abort acquisition on quality/account/effect guardrail failure while preserving paid work.
- [ ] Restore the prior version and prove readback after revert.
- [ ] Run tests and commit/push.

### Task 52: Implement the Portfolio CEO decision function

**Files:**
- Create: `skills/earn/gig/scripts/portfolio_ceo.py`
- Create: `skills/earn/gig/tests/test_portfolio_ceo.py`

**Interfaces:** Produces one `PortfolioAction` from deadlines, reconciliations, authorized
opportunities, capacity, expected verified net, human minutes and experiments.

- [ ] Write priority tests: paid deadline > unknown-effect reconcile > fulfillment > acquisition >
  experiment > Skill build.
- [ ] Write economic tests for fees, Connects/bids, tools, refunds, chargebacks, risk and human-minute
  cost.
- [ ] Reuse existing founder allocator/bandit logic rather than creating a second optimizer.
- [ ] Return one action and durable reasoning evidence; never execute inside the scorer.
- [ ] Run tests and commit/push.

### Task 53: Connect CEO decisions to the existing wake loop

**Files:**
- Modify: `runtime/loop/index.mjs`
- Modify: `skills/earn/gig/scripts/application_direct.py`
- Create: `skills/earn/gig/tests/test_portfolio_wake_contract.py`

**Interfaces:** One existing wake asks Portfolio CEO for one action and routes it to the current
provider owner; no new daemon or cron.

- [ ] Write a failing contract test for one wake/one action, active owner lease and duplicate wake.
- [ ] Add a Gig portfolio capability to the existing registry/wake path.
- [ ] Route provider effects through their existing owner/fence; never execute from the model loop
  directly.
- [ ] Prove duplicate wake creates no duplicate effect and a busy owner leaves durable pending work.
- [ ] Run Node loop tests and focused Gig tests; commit/push.

### Task 54: Evaluate one bounded revenue experiment

**Files:**
- Modify: `skills/earn/gig/scripts/experiment_evaluator.py`
- Create: `skills/earn/gig/tests/test_portfolio_experiment.py`

**Interfaces:** Evaluates one variable among offer, price bounds, proposal version, category share,
schedule or workflow version.

- [ ] Write failing tests for incomplete outcome window, two changed variables, missing holdout,
  revenue without payment and guardrail degradation.
- [ ] Attribute outcomes to exact provider, project, Skill and strategy versions.
- [ ] Return only `insufficient_evidence`, `keep`, `pause`, `revert` or `retire`.
- [ ] Execute one bounded live canary and preserve before/after receipts.
- [ ] Run tests and commit/push.

### Task 55: Add evidence-bound Skill repair and creation

**Files:**
- Modify: `skills/earn/gig/scripts/gig_self_fix.py`
- Create: `skills/earn/gig/tests/test_skill_factory_gate.py`

**Interfaces:** Turns a repeated typed failure or confirmed capability gap into a branch, minimal
Skill change, replay and canary proposal.

- [ ] Write failing tests for speculative request, missing reproduction, policy-gate mutation,
  accounting mutation and direct hot reload.
- [ ] Search installed Skills first; compose when possible.
- [ ] Permit code generation only from reproducible evidence and constrain edits to the named Skill
  bundle/tests.
- [ ] Require normal branch/test/replay/canary/revert sequence before active promotion.
- [ ] Run tests and commit/push.

### Task 56: Publish the open-source local installer

**Files:**
- Modify: `skills/earn/gig/install.sh`
- Create: `skills/earn/gig/tests/test_open_source_install.py`
- Create: `docs/gig-money-loop-install.md`

**Interfaces:** A new owner installs locally, connects their own provider, records authorization and
starts one bounded canary without original operator state.

- [ ] Write an isolated-home archive/install test for zero secrets, identities, customers, payout
  IDs, runtime ledgers and original absolute paths.
- [ ] Guide provider login/KYC/payout ceremonies locally without exporting browser state.
- [ ] Explain safe public defaults, private authorization, spend/capacity bounds, receipts and
  earnings non-guarantee.
- [ ] Install on a clean third device and complete one authorized end-to-end receipt path.
- [ ] Run secret scan/install tests and commit/push.

### Task 57: Close portfolio revenue and replication gates

**Files:**
- Create: `skills/earn/gig/scripts/portfolio_accounting.py`
- Create: `skills/earn/gig/tests/test_portfolio_accounting.py`
- Create: `docs/superpowers/evidence/gig-portfolio-gates.md`

**Interfaces:** Reproduces provider/month funnels and USD/JPY verified-net gates from immutable
provider/payment/payout evidence.

- [ ] Write tests separating first-time one-off, repeat one-off and recurring received revenue;
  incomplete sources return `unknown`.
- [ ] Reconcile gross, actual provider fees, Connects/bids, execution cost, refunds, chargebacks,
  payout and recorded FX.
- [ ] Report application, conversation, contract, delivery, payment, retention and human-minute
  funnels separately.
- [ ] Close USD 10,000 and JPY 10,000,000 gates only from complete source evidence.
- [ ] Record clean-device replication evidence; run tests and commit/push.

## Final verification

- [ ] `git diff --check` exits 0.
- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests` exits 0 with zero
  failures.
- [ ] `python3 -m compileall -q skills/earn/gig` exits 0.
- [ ] Existing runtime loop Node tests exit 0.
- [ ] Secret/PII scan reports zero tracked credentials, approvals, customer data and payout details.
- [ ] Every market has a terminal disposition and every mutation has authorization, intent, effect,
  authoritative readback and receipt.
- [ ] Every crash replay produces zero blind duplicate effects.
- [ ] Coconala production release and repair order remain valid.
- [ ] Clean-device installation completes one real authorized receipt path.
- [ ] Portfolio accounting reconciles provider/payment/payout evidence and preserves `unknown`.
