# Life Manager Open-Source Money Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close one real Upwork email-signup/login → job → proposal → negotiation → contract →
delivery → received-payment loop, repeat it across three independent paid jobs, then operate the
proven local loop until one complete calendar month reaches USD 10,000 verified net received before
adding another market.

**Architecture:** The active slice is Upwork only. It uses the dedicated CloakBrowser profile,
normal owner email/password authentication, Upwork-scoped state and the smallest existing durable
effect primitives needed for the first live path. Coconala continues independently and contributes
neither runtime state nor capacity to Upwork. Cross-market Portfolio CEO and Skill Factory work
resumes only after the Upwork USD 10,000 received-cash gate closes.

**Tech Stack:** Python 3.13+, standard-library SQLite/JSON, existing CloakBrowser CDP helpers,
approved provider APIs, existing launchd release system, pytest with plugin autoload disabled.

**Spec:** `docs/superpowers/specs/2026-08-22-life-manager-gig-economy-loop-design.md`

## Global constraints

- Execute exactly one task at a time and commit/push after its verification passes.
- Until the Upwork USD 10,000 received-cash gate, mutate and measure Upwork only; do not operate on
  Coconala from this plan.
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
| U13 | Make acquisition fully loop-owned | **DONE:** five-minute main loop uses native Best Matches, ten-job Luna batches, prompt-bound cache, durable sealed queue, Terra browser operation, exact Connects/effect readback and one-candidate failure isolation. |
| U14 | Close the first acquisition effect | **DONE:** owner-authorized seed produced 150 Connects; proposal `2091740505918763009`, exact `150 -> 141`, no subscription/boost/badge/auto-top-up. |
| U15 | Replay immediately | **DONE:** the first three proposals return the same IDs on exact replay with additional Connects 0. A fourth loop-owned proposal `2091811328085401601` for `~022091778584504223418` is also officially listed, with `118 -> 92`; its post-effect count refresh and replay remain the next readback slice. |
| U16 | Poll and answer the resulting thread | **IN PROGRESS:** official Submitted proposals is 4; canonical Messages works, rooms/unread/offers/contracts 0. Next real buyer event must produce official story/message ID and duplicate reply 0. |
| U17 | Negotiate and accept profitable terms | Offer ID, exact rate, weekly limit, 0–15% contract fee, terms hash and active contract ID |
| U18 | Fulfill and independently verify the work | Immutable scoped task, Upwork Desktop App tracker start/stop, protected diary screenshot/memo/activity evidence, artifact hash and independent verifier PASS |
| U19 | Deliver once | Official submission ID/state and replay with zero duplicate delivery |
| U20 | Reconcile money and review | Hour diary → Monday invoice → client review → Wednesday availability → official payout `received`, transaction, fee, actual costs and honest review evidence; Pending/Available excluded |
| U21 | Repeat on three independent paid jobs | Three contract/payment/review IDs and complete per-job economics |
| U22 | Operate the proven Upwork loop to USD 10k/month | One complete calendar-month window totals at least USD 10,000 verified net received; cross-month payouts and later chargebacks are attributed once to their actual months |
| U23 | Compress the next-market path | **IN PROGRESS:** general Luna/Terra market operation, shared effects/projects/accounting and Skill inventory are proven; next existing market adds only manifest plus fixed-format readback glue. |
| U24 | Let the agent onboard an unknown market | Founder scout discovers demand, observes rules/UI/payout, performs ordinary signup/login, runs one zero-spend canary and joins the same lifecycle; only typed ceremonies pause that market. |

Later implementation tasks are renumbered only when their first incomplete outcome becomes active.
Marketplace mutations remain frozen only until U14 closes one official Upwork proposal receipt.
Read-only research and adapter generation may proceed earlier. After U14, additional zero-spend
canaries may run while Upwork continues through U15–U22; paid work and unknown-effect reconciliation
always preempt expansion.

Current official truth is proposals 4, Connects 92, replies/offers/contracts 0 and payout `received`
USD 0. Production `fac29d37e0` runs every five minutes through
the dedicated authenticated 9233 browser. Finance proof remains `12d92846e`/`c0c66c32f` with 40/40;
the latest natural wake exits 0 and official/runtime proposal counts both equal 4.

Remaining order to finish the local Upwork skill and business loop:

| Order | Required closure |
|---:|---|
| 1 | **DONE:** account/profile/portfolio, dedicated browser, parallel discovery, one-call per-candidate Luna decisions, four official proposals, natural Telegram and official/runtime count 4 |
| 2 | Replay proposal 4 with the same ID and Connects `92 → 92`; remove notification transport from acquisition critical path |
| 3 | Execute all positive-EV sealed proposals with job leases and atomic Connects reservations; partial failure cannot stop sibling jobs |
| 4 | U16–U17 close the first real client reply, profitable terms and active contract with official IDs and replay 0 |
| 5 | Close protected hourly Time Tracker and diary evidence before billable work |
| 6 | U18–U19 close immutable project, Skill execution, independent PASS, one delivery/work receipt and duplicate 0 |
| 7 | U20 joins diary/milestone, gross, fee, Connects/model/tool cost, invoice/review, refund/chargeback and payout `received` |
| 8 | Publish OSS alpha after the first complete discovery-to-received path, redacted fixtures, secret scan and isolated installer pass |
| 9 | U21 closes three independent paid-review paths; retain the winning Skill/problem/proof/price and prioritize repeat clients |
| 10 | Run zero-spend canaries on uGig, Freelancer, Lancers, CrowdWorks, Fiverr and Mercor concurrently through the same common rails |
| 11 | Enable Founder discovery, close second-market `received`, clean-device OSS stable, then repeat measured winners toward the revenue gates |

The remaining work belongs to the resident Upwork loop, not to Codex as a marketplace operator.
Codex's atomic engineering TODO is ordered as follows; it only edits, activates and verifies the loop:

1. Wire authenticated search/detail receipts from port 9233 into `upwork-acquire`.
2. Give the model owner facts, installed Skill manifests, full job/client evidence, capacity and
   economics; require schema-bound `select` or `skip` with cited evidence and no keyword routing.
3. Atomically write the selected candidate cache and owner-only sealed proposal, bound to job ID,
   official URL, evidence hash, terms, exact Connects and factual claims.
4. Run the existing `ai.anicca.life-manager-upwork-free-loop`; verify it replenishes the ready queue
   itself, then replay with no duplicate candidate/proposal/effect.
5. Complete the already-planned loop-owned paths for reply, negotiation, contract, Skill fulfillment,
   independent QA, revision, delivery, payout/review and three-job replay.
6. Keep the loop resident and let `upwork-learn` change one acquisition/package/price variable at a
   time until a complete calendar month reaches USD 10,000 verified net received.

Login/signup/KYC recovery is deliberately deferred until the authenticated profile actually fails;
it is not on the current money path.

Engineering completion is Task 22's repeatability gate. Business completion is U22. Neither a test
pass nor a deployed release satisfies a live receipt checkbox.

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
12. **CONTROL-PLANE RECOVERY IN PROGRESS:** the last official wake persisted at
    `2026-08-22T18:46:29.413515+00:00` before evidence allocation failed with
    `OSError: [Errno 28] No space left on device`. The stored official truth remains Connects 0,
    submitted proposals 0, invitations 0, offers 0, active contracts 0, Catalog orders 0 and
    earnings USD 0; it is stale rather than a current successful wake. Reclaim removed only the
    regenerable `~/.npm/_npx` cache plus two unpinned immutable releases while preserving current,
    live and rollback releases. Free space recovered from roughly 320 MiB to 20.08 GiB; the owning
    disk sentinel then cleared both `disk-writers.stop` and `disk-pressure.block` through their
    normal >=11 GiB recovery condition. A fresh recheck finds the shared Gig browser healthy on 9223,
    but the Upwork provider still targets 9233 and no process owns that port. The authenticated
    `gig-upwork` profile remains separate from `gig-daily-driver`; moving the provider to 9223 would
    lose its session and is rejected. No alternate profile, fake receipt, proposal or payment exists.
13. **CANDIDATE COST EVIDENCE REPAIRED:** fresh host readback still shows no CDP listener on
    9223/9233 and the isolated Codex context still returns launchctl 141/manager 153. The correct
    `gig-upwork` profile is intact with 103 Upwork cookies and 114 Upwork history rows; an isolated
    CloakBrowser profile aborts with SIGABRT in this context, while cookie-only official GETs are
    rejected with HTTP 403. The last successful official Connects receipt says `0 Connects` and
    `No Connects transactions.` The candidate later rendered behind Cloudflare and was incorrectly
    reported with `connects_required=null`, but its immediately preceding official receipt says
    `7 Connects`; it is not a zero-Connect job. Reconciliation now retains that last official cost
    and its evidence hash when a later tick is unknown, while preserving `status=unknown`, so the
    planner still cannot submit. The focused provider suite passes 20/20, and a replay of the real
    official-7-then-Cloudflare receipt sequence returns unknown/7 rather than unknown/null without
    creating an application effect.
    Main commit `a3ff1d61e4ccfe980f8e4b1de197f8e9fa28047d` is published as immutable release
    `20260823T045407-a3ff1d61`; provider SHA-256 is
    `20fd33e07aec70063b48fd2e20539a13ca55d07727da46693580b956aefc1a72`. The same 20 focused
    tests pass from the read-only release and syntax compilation passes with a redirected bytecode
    cache. This proves deployment, not a fresh Upwork wake or application.
14. **DEDICATED BROWSER OWNER CODE COMPLETE / PRODUCTION PENDING:** root-cause comparison proves the
    original 9233 choice is intentional: `gig-upwork` has 103 Upwork cookies while the shared 9223
    profile has zero. The missing component is its durable browser owner. The manifest now reuses
    `launch_gig_browser.sh` as `ai.anicca.life-manager-upwork-browser` with port 9233, profile
    `gig-upwork`, historical fingerprint `80138`, KeepAlive and a distinct log; the provider names
    that label. Fingerprint provenance is the prior live main Chromium argv at
    `/Users/anicca/.codex/sessions/2026/08/22/rollout-2026-08-22T12-44-48-01a02792-348c-7ad3-b606-eaf93a8eb3c0.jsonl:11941`,
    which binds `80138`, `9233` and `gig-upwork` in one process. Focused provider tests pass 20/20.
    Disk cleanup preserves client projects, ledgers,
    archives and proof while recovering regenerable caches and compressing 1376 trashed Codex
    sessions into an integrity-checked archive. Headroom is still 7.6 GiB because macOS holds 15 GiB
    of swap, so build/publish/Aqua activation and fresh provider readback remain pending.
15. **PRODUCTION LABEL ACCEPTED / DISK-BLOCKED:** native release watcher published descendant release
    `5351f1f58483bac6eec9c1610e4224022bde9d03` and loaded both new definitions. The dedicated browser
    plist readback is label `ai.anicca.life-manager-upwork-browser`, stable-current
    `launch_gig_browser.sh`, port `9233`, profile `gig-upwork`, fingerprint `80138`, KeepAlive true,
    CDP URL `9233` and dedicated owner label. The browser preflight then returned
    `reason=disk_writers_stop`, `available_bytes=7347806208`, `required_bytes=536870912`, `effect=0`,
    `readback=0`; 9233 stayed absent. The provider wake failed on connection refused and left the
    official state timestamp at `2026-08-22T18:46:29.413515+00:00`. Shared 9223 remained healthy.
    Current free space later read 6.8 GiB and macOS swap remained 15 GiB. U13 therefore waits on the
    host disk policy, not missing code, launchd definition, browser profile or provider routing.
16. **MEMORY/DISK SAFE RECLAIM EXHAUSTED:** browser restart had invalidated the old target-ownership
    IDs, so the normal tab GC saw zero owned pages while 45 Coconala pages remained. A direct CDP
    audit closed only exact duplicate or `/mypage/direct_message/` pages whose textarea and
    contenteditable controls were empty; no draft or evaluation-error page was closed. The shared
    browser moved from 45 pages to 5, preserving storefront, offer edit, one message, active talkroom
    and blank. Swap total fell from 15 GiB to 14 GiB and free disk rose from 6.8 GiB to 8.5 GiB.
    Standard `purge` was denied by macOS, and no live loop, app, customer project, ledger, archive or
    proof was removed. The 20 GiB host policy therefore remains active; a native reboot or equivalent
    authorized host-level swap recovery is still required before 9233 can start.
17. **EXPLICIT CLEANUP COMPLETED / SWAP CONFIRMED AS ROOT BLOCKER:** after operator cleanup approval,
    Trash `2.34 GiB` was emptied and a `1.64 GiB` pre-OSS Git bundle was removed only after all
    `566/566` bundle head commits were proven present in the current repository. Project janitor
    scanned 25 projects and deleted zero because every project remained nonterminal or guarded;
    customer work was preserved. Trash is now empty. Despite roughly 4 GiB of file cleanup, free
    space is only 8.0 GiB because macOS swap grew to 16 GiB with 15.66 GiB used. Deleting enough
    additional space would require active project/runtime or Codex history loss. The smallest safe
    unblock remains a native reboot that releases swap, followed by the existing 20 GiB policy
    readback and automatic 9233 restart.
18. **20 GiB PREVENTIVE CAP REMOVED FOR UPWORK:** operator explicitly rejected the 20 GiB startup
    requirement. The host-wide policy remains unchanged for other producers. Only the dedicated
    Upwork browser now ignores `disk-pressure.block` and the stale `disk-writers.stop`, while
    `GIG_DISK_HEADROOM_KIB=524288` still requires 512 MiB free before Chromium starts. The shared
    9223 browser and all other lanes retain their existing policy. Next acceptance is 9233 argv/profile
    readback followed by two fresh provider wakes and exact funnel counts.
19. **141 CONTROL PLANE RECOVERED:** the command parent was stale app-server PID `2128`, started before
    the current ChatGPT GUI and detached at PPID 1. Targeted TERM plus the official acct2 daemon stop
    reconnected this thread to new PID `26982`. The same preflight changed from numeric username,
    manager 153 and gui 141 to `id-un=anicca`, `managername=Aqua`, UID 501, manager PID 1,
    `gui/501` rc 0, `status=pass`, `mutation_allowed=true`. No OS service or browser was restarted.
20. **9233 AND FRESH FUNNEL ACCEPTED:** release `3e41b0ce0c3a` scoped the preventive flag override to
    the Upwork browser and retained the 512 MiB hard floor. Production readback is PID `68012`,
    fingerprint `80138`, profile `gig-upwork`, port 9233 and launchd running. Two provider wakes exited
    0. The second observed balance 0, submitted proposals 0, replies/messages 0, invitations 0,
    offers 0, active contracts 0, payout USD 0, provider effects 0 and transition delta 0. Catalog is
    visible with one 30-day view and zero orders. Of three sealed candidates, the $15 usability job
    is officially closed; the two open jobs require 14 and 9 Connects. U13 next replaces the closed
    candidate before U14.
21. **STATIC-CANDIDATE DEFECT IDENTIFIED / AUTONOMOUS REPLENISHMENT NEXT:** the deployed provider can
    reconcile and execute sealed proposals, but its public candidate JSON is still a manually
    maintained input. That is not an end-to-end Upwork loop. U13 now closes only when the existing
    launchd loop searches authenticated current jobs, supplies full evidence plus owner/Skill facts
    to model judgment, selects or skips, and atomically seals enough truthful proposals to restore
    three ready candidates without Codex choosing or editing marketplace work. This is the first
    unfinished engineering item; reply, contract, fulfillment, delivery, money and learning remain
    subsequent loop-owned closures.
22. **AUTONOMOUS REPLENISHMENT CODE COMPLETE / PRODUCTION PENDING:** the provider now reads the
    release candidate JSON only as an initial seed. With fewer than three officially open ready jobs,
    the same resident wake opens authenticated recency search and up to four current job details,
    supplies each exact evidence receipt, owner profile and installed Upwork delivery Skill contract
    to the existing isolated model runner, and accepts only a schema-valid `submit` or evidenced
    `skip`. Deterministic code binds job ID/URL/title/evidence hash/Connects, requires empty unsupported
    claims and attachments, writes mode-600 sealed proposals and atomically replaces the runtime
    cache. Existing replies/inbound and already-ready covered proposals preempt discovery; discovery
    failure is fail-visible without killing those lanes. All current Upwork tests pass 154/154. The
    next closure is immutable release activation followed by one live replenishment and replay.
23. **FIRST LIVE REPLENISHMENT REACHED MODEL GATE / SCHEMA FIX ACTIVE:** release `e0c2ae15034e`
    completed authenticated account, candidate, inbox, contract, finance, recency-search and current
    job-detail reads. The loop created a private evidence packet itself, then the existing model runner
    rejected the new response schema because `provider` and `status` used `const` without explicit
    string `type`. The provider surfaced `candidate_replenishment=failed`, exited 0, preserved the two
    open candidates and produced zero proposals/effects. Add the required types, release, and replay;
    no selection or marketplace action is inferred from this failed call.
24. **SECOND LIVE REPLENISHMENT REACHED STRICT ARRAY GATE:** release `6b2a00bdf000` accepted the
    explicit scalar types and again reached the model provider with a fresh official job packet. The
    response-format validator then required `items` even for arrays constrained to `maxItems: 0`.
    Add inert item schemas for `unsupported_claims` and `attachments`; the wake remained exit 0,
    `candidate_replenishment=failed`, proposals/effects 0 and the existing two ready jobs intact.
25. **MODEL-OWNED SEARCH/SKIP PROVED / READY REPLENISHMENT CONTINUES:** release `1cb151a2e430`
    completed a production wake with exit 0, searched four current public jobs and passed four full
    official detail receipts through schema-valid model judgment. All four were skipped for observed
    capability/location/client/terms risks; no proposal or marketplace effect occurred. The run also
    exposed that the prompt incorrectly allowed zero current Connects to count against qualification,
    and that skipped IDs were not durable. Clarify that Connects gate execution rather than sealing,
    persist rejected IDs in the runtime cache, and continue deeper into current results next wake.
26. **REJECT MEMORY PROVED / MODEL SEARCH STRATEGY NEXT:** release `bca5e36ff0b4` completed two
    production wakes. Each inspected four fresh jobs, persisted eight unique model-skipped IDs, and
    the second wake did not reconsider the first four. Zero Connects no longer appeared as a sole
    rejection reason. The broad unqueried recency feed was dominated by unrelated design, CAD and
    location-bound work, exposing search strategy as the next bottleneck. The next slice asks the
    model for three narrow queries from the installed Upwork Skill and owner evidence, persists a
    rotation index, and uses no hardcoded semantic keywords.
27. **MODEL SEARCH QUERY PROVED / URL CANONICALIZATION FIX ACTIVE:** release `33f8ae5d9755` asked the
    model once and received three Skill-bound queries covering FastAPI text AI, multimodal similarity
    ranking and bounded AI integration. The first authenticated search rendered real results, but
    Upwork canonicalized query spaces from `+` to `%20`, so the strict requested/final URL receipt
    rejected it before candidate judgment. Generate `%20` directly and replay the same cached model
    strategy. No proposal, Connects or marketplace effect occurred.
28. **MODEL QUERY EXECUTION PROVED / VERIFIER CAPABILITY GAP NEXT:** release `7a3559b85d84` reused the
    cached model strategy, executed the canonical authenticated query and inspected four API/AI jobs.
    It rejected all four with direct scope, margin, client and proof reasons; one repeated reason was
    that `upwork-ai-api-delivery` explicitly requires a different verifier Skill but none was installed.
    Add the narrow independent `upwork-ai-api-verifier` contract so qualification can truthfully bind
    build and QA before selecting work. Search query index advanced, rejected IDs remained durable,
    and proposals/effects stayed 0.
29. **PONYTAIL SCOPE CUT / APPLICATION IS THE ONLY NEXT EFFECT:** release `883a329efc7e` includes the
    independent verifier and completed another production model-search wake with exit 0. The loop has
    inspected twelve model-query jobs plus earlier broad-feed jobs, retains one officially open sealed
    proposal requiring 9 Connects, and has submitted 0 because the official balance is 0. Stop adding
    acquisition abstractions or requiring three ready jobs before action. Reuse the existing proposal
    effect path and submit the best sealed job as soon as wallet-authorized Connects are officially
    available. A Connects purchase is the only next action requiring owner approval.
30. **ZERO-CONNECT PUBLIC JOB BUG REMOVED:** operator confirmed no Connects purchase and directed the
    loop to pursue work requiring no prior network or paid capacity. Official Upwork documentation
    distinguishes human connections from Connects and confirms invitations cost zero; public job cost
    is provider-assigned and read per job. The existing planner incorrectly returned immediately for
    balance 0 before checking a candidate whose official `connects_required` could itself be 0. Remove
    that guard and rely only on `required_connects <= balance`, preserving the existing sealed proposal
    and exactly-once submission path. Search/selection remains model-owned; regex is limited to fixed
    provider identifiers and numeric readback, never suitability judgment.
31. **COCONALA SELLER POLICY RESTORED:** live zero-spend search exposed that the Upwork candidate
    planner was reading the employee job-search profile, so its annual salary floor incorrectly
    rejected bounded $400 freelance work. Coconala application planning does not use employee salary
    policy. Point Upwork acquisition to the existing gig owner profile and installed Skill contracts;
    do not add a new scoring rule, keyword list or marketplace-specific salary abstraction.
32. **CUSTOM ACQUISITION STACK DELETED / COMMON LOOP RESTORED:** remove 521 lines of dedicated query
    planner, candidate planner, response schemas and verifier Skill. Keep the existing Upwork browser,
    proposal model, effect fence and official readback. The single provider now follows the proven
    Coconala shape: read current listings, let the model decide from full detail, submit through the
    provider adapter, then require the official proposal ID. Code parses only fixed Upwork URLs, IDs
    and Connects amounts; it contains no keyword or regex suitability judgment.
33. **COMMON LOOP LIVE / ZERO-CONNECT SCAN EXPANDED:** release `a76fb2e9c611` completed the first
    production wake through the simplified path: ten current jobs inspected, zero official
    zero-Connect jobs, proposals 0 and external effects 0. Reuse the marketplace's ordinary page
    order and follow three bounded result pages per wake, exactly like the existing Coconala scanner;
    no semantic query, score, category allowlist or custom judgment layer is added.
34. **ADAPTER COMPRESSION IS THE EXPANSION CONTRACT:** current Upwork support spans eighteen provider
    files and roughly 4,200 lines, so copying it would make later markets slower rather than faster.
    Preserve the running Upwork canary, then after its first proposal receipt extract only behavior
    already proven by Coconala plus Upwork. The next gig or bounty market must fit in at most three
    provider files/about 300 production lines with zero kernel changes; later markets shrink toward
    one manifest plus transport glue. Unknown-site signup and adapter generation belong to the resident
    agent, not manual Skill authoring, except for typed human-only identity/tax/payout ceremonies.
35. **UPWORK APPLY LOOP LIVE / NO CURRENT ACTIONABLE JOB:** release `5a0ff9e4f93c` completed a
    production wake with exit 0, traversed three official result pages and inspected 28 unique current
    job details. None showed an official zero-Connect proposal entry. Balance, submitted/active
    proposals, invitations, Direct Offers and Catalog orders all remain 0; marketplace effects remain
    0. U13 is therefore engineering-complete: the five-minute loop applies through the existing fence
    as soon as a zero-cost job, invitation, offer, order or free Connects becomes official. U14 remains
    a live business outcome, not another code task.
36. **REOPENED UNTIL ACTUAL APPLICATION / DURABLE SEARCH CURSOR:** application count 0 means U13 is
    not complete. The three-page wake repeated the same leading pages and could never cover deeper
    current inventory. Reuse the Coconala search-objective pattern: every wake refreshes page 1, then
    reads two pages from a mode-600 durable cursor and checkpoints the next page. No query, category,
    keyword, score or suitability rule is added. U13 closes only after consecutive production wakes
    prove cursor advancement; U14 still requires an official proposal ID and replay effect 0.
37. **DURABLE CURSOR LIVE / ACQUISITION PIVOT REQUIRED:** consecutive production wakes advanced the
    official search cursor `4 → 6 → 8 → 10` while refreshing page 1 each time. The latest wake still
    reports balance 0, eligible zero-Connect jobs 0, submitted proposals 0, invitations 0, offers 0
    and Catalog orders 0. Search continuity is fixed, but U13 remains open until a real proposal ID.
    The same resident agent must continue search while shifting spare acquisition effort to the
    already-approved Catalog and profile/invitation surfaces; it must not wait for another manual
    session or create another scheduler/decision engine.
38. **SEARCH CONTINUES / CATALOG PRICE CANARY PENDING PUBLIC READBACK:** later wakes advanced the
    cursor `10 → 12 → 14`; zero-Connect eligibility and submitted proposals remain 0. Direct browser
    inspection found the approved Catalog service visible with one view, zero orders and a $75 public
    price despite a zero-review profile. The existing editor accepted and persisted a $10 draft and
    returned `Project has been saved successfully`, but the public service still reads $75. Treat the
    price experiment as pending, not live, until the public URL itself reads $10; continue job, invite,
    offer, order and free-Connect monitoring meanwhile.
39. **ZERO-CONNECT HACK HYPOTHESIS REJECTED / APPLY PATH REQUIRES CAPACITY:** Upwork's current help
    says Connects are the tokens used for job proposals and that most jobs require them; free awards
    are account-specific and not guaranteed. Current official help says invitations cost zero, while
    Direct Offers and Catalog bypass public applications. User reports largely say balance 0 prevents
    applications; isolated zero-cost public-job reports describe experiments or bugs, not a searchable
    category. Production cursor reached page 14 with no zero-cost public proposal. Stop treating a
    rare exception as the primary strategy. Continue free inbound monitoring, but require an explicit
    owner decision before the reproducible one-time $15/100-Connect public-application canary. Reject
    fake-client, self-interview, multi-account or other manipulation as fraud, not growth tactics.
40. **2026 FIRST-JOB/SCALE RESEARCH INCORPORATED:** current Upwork guidance emphasizes complete
    profiles, portfolios, early job alerts, concise personalized first lines, job-specific proof,
    proposal statistics and repeat client relationships. Current official fee is 0%-15% and fixed per
    contract; Rising Talent can award 30 Connects but requires additional eligibility and its identity
    badge costs 35 Connects. User reports converge on applying early, targeting fewer than 15 competing
    proposals and showing relevant proof, while showing wide variance in proposals-to-first-job and no
    reliable free-public-application route. Adopt one explicitly approved $15 seed for proposal spend
    only, then self-fund up to 10% of verified net received capped at $15/month until three reviews.
    Add funnel stop/repair gates at ten no-view proposals and five viewed/no-interview proposals, then
    climb from one bounded review to repeat work, $100-$500 packages and $500-$2,000 milestones.
41. **ONE-TIME SEED PREFLIGHT COMPLETE / NO CHARGE:** the authenticated Buy Connects page reads
    balance 0, `100 for $15.00`, charge `$15.00 + Tax`, post-state 100 and expiration August 24,
    2027; unused Connects roll over monthly. The ordinary `Buy Connects` control is enabled. No click,
    billing charge, subscription, Plus upgrade, boost or badge effect occurred. After an explicit
    owner capital receipt, the existing loop can purchase once and proceed directly to focused
    proposals without another setup/research step.
42. **SEED PURCHASED / COST-DRIFT BLOCKER FOUND:** explicit owner approval funded one $15 bundle;
    checkout ID `2091725750142893820` completed and official Connects History reads +100 purchased,
    +50 new-member credit and balance 150. The first application wake then failed before effect because
    one sealed candidate's official cost changed from 11 to 14 Connects, and the planner raised instead
    of reaching the next valid 9-Connect candidate. Preserve invalid-payload fail-closed behavior, but
    treat an official cost change as stale qualification and continue to the next sealed candidate.
    No proposal or Connects spend occurred in the failed wake.
43. **CURRENT PROPOSAL UI PREFLIGHT PASS:** Upwork moved public proposal entry from `/ab/proposals/`
    to `/nx/proposals/` and replaced the old cover, bid, duration, balance and submit controls. Update
    only those provider selectors/readbacks and wait two seconds for the SPA form after page load. A
    fresh click-free production-profile preflight now returns `ready=true`, exact job
    `~022091170260597544595`, required Connects 9, available Connects 150 and evidence hash
    `77cf032a…1f84e`. No submit click or Connects deduction occurred during preflight.
44. **UNTRUSTED CLICK PRODUCED OFFICIAL ABSENCE / TRUSTED INPUT NEXT:** the first current-UI wake
    crossed the durable fence but its JavaScript `button.click()` produced no Upwork mutation.
    Authoritative Proposals remained submitted/active 0 and Connects History remained 150, while the
    exact intent entered `reconcile_unknown`. Current Upwork controls require trusted input, as the
    Connects checkout did. Change only the post-fence action to focus the verified Submit proposal
    control and dispatch a CDP Enter key sequence, wait five seconds, then require the official
    proposal ID. Reset only this exact intent after binding the official absence evidence; no blind
    retry is allowed.
45. **TRUSTED ENTER RECONCILED ABSENT / ROOT CAUSE FIXED:** fresh official readback proves proposals
    `0`, active `0`, and Connects `150`, so neither prior attempt created an external effect. Live DOM
    inspection proves the current `Submit proposal` control is `type=button` and has no form; Enter
    therefore cannot submit it. The executor now scrolls that exact verified control into view and
    dispatches one trusted CDP mouse press/release at its measured center after the durable fence.
    Upwork regression is `154 passed`; next release, reset only this absence-proven effect to prepared,
    trigger the existing launchd loop once, then reconcile proposal ID and Connects delta before any
    further acquisition.
46. **FIRST-USE CONNECTS EXPLAINER FOUND:** the trusted Submit click is working, but Upwork intercepts
    the account's first proposal with an official `Use Connects to submit proposals` education dialog
    whose only action is `Close`. Post-attempt official evidence again proves proposals `0` and balance
    `150`. Keep the same sealed proposal and effect identity; within the same fenced attempt, close only
    that exact platform explainer with trusted input, then click the already verified Submit control
    once and require proposal ID plus the exact `150 -> 141` Connects readback. No generic modal
    dismissal, JavaScript click, duplicate retry or new qualification logic is introduced.
47. **EXPLAINER CLOSE COORDINATE REJECTED:** the exact dialog remained visible after a trusted click
    on its rendered Close center; official evidence still proves proposals `0` and balance `150`.
    Replace only that no-effect dismissal with the platform-standard trusted Escape key, require that
    no visible dialog remains, then issue the single trusted Submit click. Failure to close aborts
    before Submit and remains reconcile-only.
48. **EXPLAINER REJECTS ESCAPE:** trusted Escape also leaves the education dialog visible, and the
    executor aborts before Submit; official evidence remains proposals `0`, balance `150`. Because
    closing this exact first-use explanation has no marketplace effect, invoke only its exact `Close`
    DOM control, verify the dialog disappeared, then retain trusted mouse input for the actual Submit.
    No proposal mutation may use a JavaScript click.
49. **ARCHITECTURE CORRECTION — UI JUDGMENT RETURNS TO THE AGENT:** the growing Upwork-specific
    submit sequence is the wrong abstraction. The production proposal model is Luna-first, but the
    submit transport is fixed Python and cannot reason over first-use UI; Coconala already routes
    open-ended browser work through the shared Terra-first `browser-lane-agent` with Sonnet/Gemini
    fallback. Reuse that operator for Upwork and every later market. Deterministic code retains only
    immutable proposal intent, spend/capacity checks, exactly-once fence and official proposal/
    Connects readback. Remove provider-coded dialog/button workflows; give the operator the current
    page, natural-language objective, bounded browser tools and those effect contracts. One loop can
    then adapt to changed or unknown marketplace UI without adding another site script.
50. **SHARED BROWSER OPERATOR WIRED:** after exact form fill and durable effect start, the Upwork
    proposal path now invokes the existing `browser-lane-agent` with its configured Terra model on the
    live authenticated 9233 page. The prompt supplies the immutable job identity and objective but no
    dialog sequence or selector decisions. Provider-specific first-use modal handling and submit-click
    code are removed. The parent keeps the target alive, independently requires official proposal ID,
    then verifies the exact Connects delta before marking the effect verified. The model cannot turn its
    own success claim into a receipt. Upwork regression remains `154 passed`; next evidence is one
    loop-owned live submit and official replay.
51. **AGENT OBSERVED THE NEXT STATE / CEREMONY BOUNDARY CORRECTED:** the first Terra production run
    dynamically passed the Connects explainer, then stopped at a safety-policy acknowledgement because
    the initial prompt classified every acknowledgement as human-only. Official readback proves
    proposals `0` and balance `150`. Ordinary educational and marketplace-safety acknowledgements that
    do not change proposal, price, contract, identity, tax or payment facts are part of the authorized
    browser task; CAPTCHA, identity proof and personal legal/tax declarations remain typed human
    ceremonies. This is one general prompt rule, not an Upwork dialog string or scripted path.
52. **FIRST LOOP-OWNED PROPOSAL VERIFIED:** the second Terra run handled the live safety acknowledgement
    and submitted the immutable proposal exactly once. Official receipt is proposal
    `2091740505918763009`; Connects History names the target job and proves `150 -> 141` (`-9`), while
    a fresh Proposals page proves submitted count `1`. The next wake found no duplicate effect but
    failed read-only inventory because Upwork renders the one-item label as singular `Submitted
    proposal (1)`. Accept singular/plural for this fixed official count field, then prove replay leaves
    proposal count `1` and Connects `141`.
53. **G3 PROPOSAL GATE COMPLETE / REPLAY ZERO:** release `05a6797d2` parses Upwork's singular official
    count and a fresh launchd wake exits `0` with `submitted_proposals=1`, balance `141`, no model call
    and no second effect. A separate post-replay browser read proves the same official count and
    balance. G3 evidence is therefore proposal `2091740505918763009`, exact Connects `150 -> 141`, and
    replay delta `0`. The next active acquisition item is replacing the exhausted static candidate
    cache with loop-owned current-job discovery and Luna proposal sealing whenever no eligible sealed
    proposal remains and the official balance can fund another application.
54. **CURRENT-JOB REPLENISHMENT GENERALIZED:** when no existing sealed proposal is eligible, the same
    authenticated search cursor now scans current jobs regardless of whether balance is zero, opens
    official details and passes every affordable job to the existing Luna-first proposal planner.
    Luna alone decides submit or skip from full job evidence and owner capabilities; deterministic code
    only requires official `required_connects <= balance`, binds those exact values into the immutable
    payload and persists a ready proposal. The former zero-Connect-only discovery name/state and fake
    invitation packet are removed. Upwork regression remains `155 passed`; next proof is a launchd wake
    discovering, sealing and submitting a new current job without editing the static candidate list.
55. **DELIVERY SKILLS BOUND INTO LUNA QUALIFICATION:** the first generalized wake correctly skipped
    physical/location-bound jobs but also rejected feasible work merely because an identical prior job
    or portfolio claim was absent. The existing capability inventory already parses every repository
    `SKILL.md`; pass that signed name/description/path inventory to the Luna planner. Installed Skills
    prove executable and independently verifiable capability, never prior client experience. Luna must
    not fabricate experience, but exact prior work, testimonial or portfolio absence alone is no longer
    a skip reason when a Skill can complete the work; missing implementation details become concise
    pre-contract questions. Regression remains `155 passed`.
56. **FIRST SKILL-AWARE DYNAMIC SELECTION REACHED PREFLIGHT:** production Luna selected and privately
    sealed current job `~022091742848386274963`, `Research and Compile a List of Companies from
    Specific Industries With Issues and Concerns`, at an official cost of 8 Connects and balance 141.
    No provider effect row was created because click-free form validation failed before the durable
    fence. Current money truth remains one submitted proposal, zero replies/offers/contracts and
    Connects 141. Inspect that exact live form, correct only the generic form-control contract, then
    resume the same sealed intent; never regenerate or blind-submit it.
57. **RUNNING COCONALA LANES INSPECTED / REINVENTION CUT:** production is already four Life Manager
    entrypoints from one immutable release: Apply (`application_direct → application_parent`), Reply
    (`reply_detector → ConnectorOutbox`), Paid (`paid_direct → project/workflow/QA ledgers`) and
    Storefront (`storefront_direct → capability/funnel allocator`). The application parent already
    performs parallel discovery, ten-candidate Luna batches, planner/ineligible caches, cursor resume,
    immutable intent fencing, delayed uncertain-effect reconciliation and exact-ID readback. Therefore
    the Upwork per-job Luna loop is not promoted. Next implementation adds Upwork provider effects to
    these existing parents, keeps its observer read-only, then deletes duplicated orchestration.
58. **SCALABILITY CORRECTION — COPY CONTRACTS, NOT CONTROLLERS:** the Coconala inspection proves
    useful lane priority, parallel read-only work, batching/cache/cursor, durable effects, project/QA
    and official receipts. Its large site-specific parent scripts are not the cross-market API.
    Luna/Terra remains the general looping market agent and owns navigation, form interpretation,
    qualification, proposals, replies and ordinary UI across websites. Shared deterministic services
    expose authorization, money/capacity, leases, effects, projects and readback. New markets add a
    manifest plus unavoidable fixed-format transport/readback only; no site gets four copied controllers.
    Item 58 supersedes item 57's instruction to bind new markets directly to Coconala parents.
59. **DYNAMIC JOB PREFLIGHT ROOT CAUSE CLOSED:** the sealed research job's cover, bid `$10`, duration,
    zero screening answers, Connects cost `8`, available balance `141` and enabled Submit control all
    matched. The mismatch came solely from collecting a hidden ARIA live-region message as a validation
    error; the page had zero visible/native invalid controls. Restrict existing error collection to
    visible elements. Fresh click-free production-profile preflight now returns `ready=true`, exact job,
    cost 8, balance 141 and evidence `1009e093…b24a`; Upwork regression is `155 passed`. Next release
    must run the same immutable payload through the existing launchd loop and require proposal ID,
    `141 -> 133` Connects and replay zero.
60. **SEALED PROPOSALS BECOME THE DURABLE READY QUEUE:** the next natural wake returned to discovery
    because it rebuilt candidates only from the repository bootstrap JSON; the dynamic research
    proposal existed privately but was not reloaded. This is restart bookkeeping, not market judgment.
    On every wake, merge valid mode-600 immutable `frozen_waiting_for_connects` payloads from the
    owner-only proposal store into the ready queue, deduped by job ID. No proposal content, score or
    category is inferred. Regression remains `155 passed`; next release must resume the existing
    research payload before spending another Luna call on unchanged discovery.
61. **SECOND LOOP-OWNED DYNAMIC PROPOSAL VERIFIED:** release `f733d9022` reloaded the private sealed
    queue before discovery, passed the corrected click-free preflight and invoked the shared Terra
    browser operator. Official proposal `2091760957211561985` is verified with exact Connects
    `141 -> 133`; a separate fresh Proposals page reads submitted `2`, and Connects History names the
    exact research job with `-8`. No purchase, boost, identity, tax or payment action occurred. The
    next wake must preserve both proposal IDs and spend zero additional Connects on either while any
    newly qualified proposal remains a distinct effect.
62. **SECOND PROPOSAL REPLAY ZERO:** replaying the exact sealed payload returns the same official
    proposal `2091760957211561985` from the verified effect row before any browser mutation. A fresh
    independent Upwork read remains submitted proposals `2` and balance `133`; duplicate proposal and
    additional Connects delta are both zero. The next atomic item is replacing one-job Luna discovery
    with one bounded candidate-set market-agent turn while the reply/offer monitor continues.
63. **ONE LUNA DECISION PER CANDIDATE SET:** public discovery now collects up to ten affordable
    official job packets, passes the full set plus owner facts and installed Skills to one Luna call,
    and asks for the single best positive-utility proposal or one skip for the set. The existing strict
    single-proposal schema is reused; chosen job ID, URL, source hash, Connects cost and balance are
    validated against that packet before sealing. The batch evidence key is the ordered packet-hash
    set, so unchanged candidates reuse the decision rather than repay the model. No regex/keyword job
    judgment or new agent/schema is added. Upwork regression is `156 passed`; next production wake must
    show at most one Luna call per ten inspected candidates and preserve both verified proposals.
64. **VERIFIED EFFECTS NO LONGER BLOCK ACQUISITION:** the first batch release wake spent zero model
    calls and zero Connects, but returned early on the already-verified second proposal instead of
    reaching discovery. Add one generic `ConnectorOutbox` projection of verified resource IDs and
    exclude only those IDs from the acquisition-ready queue; their proposal/history monitoring remains
    intact. Unknown or unverified effects still preempt and reconcile. Regression remains `156 passed`;
    next production wake must reach batched discovery without resubmitting either verified job.
65. **BATCH LUNA PRODUCTION PASS / CACHE IDENTITY FIX:** one natural wake inspected 30 affordable
    jobs in three pages and used exactly three Luna calls, one per ten-job set; all three sets were
    skipped for missing Skill/verification/positive-value evidence. The old path would have used 30
    calls. Existing proposals remained 2, balance 133 and duplicate effects 0. The first batch key still
    inherited packet observation time, so an unchanged next wake would miss cache. Key batches only by
    ordered job ID, official detail hash, Connects cost and current balance; timestamps remain evidence,
    never decision identity. Regression remains `156 passed`; next wake must reuse unchanged page-one
    batch evidence without a new Luna call and evaluate only changed/new sets.
66. **STABLE-KEY CANARY PRESERVED MONEY / RELEASE CONFLICT:** release `0dbeb8784` reached two new
    stable-key candidate sets and used one Luna call for each; both returned skip, while official
    proposals remained 2, balance 133 and duplicate effects 0. The final detail snapshot was
    inconclusive and the wake exited 1 without mutation. Before an immediate same-page cache replay,
    another active Life Manager task switched `current` to Paid release `e3d93c806`, which does not
    contain the Upwork batching/durable-queue changes. The Upwork branch remains pushed and verified;
    do not overwrite the shared production symlink until that concurrent release owner is clear, then
    activate the integrated commit and prove unchanged batch model-call delta 0.
67. **INTEGRATED PARALLEL RELEASE / EXACT CACHE REPLAY PASS:** integrated release `a6412f144`
    contains the active Paid fix and all Upwork batching changes. Coconala Paid and Upwork ran
    concurrently under separate pinned immutable SHAs; neither was stopped. The Upwork wake exited 0,
    retained official proposals 2 and balance 133, and evaluated only changed/new candidate sets.
    Replaying the exact saved ten-job packet set `1c776b…` against its stable evidence directory
    returned the same skip with `summary.json` and `attempts.jsonl` mtime/size byte-for-byte unchanged,
    proving new Luna calls 0. This closes candidate batching/cache hardening. The next atomic item is
    continuous proposal-state/view/reply reconciliation while acquisition keeps running.
68. **SALES RECONCILIATION ROUTES GROUNDED:** fresh official Upwork reads show submitted proposals 2,
    messages 0, offers 0 and contracts 0. Proposal links now carry provider context `Initiated`, not
    `Submitted`; classify that fixed official state as submitted. The sidebar's trailing-slash message
    URL returns 404 in hidden navigation, while canonical `/ab/messages/rooms` renders the Messages app
    and official empty state `Welcome to Messages / Once you connect with a client`. Use that canonical
    URL and accept those provider-authored empty markers. No reply or contract is fabricated. Upwork
    regression remains `156 passed`; next production wake must normalize both proposal IDs as submitted,
    read the real empty inbox and exit 0 while acquisition remains enabled.
69. **CONTINUOUS SALES ZERO-EVENT BASELINE PASS:** integrated release `9adf4fe15` exits 0 with both
    official proposal IDs normalized as submitted, unclassified 0, canonical Messages readback,
    rooms/unread 0, offers/invites/contracts 0 and inbox events appended 0. Proposal count remains 2,
    balance 133 and both effect rows verified. The same wake continues batched acquisition, proving
    Sales monitoring does not serialize or disable Apply. The next external reply/offer must preempt
    acquisition and flow through Luna composition, immutable outbox effect and official message/
    contract readback; until one exists, no synthetic effect can close that live gate.
70. **UPWORK LOOP MERGED TO MAIN / SURVIVES SHARED RELEASES:** the focused Upwork production delta
    was rebuilt from clean remote main, passed 156 tests and compile/diff checks, and fast-forwarded to
    main at `1820eb65a` without unrelated Paid/Storefront changes. Later main Paid release
    `c9a0d00ea` still contains `invoke_batch`, durable verified-effect projection and canonical Messages
    route, proving shared-release updates no longer remove the Upwork loop. Its natural wake exits 0
    with proposal IDs 2, balance 133, rooms/offers/contracts 0, duplicate 0 and 27 affordable jobs
    inspected while other lanes remain independently scheduled. Apply is now a persistent 24/7 main
    capability; the next live gate is an external client reply or offer.
71. **NATIVE BEST-MATCHES FEED REPLACES BLOCKED GLOBAL SEARCH:** authenticated comparison proves
    `/nx/find-work/best-matches` and `/nx/find-work/most-recent` render current personalized job cards,
    including an iOS/webapp opportunity aligned with installed Skills, while the prior global
    `/nx/search/jobs/?sort=recency` now returns a Cloudflare challenge and zero jobs. Use Upwork's native
    Best Matches ranking as the primary discovery surface and retain Luna as the final fit/value judge;
    provider pagination is bookkeeping only. This removes a brittle blocked transport and improves
    candidate relevance without hardcoded categories or a new search agent. Regression remains
    `156 passed`; next main wake must inspect the native feed, preserve existing proposal effects and
    submit only if Luna finds positive verified value.
72. **PUBLISHED PROOF ENTERS QUALIFICATION / CACHE BINDS ALL MODEL INPUT:** native Best Matches exposes
    plausible iOS, AI-integration, invoice-agent and Claude-marketing work, but Luna skipped them because
    it received Skills and the general owner profile without the already-published Upwork portfolio.
    Load the existing private `upwork-profile-state.json` alongside owner facts so exact provider-owned
    project IDs/titles can support truthful examples; never infer more than that evidence states.
    Bind cache reuse to the SHA of the complete prompt, including job evidence, owner/market facts,
    Skill inventory and policy. A changed proof or Skill therefore triggers one fresh Luna decision,
    while identical inputs remain zero-call. Regression remains `156 passed`; next native-feed wake
    must reconsider the same opportunities with official proof and apply only on positive verified value.
73. **EXISTING QA BECOMES A DISCOVERABLE VERIFIER SKILL:** even with published portfolio evidence,
    Luna still returned `no_verified_skill_fit` because delivery Skills require an independent verifier
    but the production artifact/test/visual QA machinery had no discoverable Skill contract. Add one
    instruction-only `gig-delivery-verifier` that routes code/API, research/data, writing/documents,
    presentations and mobile/web builds to existing executable or visual evidence. It never builds,
    submits or approves money; missing modality/evidence is `UNDETERMINABLE`. Skill validation and
    capability-inventory readback pass. A changed Skill inventory changes the prompt SHA, so native
    Best Matches receives one fresh Luna decision rather than reusing the prior skip.
74. **PUBLISHED IOS CAPABILITY BECOMES A BOUNDED DELIVERY SKILL:** native Best Matches repeatedly
    surfaces iOS/webapp and AI-mobile work, and the provider profile already publishes two iOS proofs,
    but inventory had no mobile delivery Skill. Add an instruction-only `mobile-app-delivery` covering
    Swift/SwiftUI, existing-repo repair, REST/documented AI integration, simulator/build/archive and
    store preparation. Explicitly exclude unsupported Android-native, named specialized SDK experience,
    unbounded rebuilds and unauthorized publication. It composes the independent verifier and changes
    prompt SHA, allowing one fresh truthful Luna comparison without inventing prior client work.
75. **DRIFTING PROFILE STATE REMOVED FROM MODEL FACTS:** the first mobile-Skill wake still skipped with
    `official_connects_balance_zero` because the historical bootstrap profile file contained stale
    balance 0 alongside each current job packet's authoritative balance 133. Project only immutable
    provider proof into the planner: provider/profile ID and officially read-back portfolio project
    IDs, titles and public URLs. Exclude Connects, capacity, next action and other time-varying account
    fields; those come from the current wake. Regression remains `156 passed`, and prompt SHA changes so
    Luna re-evaluates rather than caching the contradictory skip.
76. **SELLER-OWNED TERMS NO LONGER REQUIRE CLIENT VALUES:** after current balance and proof were clean,
    Luna still skipped hourly work because the client supplied a rate range rather than one exact bid
    and did not prescribe delivery days. These are proposal decisions, not client facts. Permit Luna to
    choose bid and delivery estimate within the official displayed budget/rate and verified Skill
    capacity, requiring positive expected value and explicit assumptions. Scope, experience, identity,
    credentials and client facts remain non-inventable. Prompt SHA changes; regression stays `156 passed`.
77. **ONE BAD DETAIL CANNOT KILL THE MONEY WAKE:** the pre-terms wake preserved both verified effects
    but exited 1 when one read-only job snapshot redirected or returned incomplete evidence. Retry that
    detail read at most three times with bounded backoff; if all fail, increment `proposal_discovery.incomplete`
    and continue to the remaining candidates. Do not weaken or retry any external proposal effect.
    Regression remains `156 passed`; next wake must exit 0 unless a required account-level surface,
    rather than one optional acquisition candidate, is unavailable.
78. **MISSING CLIENT RATE IS NOT A SELLER-PRICE BLOCKER:** the corrected native-feed wake still
    skipped its best fit because the job detail omitted an hourly range. Upwork asks the freelancer to
    propose the rate; this is a seller decision, not an invented client fact. When a client range is
    shown, Luna stays within it. When absent, Luna chooses a reasonable rate from scope, verified Skill
    capacity, delivery effort and positive expected value and states the assumption. Experience,
    credentials, scope and client facts remain immutable. Prompt SHA changes; regression is `156 passed`.
79. **THIRD HIGH-VALUE PROPOSAL SELECTED / HOURLY PREFLIGHT READY:** with current balance 133,
    provider-published iOS proof, `mobile-app-delivery`, independent verifier and seller-owned pricing,
    Luna selected `~022091764251902772206` (`Transform a webapp to IOS appstore!`) at `$40/hour`,
    14-day estimate and 15 Connects. No effect started because the proposal code required a fixed-price
    duration control that hourly forms do not have. Bind hourly rate to official `#step-rate`, leave
    optional rate increase/boost untouched, and represent duration readback as null for hourly while
    retaining the sealed estimate. Fresh click-free production preflight returns `ready=true`, exact
    job, available 133, required 15 and evidence `5c9e52cc…544cd`; regression remains `156 passed`.
    Next release must produce proposal ID, exact `133 -> 118` and replay 0.
80. **BROWSER MODEL CAPACITY FALLS BACK WITHOUT DUPLICATE EFFECT:** the first hourly submit crossed the
    durable fence but forced Terra returned `Selected model is at capacity` before acting. Fresh
    official evidence proves submitted proposals still 2 and balance 133, so the effect is absent.
    Remove the forced candidate model and use the existing `browser-lane-agent` route: Terra first,
    then configured Sonnet/Gemini fallback. UI judgment and effect/readback contracts stay identical.
    Regression remains `156 passed`; bind the absence evidence to this exact effect, reset it once and
    require proposal ID plus `133 -> 118` before any later retry.
81. **ABSENT RATE-INCREASE TERM MAPS TO OFFICIAL NEVER:** a later Terra attempt reached Submit but
    Upwork rejected the hourly form because its visually optional rate-increase component requires an
    explicit frequency selection. Official absence remains proposals 2 and balance 133. The provider
    options are `Never`, 3, 6 or 12 months. The sealed proposal contains no rate-increase term, so map
    that absence to official `Never`; do not select a percent or boost. This is deterministic form
    projection, not a pricing judgment. Fresh click-free preflight remains ready for exact job/rate/
    Connects, and regression is `156 passed`. Reset only the absence-proven effect once after release.
82. **THIRD PROPOSAL CLOSES HIGH-VALUE HOURLY PATH:** release `0859676d0` resumed the exact sealed
    iOS proposal, explicitly selected no rate increase, used the configured browser-model route and
    submitted exactly once. Official proposal `2091789044149923841` is verified at `$40/hour` with
    exact Connects `133 -> 118` and boost 0. A fresh Proposals page reads submitted 3, Connects History
    names the exact job with `-15`, and exact payload replay returns the same proposal ID with no new
    spend. The application portfolio now contains bounded fixed-price review work, research work and a
    higher-value hourly iOS opportunity. Acquisition remains active while Sales monitors all three.

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
- Reuse: `skills/earn/gig/scripts/providers/upwork_offer_gate.py`
- Reuse: `skills/earn/gig/scripts/providers/upwork_offer_browser.py`
- Reuse: `skills/earn/gig/scripts/providers/upwork_offer_effect.py`
- Modify: `skills/earn/gig/scripts/providers/upwork_browser_provider.py`
- Reuse: `skills/earn/gig/tests/test_upwork_offer_gate.py`
- Reuse: `skills/earn/gig/tests/test_upwork_offer_effect.py`

**Interfaces:** Produces canonical contract state and one acceptance effect.

- [x] Reject terms mismatch, missing fixed-price funding, missing verified hourly billing and
  duplicate acceptance in focused tests.
- [x] Re-read the exact official offer URL and visible scope/amount/deadline/funding immediately
  before the effect.
- [x] Persist the immutable offer decision/terms hash behind the durable provider-effect fence.
- [x] Atomically reserve one concurrent-job slot with that effect; reject a two-offer capacity race.
- [x] Execute at most one authorized acceptance and require an official active `/workroom/{id}`
  contract readback.
- [x] Replay the verified effect with no additional click; the related matrix passes 62/62.
- [ ] Close one real offer and replay it; until an offer exists, keep official contracts/offers at
  zero rather than manufacturing a fixture as live evidence.

Task 15 reuse evidence: the existing Direct Offer lane already performs the offer/contract work
described here, so a second `upwork_contract.py` abstraction is rejected. `upwork_offer_gate.py`
binds offer ID/URL/source hash and exact scope, amount, deadline, account state and payment
protection. `upwork_offer_browser.py` re-reads those terms immediately before the durable fence,
permits one exact `Accept offer` click and accepts success only from an official
`/workroom/{contract_id}` active-contract readback. `upwork_offer_effect.py` makes replay return the
stored contract ID without another click. The remaining code gap is narrower: reservation of the
owner's `concurrent_job_cap` must be writer-serialized with the effect so two concurrent offers do
not both pass a stale active-contract count.

Task 15 capacity evidence: `provider_capacity_reservations` now enters in the same SQLite
`BEGIN IMMEDIATE` transaction that persists a new offer effect. The transaction first hands any
reservation whose contract ID is now present in the official active-contract inventory back to that
inventory, then calculates `official active IDs + unresolved reservations` against the private cap.
At the final slot, the first offer reserves and the second offer raises `provider capacity
exhausted` before any second effect row or click exists. Official contract verification binds the
reservation to its `/workroom/{contract_id}` so the next official wake can perform that handoff.
The focused test was observed RED on the missing `capacity` contract, then GREEN; shared proposal,
message, offer, browser and negotiation effect coverage passes 75/75. No live offer exists, so the
final real acceptance/readback/replay checkbox remains open and revenue remains USD 0. The next
buildable item is Task 16's immutable project workspace, while Task 15's first real acceptance stays
event-driven.

### Task 16: Create an immutable project workspace

**Files:**
- Create: `skills/earn/gig/scripts/project_workspace.py`
- Create: `skills/earn/gig/tests/test_project_workspace.py`

**Interfaces:** Produces owner-only project directory, source manifest, workflow version, deadline,
artifact manifest and client-data policy.

- [x] Write failing tests for path traversal, shared-client directory, missing contract scope and
  secret copied to public/log paths.
- [x] Create one workspace from canonical contract data; mode all private state owner-only.
- [x] Bind inputs and workflow version by SHA-256; preserve revisions rather than overwriting.
- [x] Project canonical lifecycle events into `project_ledger.py`.
- [x] Run focused tests and commit/push.
- [ ] Create the first production workspace from a real official Upwork contract; require its frozen
  workflow identity rather than inventing one after acceptance.

Task 16 evidence: `project_workspace.py` is a narrow security/content-addressing wrapper around the
existing `project_ledger.py`; no second ledger, database, dependency or workspace service was added.
It accepts only the exact canonical contract and frozen workflow keys, rejects traversal and secret
extra fields before creating the base, gives every provider/contract a distinct directory, and uses
an owner-only per-contract file lock. Each contract/workflow pair receives a SHA-256 revision under
`requirements/revisions`, source and workflow manifests, an initially empty artifact manifest and a
fixed owner-only client-data policy. Existing bytes must match exactly; changed scope creates a new
revision instead of overwriting the first. Only hashes enter the append-only economic lifecycle
fact. Directories are mode 700 and files mode 600.

The security REDs reproduced both missing implementation and a nested `requirements/revisions`
symlink writing one private revision outside the workspace before rejection. The implementation now
checks the complete existing tree before any revision write; traversal, provider symlink, nested
symlink, shared-client, missing-scope, secret-extra, replay and revision behavior pass 7/7. OSS code
comparison: Conway Automaton commit `871c53e39b9180920c775759ddc38789699d69ea` supplied resolved
path containment and version archival patterns
(https://github.com/Conway-Research/automaton); profitable-claude commit
`bf1d4f2ac9918a9de0e718786be274167382c547` supplied atomic JSON and deterministic SHA-256 manifest
patterns (https://github.com/Daisuke134/profitable-claude). Automaton's ordinary output overwrite
and default file modes were rejected for client data. GitHub API and DuckDuckGo retrieval were also
attempted but the host resolver was unavailable; these two already-cloned fixed commits were read
directly. Production currently has offers 0, active contracts 0, earnings USD 0 and no
`~/gig/projects/upwork` directory, so no live project or revenue is claimed. The next buildable item
is Task 17's frozen-workflow executor; live Task 16 creation remains gated by a real contract and the
workflow identity frozen before acceptance.

### Task 17: Execute the contracted Skill workflow

**Files:**
- Create: `skills/earn/gig/scripts/workflow_executor.py`
- Create: `skills/earn/gig/tests/test_workflow_executor.py`

**Interfaces:** Produces artifact versions, provenance, cost, elapsed time and execution receipt.

- [x] Write failing tests for uninstalled Skill, changed contract scope, expired deadline budget,
  missing output and secret leakage.
- [x] Execute only the workflow frozen at qualification/contract acceptance.
- [x] Checkpoint each completed step and resume without repeating completed external effects.
- [x] Record model/tool cost and artifact hashes in the private ledger.
- [x] Run focused tests and commit/push.

Task 17 implementation evidence: `workflow_executor.py` reuses the existing generic agent runner;
it adds no agent service, database, marketplace client or delivery effect. Before invoking a model it
recomputes the canonical contract, source-manifest, revision and frozen workflow hashes, resolves the
installed Skill below the configured Skill root, verifies its version and deterministic bundle hash,
and rejects an expired runner-sized deadline budget. The runner works only in a private staging
directory and is instructed to produce local artifacts with zero marketplace, message, delivery,
payment or browser effects. `runner_completed`, `artifacts_validated` and `completed` checkpoints
resume without rerunning a completed runner step. Every artifact is contained, regular, nonempty,
secret-scanned and hashed before any promotion; promotion is content-addressed and collision-safe.
The mode-600 receipt and append-only economic fact contain paths, sizes, hashes, elapsed time and
measured model/tool cost, never client content. Receipt-first crash recovery idempotently repairs a
missing ledger fact without rerunning the Skill. Focused executor plus workspace integration tests
pass 13/13, including a second tick after missing-output/secret rejection proving one runner
invocation, and Python compilation plus `git diff --check` pass. No live execution is claimed:
official Upwork contracts remain 0, so production has no contract workspace to run yet.
Main commit `76291a1fa` is published as immutable release
`76291a1faaa56f5723cb868a43123b09a4f3b893`; release-file SHA-256 is
`aee2a2c0ad2a90f50fdd0aad932ec83f4635c9f81206828eaed28562a8472841`. The same 13 tests pass
from the read-only release and syntax compilation passes with its bytecode cache redirected to a
temporary directory. Launchd readback remains unavailable in the orphaned GUI context, so this
release proof does not pretend that the stopped browser or a nonexistent contract executed it.

### Task 18: Independently verify deliverables

**Files:**
- Create: `skills/earn/gig/scripts/deliverable_verifier.py`
- Create: `skills/earn/gig/tests/test_deliverable_verifier.py`

**Interfaces:** Returns `PASS`, `REVISE`, `BLOCKED` with contract clause, artifact hash and evidence.

- [x] Write failing tests rejecting self-approval, wrong artifact hash, missing contract criterion,
  unsupported factual claim and private-data leak.
- [x] Run deterministic validators before model review.
- [x] Use an independent review context bound to exact contract and artifact hashes.
- [x] Permit delivery intent only from `PASS`; route `REVISE` back to Task 17.
- [x] Run focused tests and commit/push.

Task 18 implementation evidence: `deliverable_verifier.py` is a local, effect-free gate over the
immutable Task 16 contract and Task 17 execution receipt. It treats the exact frozen contract
`scope` as the acceptance clause; a reviewer cannot add or paraphrase a later criterion. Before
trusting the review verdict it contains every artifact below the private workspace, recomputes its
size and SHA-256, compares the caller receipt with the immutable stored receipt and contract hash,
rejects the builder execution ID as reviewer context, and scans bytes for credential, email and
phone-shaped private data. A `PASS` criterion must name the exact clause and nonempty evidence;
each factual claim must carry evidence. Structural, identity, hash and privacy failures return
`BLOCKED`; incomplete/failed criteria or unsupported claims return `REVISE` with
`next_action=execute_workflow`; only `PASS` sets `delivery_intent_permitted=true`. The new verifier,
Task 17 executor and Task 16 workspace focused suite passes 19/19, and Python compilation passes.
This proves the private verification gate only: official Upwork contracts and earnings remain 0,
so no real deliverable has been reviewed or delivered.
Main commit `e089a8f2d8ba70937cbea16859dbcc60dae326b0` is published as immutable release
`20260823T044408-e089a8f2`; verifier SHA-256 is
`74b30ee9442467d96f6bfc488c0d70421e7624490068daa62ef6a62bf45830c3`. The same 19 focused tests
pass from the read-only release and syntax compilation passes with a redirected bytecode cache.
This release readback still does not claim a live Upwork effect: the official account snapshot has
zero submitted proposals, invites, offers, active contracts and earnings.

### Task 19: Deliver an Upwork milestone exactly once

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_delivery.py`
- Create: `skills/earn/gig/tests/test_upwork_delivery.py`

**Interfaces:** Produces submission ID/state and binds it to contract, milestone and artifact hashes.

- [x] Write the lost-ACK/repeated-tick/changed-artifact failing matrix.
- [x] Persist delivery intent only after independent `PASS` and fresh contract readback.
- [ ] Execute one authorized milestone submission with frozen message/files.
- [x] Require official submission ID and `Submitted` state; reconcile before any resubmission.
- [x] Replay with zero duplicate delivery; run tests and commit/push.

Task 19 engine evidence: Upwork's current official instructions say fixed-price work must be sent
through `Deliver work > Your active contracts > Submit work` to start the 14-day review period;
files do not need to be uploaded again when already shared, and only a funded active milestone is a
valid starting point ([submit work](https://support.upwork.com/hc/en-us/articles/211068368-How-to-submit-work-and-milestones-to-your-client),
[fixed-price flow](https://support.upwork.com/hc/en-us/articles/211063718-How-payments-for-milestones-and-fixed-price-contracts-work)).
`upwork_delivery.py` therefore validates the Task 17 artifact bytes/hashes, requires both Task 18
independent-PASS evidence markers, rereads an exact funded/active contract+milestone no more than
five minutes old, and freezes contract, milestone, message, file paths, artifact hashes and
verification hash before the shared provider-effect fence closes retry permission. A lost ACK or
later tick performs readback only. Only an exact official `submitted` row with a nonempty
submission ID, matching contract/milestone/artifact hashes and evidence SHA-256 verifies the row.
The shared ledger now also forbids a second payload for one `deliver_milestone` resource, matching
its existing proposal invariant. Focused delivery/proposal/authorization tests pass 27/27,
including success, lost ACK, replay, changed artifact, non-PASS, forged-PASS and unfunded gates.
This is not a live delivery claim: the official account still has zero active contracts, so no
workroom submission control or real submission ID exists to exercise yet. The external-effect
checkbox stays open until that official receipt exists.
Main commit `c3497d117dd9065eab2eaacb190386279f9389a5` is published as immutable release
`20260823T050059-c3497d11`; delivery-engine SHA-256 is
`1a2ca6bc73147ab893d928c95bdc8f9634b28a0a27fbc2dff14536d3772bc276`. The same 27 focused
tests pass from the read-only release and syntax compilation passes with a redirected bytecode
cache. This release proof is local and cannot satisfy the still-open live submission checkbox.

### Task 20: Process Upwork revisions

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_revision.py`
- Create: `skills/earn/gig/tests/test_upwork_revision.py`

**Interfaces:** Normalizes revision request, in-scope decision, new artifact version and resubmission.

- [x] Write failing tests for duplicate request, out-of-scope work, changed deadline and overwritten
  original artifact.
- [x] Bind revision to provider message/milestone identity.
- [x] Route in-scope work through Tasks 17–19; route scope changes through negotiation.
- [x] Record revision time/cost for economics.
- [x] Run focused tests and commit/push.

Task 20 engine evidence: Upwork's current fixed-price instructions give a client fourteen days to
approve submitted work or request changes, and require the client to use the contract's official
`Request Changes` path. Upwork separately treats milestone title, description, due-date and amount
changes as contract changes that the freelancer must approve or reject; they are not ordinary free
revisions ([review and pay](https://support.upwork.com/hc/en-us/articles/360000980507-Review-and-pay-for-fixed-price-contracts-and-milestones),
[respond to milestone changes](https://support.upwork.com/hc/en-us/articles/360023544173-How-to-propose-or-respond-to-milestone-changes-as-a-freelancer)).
`upwork_revision.py` therefore binds each request to the exact official message, room, contract and
milestone plus source-evidence hash. It re-hashes every originally delivered artifact before routing,
stores an in-scope request as a new immutable manifest, and advances the existing project ledger to
Task 17; Task 18 and Task 19 remain the required following actions. Out-of-scope work and any changed
deadline advance the same durable state to Task 14 negotiation without creating a fulfillment
manifest. Exact replay repairs missing ledger/state only, records one economic fact, and a changed
payload under the same provider identity is rejected. The revision/workspace/executor/verifier/
delivery focused suite passes 31/31, plus the six-case revision suite passes independently; Python
compilation and `git diff --check` pass. This proves the engine only: the last official Upwork state
has zero active contracts and no revision request, so no live revision, rebuilt artifact or
resubmission is claimed. Main merge `d6bf01002758560d015aa7aea64f8dc96567b941` is published as
immutable gig release `d6bf01002758560d015aa7aea64f8dc96567b941`; the revision engine SHA-256
is `71d610948e09fb207df4c004da9a6eb83ce710fdb721e9643de60158b74f5f04`. The same 31 focused
tests pass from the read-only release. The stable `current` pointer resolves to that release, while
launchd argv readback remains unavailable in the orphaned GUI context; deployment is proven, but a
fresh official Upwork wake is not.

### Task 21: Reconcile Upwork payment, fee and payout

**Files:**
- Create: `skills/earn/gig/scripts/providers/upwork_finance.py`
- Create: `skills/earn/gig/tests/test_upwork_finance.py`

**Interfaces:** Implements `list_payments()` returning gross, fee, refund/chargeback, released state,
payout availability and provider transaction IDs.

- [x] Write failing tests separating pending balance, released payment, available payout, refund,
  chargeback and missing source window.
- [x] Normalize official transaction IDs and forbid one transaction in two accounting periods.
- [x] Join payment to contract, delivery and actual execution cost.
- [x] Recognize revenue only from complete released/received evidence; retain missing fields as
  `unknown`.
- [ ] Reconcile the first live payment and commit/push after focused tests pass.

Task 21 engine evidence: Upwork's current fixed-price flow distinguishes work in progress, review,
the five-day `Pending` security hold and `Available`; only Available can be withdrawn
([fixed-price payment flow](https://support.upwork.com/hc/en-us/articles/211063718-How-payments-for-milestones-and-fixed-price-contracts-work),
[earnings statuses](https://support.upwork.com/hc/en-us/articles/211068418-How-to-track-the-status-of-your-earnings-on-Upwork)).
`upwork_finance.py` requires a complete official transaction window and stable provider transaction
IDs, groups gross payment, fee, refund, chargeback and payout without treating absent fees as zero,
and joins the exact contract, Task 19 submission and Task 17 measured execution cost. In-review,
Pending and merely Available balances never become recognized revenue. Revenue and verified net
remain `unknown` until the official payout row is `received` and its amount equals gross minus fee,
refund and chargeback. Each transaction is claimed once to its actual occurrence month; a payout may
arrive in a later month, and revenue is then attributed only to that received month. Exact replay is
idempotent and the same transaction ID in another month is rejected. A later refund or chargeback is
recorded once as negative revenue in its actual month without subtracting execution cost twice. The
ten-case finance suite and the 40-test provider/delivery/revision/executor focused suite pass; Python compilation and
`git diff --check` pass. This is engine proof only: the last official account snapshot has no active
contract, payment or payout, so the first-live-payment checkbox remains open and no revenue is
claimed. Main merge `c0c66c32f562807d8a9d32b604c1019989b3069c` is published as immutable
gig release `c0c66c32f562807d8a9d32b604c1019989b3069c`; the finance engine SHA-256 is
`8a917ad97902d86639a430c97d007059d9abaa1ac2a58ec798624c680cccffd6`. The same 40 focused
tests pass from the read-only release. The stable `current` pointer resolves to this release, while
launchd argv readback remains unavailable in the orphaned GUI context; deployment is proven, but a
fresh official transaction window is not.

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

### Task 22A: Operate Upwork to the USD 10k received-cash gate

**Files:** Modify `skills/earn/gig/scripts/providers/upwork_finance.py` and
`skills/earn/gig/tests/test_upwork_finance.py` only.

**Interfaces:** Add `cash_accounting_period` to normalized cash-relevant rows, then
`summarize_verified_month(rows, accounting_period, source_window) -> int | None`. Require `complete`
and exact first/last calendar-day bounds. For the requested period, sum `verified_net_usd_minor`
where `cash_accounting_period` matches regardless of payment state; return `None` if any such row
lacks join/cost evidence, and reject duplicate transaction IDs.

- [ ] Test partial-month rejection, cross-month payout, an `available` payment with a later negative
  chargeback, pre-payout adjustment, unknown evidence and USD 9999.99/USD 10000.00 boundaries.
- [ ] Repeat the winning Skill and change one strategy variable at a time until a complete month
  returns at least `1_000_000`; then close G11. Other market canaries do not wait for this gate.

## Phase C — Second-market canary through the common browser ACI

Phase C runs concurrently with Upwork. G11 remains Upwork's primary outcome gate, not authority to
block independent read-only discovery, zero-spend canaries or positive-EV work on another market.

**Current execution rule:** Tasks 23–28 below are historical decomposition, not permission to build
six Fiverr-specific controllers. They are superseded by the common `observe/extract/act/readback` ACI
and remain only as acceptance scenarios. Implement one thin manifest plus exceptional authentication,
fee/currency or official-readback glue; reuse the common effect, inbox, project, QA, delivery, money,
Telegram and learning paths. If the canary needs more than three provider files or about 300 LOC,
stop and extract the missing common primitive first.

### Task 22B: Prove the common browser ACI on one second-market canary

- [ ] Reuse the current model-driven browser operator to observe and schema-extract the authenticated
  market without provider-specific semantic routing.
- [ ] Bind one frozen effect to provider/account/source/payload/observation identity before acting.
- [ ] Execute one authorized zero-spend canary and require official provider readback.
- [ ] Project its lifecycle through the existing work-events, Telegram, funnel and money ledgers.
- [ ] Replay with zero duplicate effects and record actual provider-only LOC/files.

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

### Task 58: Project Upwork decisions and funnel receipts to Telegram

**Ponytail constraint:** Reuse the existing Coconala `work-events`, `telegram_report.py` and durable
Telegram outbox. Add no scheduler, notifier, database or provider-specific semantic rules.

- [x] Project each new Upwork apply/skip decision once with a provider-scoped event key and
  model-authored natural-language reason. Reply/offer/contract/delivery/money projections remain.
- [x] Provide one provider-neutral `append_work_event → report envelope → Telegram outbox` path for
  natural-language selected/skipped decisions; focused fake-transport proof reaches `sent` and replay
  appends zero duplicate WorkEvents.
- [ ] Project each new Upwork reply/offer/contract/delivery/money transition once with a
  provider-scoped event key and model-authored reason.
- [x] Wire the production Upwork planner output into the shared path for selected and honest aggregate
  batch-skip decisions; focused production-helper proof appends once and invokes the existing
  `instant-work-events` reporter once.
- [x] Release it, observe one real natural-Japanese planner decision, confirm Telegram message ID
  `31872` through its provider receipt, and prove replay keeps WorkEvent `1 → 1`, outbox row `1 → 1`
  and duplicate send 0.
- [ ] Emit one compact periodic funnel/KPI report and a stalled-stage alert; unchanged polls stay
  silent.
- [ ] Bind each one-variable Luna experiment to its strategy version and later keep/revert evidence.
- [x] Verify one real Upwork decision notification, Telegram message ID and duplicate send 0.

### Task 59: Let Upwork lifecycle lanes progress independently

**Ponytail constraint:** Reuse the existing wake, durable queues and effect fence. Add no provider
scheduler. Fence the narrowest resource and serialize only genuinely shared account state.

- [ ] Split the current wake's durable work into acquire, sell, fulfill, money and learn queue items.
- [x] Run independent hidden-CDP job detail reads concurrently with a locked shared trajectory append;
  production ten-job search-to-all-details improved `49s → 11s` and completion span `44s → 5s`.
- [x] Make one Luna batch return exactly one ordered decision per candidate rather than one winner;
  production release `a81ec3b630` returned 10/10 decisions from one call.
- [ ] Promote main `e846b873e4` or later and prove all decisions append in one WorkEvent handoff with
  every submit proposal sealed before Telegram transport begins.
- [ ] Replace one-proposal-per-wake and the fixed three-contract cap with dynamic workers and measured
  backpressure; ten proposals remain a learning checkpoint, never a stop.
- [ ] Key leases by job, message head, offer and contract/milestone so distinct effects run in
  parallel; use a short global reservation only for Connects/account/KYC/billing/payout state.
- [ ] Prove two different proposals, rooms and contracts progress concurrently while replay of the
  same resource produces zero duplicate effects.
- [ ] Prove queue depth increases workers and provider errors/throttling/deadline risk reduce them
  without hardcoded marketplace-specific counts.
- [ ] Prove paid deadline/revision and unread buyer receive priority without stopping unrelated
  acquisition or fulfillment.
- [ ] Expose per-lane last progress, queue depth, blocker and next action in the existing Telegram
  funnel heartbeat.

### Task 60: Close fourth-proposal readback and protected hourly work

- [ ] After every proposal effect, refresh the official Proposals page and persist the post-effect
  submitted count/entities; proposal 4 must change runtime state `3 → 4`.
- [ ] Replay proposal `2091811328085401601`; require same ID and Connects `92 → 92`.
- [ ] Remove Telegram transport from the acquisition critical path; a notification timeout leaves the
  durable event pending but cannot stop search, proposal sealing or submission.
- [ ] Promote the latest main release and prove one natural wake exits 0 without disk or reporter
  timeout.
- [ ] On an hourly offer, read exact rate, weekly limit, contract fee and verified billing before
  accept/counter/decline.
- [ ] Drive Upwork Desktop App Time Tracker around the exact project task, including meaningful memo,
  related screenshots, adequate activity and limit enforcement; manual time is not protected.
- [ ] Join diary segments, weekly invoice/review, availability, payout and occurrence-month
  adjustments to the contract; only payout `received` enters verified cash.

### Task 61: Freeze the OSS boundary without scaffolding a second framework

- [ ] Move a primitive into `skills/_shared/marketplace-core` only after Upwork plus one second market
  prove identical behavior; do not create empty interfaces for future markets.
- [ ] Add one declarative market manifest per provider containing only official URLs, stable entity/
  state names, currency/fee/payout mapping and supported effects; no judgment or credentials.
- [ ] Run one provider conformance suite over redacted Upwork and second-market fixtures, including
  success, skip, timeout, unknown effect, receipt, refund and chargeback paths.
- [ ] Prove isolated install has zero credentials, identities, customer content, runtime ledgers and
  original absolute paths; defaults perform zero external effects and zero spend.
- [ ] Close OSS alpha only with Upwork real-receipt replay and close OSS stable only after a second
  market reaches official `received` plus clean-device receipt.

### Task 62: Close one real Upwork proposal-to-money path

Only the first unchecked row is active; a missing buyer event blocks that resource, not sibling lanes.

- [ ] Reconcile proposal 4 and replay the same payload; require proposal ID
  `2091811328085401601`, official Submitted proposals 4 and Connects `92 → 92`.
- [ ] Make Telegram delivery a durable independent queue effect; acquisition never waits for OpenClaw
  send/ACK or fails because a notification times out.
- [x] Code the separation: decision events launch the existing reporter asynchronously, while a new
  verified application event is created only from official Proposal ID plus Connects before/after and
  renders `[Upwork][応募完了]`. Production receipt remains.
- [ ] Replace one-proposal-per-wake with job-scoped proposal workers plus an atomic shared Connects
  reservation; prove two sibling jobs can progress and same-job replay effect 0.
- [ ] On the first official buyer message, append its exact room/head before Luna, send one truthful
  reply, read the official story ID and replay the same head with reply 0.
- [ ] On the first offer, read exact scope, rate/bid, weekly limit/milestones, fee, billing and deadline;
  persist Luna accept/counter/decline and require official offer/contract state plus replay 0.
- [ ] Compile active contract into one private project, reserve measured capacity and select an
  installed Skill without copying customer content to logs, fixtures or Telegram.
- [ ] For hourly work, prove Desktop App tracker start/stop, related screenshots, meaningful memo,
  adequate activity and weekly-limit compliance before counting protected time.
- [ ] Produce immutable artifacts, run independent verifier PASS, and freeze the exact accepted
  artifact hash before any delivery or client-visible work-complete message.
- [ ] Deliver once according to contract type and require official submission/story/diary receipt;
  exact replay produces delivery 0. Revisions require a new official buyer head.
- [ ] Reconcile work diary/milestone, invoice, review, gross, actual fee, Connects/model/tool cost,
  refund/dispute/chargeback, availability and payout; only payout `received` enters cash.
- [ ] Request only an honest review, capture repeat-work identity, attribute the complete funnel and
  emit one evidence-backed keep/revert/pause decision.

### Task 63: Remove the harmful installed-Skill application gate everywhere

- [x] Establish one shared Coconala-derived feasibility policy: apply to every legal job the general
  agent can truthfully complete with model/tools; skip only actual policy, embodied, legal, identity,
  scope, deadline or negative-economics impossibility.
- [x] Remove `INSTALLED_SKILLS` and capability inventory from the Upwork application prompt. Missing
  Skill, exact tool history, domain job, testimonial, portfolio or prior result has zero skip authority.
- [x] Define Skills as optional caches for repeated profitable methods, never application or execution
  prerequisites; the agent may perform work directly without creating a Skill.
- [x] Run prompt regressions proving Coconala and Upwork both include the common policy and Upwork
  contains none of `INSTALLED_SKILLS`, `installed Skills can complete`, or Skill-based skip language.
- [x] Replay the previously skipped Mobile App and Website Developer evidence through the repaired
  planner: the same job `~022091720689866384000` now returns `submit`, USD 35/hour and a phased
  iOS/Android/Web plan with external effects 0 and no missing-Skill reason.
- [x] Release the repaired prompt: production `71d41b8e35` returned 2 submit / 8 skip from ten current
  candidates with zero missing-Skill reason. A delayed Skill-based Telegram message was traced to a
  pre-repair event and remaining stale unknown reports were fenced from redrive without deleting history.
- [x] Prove feasible high-value jobs are submit-by-default with a same-ten-candidate read-only replay:
  8 submit / 2 skip; both skips require phone/live handling, while Skill/payment/history/duration/
  Connects-only skips are 0. Production promotion remains.
- [ ] Apply the same invariant to Fiverr, Lancers, CrowdWorks, Freelancer, Mercor, uGig and unknown
  markets through provider conformance; no provider-specific capability matrix or brain is allowed.

### Task 64: Retire provider-specific application form scripts

- [x] Add one provider-neutral `market_form_operator.py` that passes provider, resource URL and sealed
  intent to the existing Terra `browser-lane-agent`; it contains no site selectors or form policy.
- [x] Bypass Upwork deterministic form filling in the acquisition path. Fence from the already-read
  official Connects receipt, let Terra operate the whole form, then independently read Proposals and
  Connects pages for Proposal ID and exact delta.
- [x] Repair the first common-operator canary: require the authenticated persistent default context,
  never isolated/incognito; add generic no-effect reconciliation from official resource absence plus
  unchanged balance so the same fenced intent can safely retry.
- [ ] Replace Upwork deterministic form filling/preflight selectors with one Terra common-Browser-ACI
  task: inspect current form, fill the sealed intent, resolve ordinary validation feedback and submit.
- [ ] Keep deterministic code only for immutable intent hash, resource lease, Connects reservation,
  at-most-once effect fence and official Proposal ID/Connects readback.
- [ ] Reduce `upwork_proposal_browser.py` to an optional token-saving fast path with zero judgment.
  Any mismatch before effect must immediately hand the same sealed intent to Terra in the same wake;
  it may never skip, abort acquisition or be the only route.
- [ ] Prove the same Terra form task works on two differently shaped Upwork jobs without code changes;
  each returns official Proposal ID, exact Connects delta and replay effect 0.
- [ ] Use the same ACI task unchanged for the first Fiverr/Lancers/CrowdWorks/Freelancer/Mercor/uGig
  canary; add no site-specific form script.

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
