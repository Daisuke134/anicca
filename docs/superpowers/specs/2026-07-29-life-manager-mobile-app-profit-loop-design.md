# Life Manager Mobile App Profit Loop — Design

**Status:** Design updated; pending written-spec review

**Owner:** Life Manager

**Parent SSOT:** [Life Manager Finance + Marketing Platform](./2026-07-29-life-manager-finance-marketing-platform-design.md)

**Pilot window:** RevenueCat Shipaton 2026

**Implementation gate:** This written design must be reviewed before the
implementation plan begins.

## 1. Decision

Build a **Mobile App Profit Loop** inside the Life Manager architecture, but
enter Shipaton with **one new consumer mobile app selected by evidence**, not
with the factory itself and not with the already-released Anicca app.

The Mobile App Profit Loop is one business unit beneath a **global Life Manager
CFO Agent**. The CFO allocates limited token, API, cash, and Mac capacity across
all Life Manager businesses. It is not a mobile-only portfolio governor.

The system is the durable product. The selected consumer app is the Shipaton
proof that the system can find a real problem, build a high-quality native
solution, pass review, acquire users, monetize, learn, and improve.

The first canary is the existing Anicca iOS app because it already has release,
subscription, analytics, and review history. It is used to prove observation,
diagnosis, rejection handling, and bounded iteration. It is not eligible as the
Shipaton submission because Shipaton requires a brand-new app.

### Done condition

The Shipaton pilot is done only when all of the following are true:

1. One new app has a public App Store URL, RevenueCat-backed purchase path,
   production analytics, privacy disclosures, and review-compliant UX.
2. Its opportunity choice, build, verification, submission, review response,
   release, marketing experiments, costs, and metric observations have durable
   machine-readable receipts.
3. The loop makes its next decision from the measured bottleneck rather than
   from a fixed calendar or an app-count quota.
4. At least one bounded product, paywall, onboarding, pricing, or marketing
   experiment reaches a keep/revert decision.
5. Revenue, refunds, attributable acquisition cost, model/API cost, and
   infrastructure cost reconcile into contribution profit.
6. Every app-changing action remains reversible through Git, release, config,
   or experiment rollback.
7. The reusable contracts can be ported into Life Manager Order 37 without
   creating a second scheduler or a second source of truth.
8. Every mission has a hard token, API, cash, elapsed-time, and scarce-resource
   budget, and its actual usage settles back into the global CFO ledger.
9. Product continuity survives process and model restarts because product
   state lives in a durable Product Cell rather than in an always-running LLM
   conversation.

## 2. Shipaton facts and operating dates

The official RevenueCat announcement and current Devpost overview define the
published competition requirements. Devpost states that the final Official
Rules are not yet available, so a rules-snapshot gate must run before release
and again before submission. The dated operating plan uses Japan Standard
Time.

| Event | Date | Operating consequence |
|---|---:|---|
| Preparation may begin | Before August 1, 2026 | Research, specs, architecture, and non-release preparation are allowed |
| Conservative eligible release window opens | August 1, 2026, 16:00 JST | Devpost's submission period begins at August 1 00:00 PDT; do not release earlier even though the general announcement states August 1 |
| Builders Weekend, Shibuya | August 8, 2026, 10:00–19:00 | Use it as a focused build-and-user-test milestone |
| Internal App Store target | August 15, 2026 | Leaves review and rejection recovery time |
| Internal Devpost freeze | September 24, 2026 | Leaves six days for asset, link, and eligibility failures |
| Internal submission deadline | September 30, 2026 JST | This is earlier than Devpost's September 30 23:45 PDT deadline and preserves a timezone buffer |

The Grand Prize is **$100,000**. Devpost currently itemizes more than
**$685,000** in prizes, while RevenueCat describes the growing cash pool as
more than **$700,000**. The Japanese campaign page describes total prize value
above **$1 million**. These are different scopes, so the loop stores each claim
with its source rather than merging them into one number.

The provided Builders Weekend page currently promises Replit Agent 4 credits
through August 10. It does not currently mention a Codex device, "Codex
Macro," or a hardware prize. No planning assumption depends on that prize.

### Eligibility and submission gates

| Gate | Requirement |
|---|---|
| Rules snapshot | Re-fetch and archive the final Official Rules before first public release and before Devpost submission; new terms override this design |
| Product | A brand-new app, not an update to an existing released app |
| Platform | iOS, iPadOS, macOS, or Android; this pilot chooses native iOS |
| Monetization | RevenueCat SDK with at least one in-app/web purchase, or ads |
| Availability | First public release between August 1 and September 30 |
| Submission | Description, public store URL, public demo video no longer than two minutes, 1024×1024 icon, 1179×2556 screenshot, and trial/promo access where applicable |
| Judging | Grand Prize emphasizes traction and growth; the HAMM category rewards effective use of RevenueCat to drive real revenue |

## 3. Evidence and inference

### Evidence

| Observation | Consequence |
|---|---|
| `Daisuke134/mobileapp-builder` already covers native Swift scaffolding through App Store submission | Reuse it as the initial build/release adapter instead of building another generator |
| Etnamute exposes explicit spec, design, build, improve, fix, test, market, and release stages | Copy its lifecycle separation and headless verification pattern where compatible |
| AppFlight advertises local native Swift generation, simulator use, signing, submission, rejection fixing, RevenueCat, analytics, and marketing | A generic "AI app factory" is already a crowded product category |
| Factory App describes a ten-stage quality-gated factory but explicitly centers single-shot builds | Generation alone does not close the business learning loop |
| Apple Guideline 4.2.6 restricts commercialized template/app-generation services and Guideline 4.3 rejects repetitive or indistinguishable apps | The system must optimize uniqueness and quality, not app volume |
| Apple Calendar and existing apps already offer travel-time and leave-now planning | A Life Manager travel-time app is not automatically the strongest Shipaton opportunity |
| RevenueCat's 2026 benchmark reports stronger iOS download-to-paid conversion than Google Play and much stronger annual than monthly renewal | Native iOS and durable value are rational pilot defaults; short-term trial starts alone are insufficient |
| RevenueCat reports AI apps with stronger early monetization but weaker retention and higher refunds | "AI" is not accepted as a durable advantage without retention evidence |
| The current Life Manager platform plan measures only about `$20 MRR`, five active subscriptions, zero trials, and incomplete product-level attribution | The first missing capability is trustworthy observation and diagnosis, not more app generation |

### Inference

| Inference | Why it follows |
|---|---|
| The factory should be the engine, not the Shipaton entry | A new consumer app can demonstrate traction; an infrastructure product would need both its own users and generated-app results inside the same short window |
| The loop must begin with existing-app iteration | Existing products provide real review, funnel, revenue, and retention evidence before opportunity generation is trusted |
| Only one new Shipaton app should be active | Focus improves quality, review recovery, learning speed, and judging traction while reducing Apple spam risk |
| Profit is a better north star than app count, downloads, impressions, or MRR alone | It incorporates proceeds, refunds, acquisition cost, infrastructure, and model/API cost |
| Local-first is required for the pilot | Xcode, signing, simulator, and App Store upload require a macOS-capable worker; a generic Linux cloud worker cannot replace it |

## 4. Approaches considered

| Approach | Strongest case | Fatal weakness for this pilot | Decision |
|---|---|---|---|
| Build an iOS Life Manager app | Existing Telegram behavior and a narrow daily/leave-time loop make a fast demo possible | Existing travel-time solutions and Apple Calendar reduce differentiation; the product choice is desire-led rather than evidence-led | Reject as the predetermined entry |
| Submit the autonomous app factory itself | It matches the long-term vision and is technically impressive | AppFlight and other factories already cover the visible demo; infrastructure traction is difficult within the Shipaton window; scope can consume the release window | Reject as the entry |
| Build the profit loop and ship its best new consumer app | Demonstrates the system through a real App Store product, revenue path, and measured learning while preserving the long-term factory asset | Requires a strict scope boundary so the engine does not become the project | **Select** |

The Life Manager daily/leave-time concept remains an opportunity candidate. It
wins only if the evidence engine ranks it above alternatives on reach, impact,
confidence, effort, willingness to pay, native-mobile advantage, and available
distribution.

## 5. Prior art to copy and adapt

| Source | Reuse | Do not copy |
|---|---|---|
| `Daisuke134/mobileapp-builder` | Native Swift project creation, quality phases, App Store Connect, localization, screenshot, build, upload, and submission flow | A single-shot "finished at submission" definition |
| Etnamute | Explicit lifecycle stages, iterative improve/fix commands, Maestro, simulator evidence, headless CI shape | Expo/React Native as the pilot default |
| fastlane | Deterministic build, screenshots, metadata, upload, and release automation | Treating a successful upload as a successful business |
| App Store Connect CLI/API | App, build, review, subscription, analytics, and message automation | Blind retries or storage of Apple ID passwords |
| RevenueCat | Entitlement, product, trial, conversion, renewal, refund, and revenue truth | Optimizing trial starts without downstream retention and profit |
| PostHog-compatible product analytics | Event funnels, feature flags, and experiment assignment | A second revenue source of truth |
| Maestro and XCTest | Repeatable critical-path and native behavior verification | Screenshot-only success claims |
| RICE | Reach, impact, confidence, and effort ranking based on measured evidence | Invented scores without source receipts |
| Lean Build–Measure–Learn | Smallest experiment that tests the current bottleneck | Fixed daily feature churn |
| OpenAI Agents SDK | Manager-controlled agents-as-tools, structured outputs, traces, run usage, and bounded specialist calls | Free-form agent chat as the durable state store |
| OpenAI Financial Research Manager | Plan, parallel research, specialist tools, independent verification, one bounded revision, and fail-closed output | Allowing an unverified CFO narrative to authorize spend |
| LangGraph supervisor pattern | Hierarchical supervisors and tool-based delegation with controlled context | A peer-to-peer swarm with no accountable manager |
| Temporal OpenAI Agents samples | Durable workflows, retries, signals, queries, cancellation, and deterministic gates around agent calls | Keeping one LLM process alive forever |
| Temporal Resource Pool | Serialized access to Xcode, simulators, repositories, browser profiles, and App Store mutations | Unbounded parallel jobs competing for the same machine or account |
| Nodenester AppFactory | `observe → prioritize → act → learn`, opportunity scanning, review mining, build, test, and submission adapters | Its app-count capacity trigger and RevenueCat project-list call as a profit allocator |
| App Store Scraper MCP | Store search, details, keyword competition, reviews, pricing, screenshots, and version history | Treating scraped estimates as first-party revenue truth |
| Mobbin official MCP | Production screen and multi-step flow research | Copying proprietary screens, assets, or brand expression |
| ASO App Store Screenshots skill | Deterministic screenshot composition followed by bounded visual enhancement | Generating text, device geometry, and every screenshot pixel nondeterministically |
| TrustMRR / Flippa / Apple app transfer | Verified revenue package, diligence artifacts, original source, and transfer readiness | Building clones or assuming every app should be sold |

### 5.1 Adjudication from the 2026-07-29 deep code hunt (adopt vs copy vs build)

Two deep GitHub hunts (code actually read, not README-only) produced this
binding adjudication. "Build" is only allowed where the hunt confirmed no
mature solution exists.

| Loop part | Best existing solution | Stars / activity | Verdict |
|---|---|---|---|
| ASC 2FA automation | `asc`-bundled `scripts/get-apple-2fa-code.scpt` — polls macOS FollowUpUI accessibility tree for the 6-digit code, auto-clicks trust dialogs | rorkai/App-Store-Connect-CLI 5,337★, daily commits | ADOPT — direct answer to the `WAITING_FOR_HUMAN` gate that killed all 7 factory apps |
| App Privacy declarations | `asc web privacy catalog/pull/plan/apply/publish` (web-session ops absent from the public API) | same | ADOPT — direct answer to the desk-stretch blocker |
| Review submission / beta localizations | `asc` API + `asc web review` | same | ADOPT (fix call order only) |
| fastlane spaceauth for metadata | Session lifetime "1 day to 1 month, region-dependent" per official docs | 40k★ | REJECT for metadata/web ops; keep fastlane for binary build/upload only |
| Build-loop hardening | umputun/ralphex — fresh session per task, staged review pipeline, completed-plan archival | 1,402★, active | COPY-PATTERN into ralph.sh |
| Whole-factory OSS | None exists (all candidates 0–1★ scaffolds) | — | BUILD justified (verified) |
| CFO / budget / mission contracts | None exists. Skeleton = Temporal openai_agents manager pattern + adenhq/hive DAG/persistent-memory design (10.8k★) | — | BUILD justified (verified) |
| ASO skills | Eronred/aso-skills 1,685★ — already installed locally (aso-audit etc.) | active | ADOPTED — pull updates only |
| ASO keyword scoring | facundoolano/aso traffic/difficulty formulas | 854★ (stale code) | COPY-PATTERN (formulas only) |
| App Store data | facundoolano/app-store-scraper | 1,399★ | ADOPT |
| Apple Search Ads client | phiture/searchads_api (agency-grade full client) | 61★, active | ADOPT |
| TikTok posting | wkaisertexas/tiktok-uploader — cookie-injection auth, merges with CloakBrowser daily-driver | 756★, active | ADOPT |
| Vertical video generation | MoneyPrinterTurbo | 100k★ | ADOPT (generation side) |
| Per-post attribution on iOS | No OSS exists. Practical path = App Store custom product pages with distinct links | — | BUILD thin + one E2E measurement to make it fact |
| App Review reply automation | No mature OSS for App Store | — | BUILD thin (asc review API + LLM) |
| Paywall A/B | No OSS; local `paywall-ab` skill already equals or exceeds | — | USE existing |
| Exit / sale automation | Nothing exists | — | BUILD later |

Unverified items to be closed by T1 execution: real-device run of
`get-apple-2fa-code.scpt`; actual `asc web` session lifetime.

## 6. System boundary

### 6.1 Pilot boundary

The Shipaton pilot runs in an isolated local worktree and may invoke existing
mobile-app-builder, App Store Connect, fastlane, RevenueCat, analytics, test,
and marketing adapters.

Before Life Manager Order 26 passes, the pilot must not:

- modify the live Life Manager scheduler;
- create another persistent scheduler;
- write into production Life Manager ledgers;
- become a hosted multi-tenant feature;
- change OpenClaw migration ownership;
- submit multiple near-identical apps;
- advertise guaranteed income.

It may emit signed, portable JSON receipts and append-only pilot ledgers. Order
37 imports the validated schemas and workers into the canonical Life Manager
runtime after the runtime/cloud migration gate passes.

### 6.2 Components

```text
Life Manager CFO Agent
├── Treasury / Policy Engine
│   ├── global revenue, cost, cash, token, API, and compute ledger
│   ├── hard spend and capacity caps
│   └── signed Business Budget Envelopes
├── Mobile Studio Manager
│   ├── Market Intelligence Agent
│   ├── Product Strategist Agent
│   ├── UX Research Agent
│   ├── Build Agent
│   ├── QA / App Review Agent
│   ├── Release Agent
│   ├── Growth / Monetization Agent
│   └── Exit Agent
├── Web Business Manager
├── Marketing Business Manager
└── future Business Managers
```

The CFO is the accountable top-level manager. It does not write application
code, operate Xcode, publish content, or mutate App Store state. It issues a
bounded budget envelope to a Business Manager, receives verified settlement
evidence, and decides whether to continue, reduce, pause, or reallocate.

The Mobile Studio Manager owns mobile business outcomes. Specialist agents are
shared, replaceable workers exposed as tools. They do not chat freely with one
another and they do not remain resident per app. The manager composes them
inside a deterministic workflow and receives typed outputs.

Each app owns one durable **Product Cell** containing identity, source,
connectors, releases, metrics, costs, hypotheses, experiments, review state,
budget history, and exit readiness. A temporary Product Lead is instantiated
for one mission, reads only the relevant Product Cell snapshot, invokes
specialists, writes verified results, and terminates.

| Component | Responsibility | Durable output |
|---|---|---|
| Global CFO Agent | Compare all Life Manager businesses and authorize bounded capital/capacity allocation | `CfoDecision`, `BusinessBudgetEnvelope` |
| Treasury / Policy Engine | Enforce hard cash, token, API, time, credential, effect, and capacity limits independently of LLM output | `BudgetClaim`, `BudgetSettlement`, `PolicyDecision` |
| Mobile Studio Manager | Select the best eligible mobile mission and coordinate specialists as tools | `MobileMissionDecision`, `Mission` |
| Product Registry / Product Cell Store | Preserve per-app identity, state, evidence, learning, budgets, and exit readiness | `Product`, `ProductCellSnapshot` |
| Opportunity Engine | Gather pain, competitor, review-gap, willingness-to-pay, native-advantage, and distribution evidence; calculate RICE | `OpportunityEvidence`, `OpportunityDecision` |
| Market Intelligence Agent | Search App Store rankings, competitors, reviews, pricing, screenshots, releases, TikTok signals, and public demand evidence | `MarketEvidencePack` |
| UX Research Agent | Query Mobbin screens/flows and public screenshots; extract interaction patterns without copying assets | `UxPatternPack` |
| Product Strategist Agent | Turn current bottleneck and evidence into one falsifiable mission with economics and rollback | `MissionProposal` |
| Build/Release Adapter | Call mobileapp-builder phases, Xcode, tests, fastlane, and App Store Connect | `BuildReceipt`, `Release` |
| QA / App Review Agent | Verify critical flows; read exact review messages; classify and test the smallest repair | `VerificationReceipt`, `ReviewIssue`, `ReviewResponseReceipt` |
| Growth / Monetization Agent | Design one attributed acquisition, onboarding, paywall, pricing, or retention experiment | `Experiment`, `PublicationReceipt`, `AcquisitionObservation` |
| Observation/Attribution | Reconcile App Store, RevenueCat, product analytics, marketing, refunds, and costs without converting missing data to zero | `MetricObservation`, `AttributionSnapshot` |
| Experiment Controller | Assign, ship, monitor, and keep/revert one product or marketing change | `ExperimentDecision` |
| Resource Pool | Lease repositories, Xcode builders, simulators, browser profiles, and external mutation scopes | `ResourceLease` |
| Exit Agent / Packager | Compare hold and sale value; prepare verified revenue, IP, dependency, operations, listing, and transfer artifacts | `ExitDecision`, `AssetTransferPack` |
| Durable Workflow Engine | Persist state, retries, signals, cancellation, timeouts, and receipts around bounded agent calls | `WorkflowRun`, `AgentRunUsage` |

No LLM decision directly spends money or mutates production. It creates a
typed proposal. The deterministic policy engine validates the proposal,
claims a budget and required leases, then dispatches an existing worker. Every
effect has an acceptance test, timeout, rollback, idempotency key, and receipt.

### 6.3 Budget hierarchy

| Level | Owner | Constraint |
|---|---|---|
| Global weekly envelope | CFO + Treasury policy | Total token, API, cash, Mac time, and external-effect cap across Life Manager |
| Business envelope | Business Manager | Maximum allocation for Mobile, Web, Marketing, or another business |
| Mission envelope | Product Lead | Maximum spend and duration for one measurable business hypothesis |
| Agent-call envelope | Workflow engine | Per-call model, token, tool, retry, and elapsed-time limit |

The CFO ranks eligible missions using evidence-backed expected incremental
contribution profit, confidence, total mission cost, downside, strategic
learning value, and scarce-resource opportunity cost. Missing inputs remain
unknown and cannot be replaced by invented numbers. Hard caps always outrank
an LLM recommendation.

### 6.4 Concurrency and ownership

| Resource | Ownership rule |
|---|---|
| Product Cell | Many readers; one active state-changing mission |
| Git repository/worktree | One write lease per product mission |
| Xcode builder | Capacity-limited lease based on measured Mac resources |
| Simulator/device | One exclusive lease per device |
| App Store Connect | One app-scoped mutation lease |
| RevenueCat catalog | One project-scoped mutation lease |
| Browser profile | One credential/profile mutation lease |
| Experiment surface | One primary experiment per funnel stage unless interaction is explicitly designed |

Research may fan out in parallel. Mutations remain serialized at the narrowest
safe resource boundary. Emergency crash, billing, privacy, security, or App
Review work preempts growth and new-build jobs.

## 7. Durable data contracts

| Entity | Required fields |
|---|---|
| `Business` | stable ID, manager, revenue/cost sources, policy, current envelope, status |
| `BusinessBudgetEnvelope` | business ID, period, cash/token/API/Mac caps, allowed effects, expiry, issuer, signature |
| `Product` | stable ID, name, repository ID, bundle ID, App Store ID, category, stage, creation source, connector refs, policy state |
| `ProductCellSnapshot` | product ID, version, lifecycle state, release/review state, current bottleneck, metrics, costs, hypotheses, experiments, budget history, learning, exit readiness |
| `OpportunityEvidence` | query, source URL, captured time, evidence type, market/problem statement, raw excerpt hash, freshness, confidence |
| `OpportunityDecision` | candidate IDs, RICE inputs, willingness-to-pay evidence, native advantage, distribution evidence, disqualifiers, winner, rationale |
| `Mission` | business/product ID, objective, hypothesis, expected contribution movement, evidence refs, success/stop gates, budget, effects, leases, timeout, rollback |
| `AgentRunUsage` | mission ID, agent role, model/provider, requests, input/output tokens, tool/API use, elapsed time, estimated and settled cost |
| `ResourceLease` | resource type/ID, mission holder, acquisition/expiry, heartbeat, release receipt |
| `Release` | product ID, Git commit, semantic version, build number, artifact hash, test receipt refs, ASC state, public URL, rollback |
| `ReviewIssue` | exact ASC message ref, guideline, affected version, classification, repair hypothesis, test, response, resolution |
| `Experiment` | hypothesis, bottleneck metric, eligibility, variant, budget, start/stop gates, guardrails, rollback |
| `MetricObservation` | product ID, source, metric, numerator, denominator, window, value, currency/unit, freshness, availability |
| `Decision` | observation refs, alternatives, selected action, expected metric movement, budget, expiry, rollback |
| `CostLedger` | product ID, acquisition, model/API, infrastructure, Apple allocation, tools, refunds, attributable operations |
| `ProfitSnapshot` | proceeds, refunds, variable costs, allocated costs, contribution profit, observation window, reconciliation state |
| `CfoDecision` | compared business/mission IDs, evidence refs, envelope changes, selected allocation, rejected alternatives, expiry, policy receipt |
| `ExitDecision` | product ID, hold-value evidence, sale-value evidence, transfer eligibility, recommendation, constraints, expiry |
| `AssetTransferPack` | source/IP manifest, revenue verification, dependency bill, credentials transfer map, operational runbook, Apple transfer checklist |

Every record is business-scoped and, when applicable, product-scoped.
"Unavailable," "stale," and "zero" are different states. A decision cannot
use a metric whose denominator, window, or source is absent.

## 8. The operating loops

### 8.1 Global CFO loop

```text
collect verified revenue, cost, token, API, capacity, and risk observations
  → settle completed Business and Product missions
  → reject stale, unreconciled, or policy-ineligible proposals
  → compare eligible missions across all businesses
  → issue signed Business Budget Envelopes
  → Business Managers execute bounded missions
  → verify effects and settle actual cost/outcome
  → continue, reduce, pause, reallocate, or exit
  → repeat weekly; interrupt immediately for material risk
```

The CFO is an agent-assisted decision layer over a deterministic treasury
policy engine. The policy engine, not the model, is the final authority on
hard spend and effect limits.

### 8.2 Mobile Studio loop

```text
observe every Product Cell and new-market evidence
  → classify urgent review/billing/crash/privacy work
  → compare iterate / market / build-new / hold / retire / sell missions
  → request a Mobile Business Budget Envelope from the CFO
  → select one bounded mission
  → claim product and resource leases
  → execute the typed specialist DAG
  → verify, release, market, or package
  → measure the declared success metric and guardrails
  → settle incremental contribution profit and total cost
  → update the Product Cell
  → submit the next evidence-backed proposal
```

The initial WIP is one new-app build slot and one live-product experiment
slot. This is a starting capacity policy, not a permanent portfolio size.
Capacity increases only after resource use, review quality, attribution,
retention, refunds, and contribution profit remain controlled.

### 8.3 Per-product mission loop

```text
load immutable Product Cell snapshot
  → instantiate temporary Product Lead
  → parallel evidence collection where independent
  → propose one falsifiable mission
  → independent evidence/policy verification
  → claim budget and resource leases
  → build/test/release/market through deterministic adapters
  → rejected or failed
      ↳ read exact evidence → classify → smallest tested repair → retry within cap
  → observe until the declared stop rule
  → keep / revert / inconclusive
  → write receipts and a new Product Cell version
  → terminate Product Lead
```

An app has durable ownership without a resident LLM. The Product Cell is the
memory; the workflow is the process; the temporary Product Lead is the
mission-scoped reasoner.

### 8.4 Timing

| Trigger | Loop |
|---|---|
| Event-driven | Crash, billing failure, privacy/security issue, rejection, review message, failed release |
| Daily | Refresh metrics/reviews, detect anomalies, advance active workflow, enforce expiries |
| Weekly | CFO settlement and cross-business envelope allocation |
| Experiment stop rule | Keep, revert, or mark inconclusive |
| Monthly | Continue, park, rebuild, retire, or exit review |

### 8.5 System-improvement loop

The outer loop improves the system only after the product loop yields repeated
evidence:

1. Group failures and wins by stage, category, and evidence quality.
2. Propose one change to a prompt, rule, template, test, threshold, or adapter.
3. Replay it against prior receipts and a held-out case.
4. Canary it on one non-destructive job.
5. Promote only when it improves the target without violating quality,
   review, privacy, cost, or retention guardrails.
6. Store the promoted rule version and rollback receipt.

One app result cannot rewrite the global strategy. Product-specific learning
stays in the product pack until it repeats across products.

## 9. Decision policy and quality gates

### 9.1 Opportunity gate

A candidate cannot enter build until it has:

- first-party or attributable evidence of a repeated painful job;
- competitor review gaps or documented workflow friction;
- at least one credible willingness-to-pay signal;
- a reason native mobile is materially better than a web page or chatbot;
- an identifiable distribution path;
- a uniqueness review against Apple Guidelines 4.2.6 and 4.3;
- RICE inputs linked to evidence receipts;
- a two-week shippable scope.

The highest eligible RICE score wins. Confidence is capped by the weakest
required evidence class. No candidate receives reach or impact points from
unattributed social impressions.

### 9.2 Work-in-progress and release gates

| Gate | Rule |
|---|---|
| WIP | One new app and one active product experiment |
| Release date | No public Shipaton release before August 1 at 16:00 JST; re-check the final Official Rules first |
| Originality | No reskin, clone, repeated bundle, or template-identical submission |
| Native quality | Critical XCTest/Maestro paths pass on the target iPhone; launch, purchase, restore, offline/error, account/privacy, and accessibility paths are verified |
| Monetization | RevenueCat offering, entitlement, purchase, restore, cancellation explanation, and price disclosure are production-verified |
| Review request | Never during onboarding or immediately after launch; request only after a completed value-producing sequence |
| Privacy | Data collection, analytics, AI behavior, account deletion, privacy policy, and App Privacy answers reconcile |
| Submission | Exact metadata, demo, screenshot, icon, reviewer notes, and access credentials are verified before upload |
| Rejection | Read the exact App Review message; do not infer the cause and do not blind-resubmit |
| Experiment | One primary metric, explicit guardrails, start/stop rule, budget, and rollback |
| Scale | Increase acquisition or capacity only after positive reconciled contribution profit and acceptable retention/refunds |

## 10. Metrics and economics

### 10.1 North star

The north star is **35-day contribution profit per product**:

```text
App Store proceeds
− refunds
− attributable paid acquisition
− model/API variable cost
− product-specific infrastructure
− attributable operational cost
= 35-day contribution profit
```

MRR remains a growth metric, not a profit substitute. App count, builds,
submissions, impressions, clicks, and installs are diagnostic inputs.

### 10.2 Funnel and source hierarchy

| Layer | Metrics | Canonical source |
|---|---|---|
| Reach | qualified impressions, store product-page views | publication/store receipts |
| Acquisition | first-time downloads, attributed installs, CAC | App Store Connect plus attribution |
| Activation | completed first value, time to value, crash-free path | product analytics and crash reporting |
| Monetization | paywall views, trial starts, trial-to-paid, download-to-paid | RevenueCat plus product analytics |
| Retention | D1/D7/D35 active, renewal, churn, cohort LTV | product analytics plus RevenueCat |
| Quality | crash-free sessions, support/review issues, refund rate | crash reporting, ASC, RevenueCat |
| Economics | proceeds, refunds, costs, contribution profit | ASC, RevenueCat, cost ledger |

RevenueCat's public benchmarks are context, not internal pass/fail thresholds.
The loop compares each product to its own cohort history and relevant category
only after the metric definition, geography, price, and window are compatible.

### 10.3 Stage gates toward the commercial target

| Stage | Required proof before advancing |
|---|---|
| First paid user | purchase and entitlement work in production; user reaches the promised value |
| `$1k MRR` | retention and refund guardrails hold; contribution profit is non-negative |
| `$10k MRR` | at least one repeatable acquisition channel and reliable cohort economics |
| `$100k MRR` | operational load, support, fraud, review, and attribution remain controlled |
| `$1M MRR` | portfolio allocation outperforms focus on the leading product after all costs |
| `$10M MRR` | multiple durable products or one dominant product have proven unit economics and scalable distribution |

The `$10M MRR` goal is directional. The loop never invents a date or guarantees
that outcome.

### 10.4 Tool-cost policy

The default stack uses open-source tools and existing accounts. No recurring
paid tool becomes a hard dependency unless its measured incremental profit
exceeds its total cost and an open fallback remains documented. "Free" does not
mean zero cost: Apple requires a `$99` annual Developer Program membership for
App Store distribution, and model/API, infrastructure, acquisition, and
operational costs remain explicit ledger entries. Existing credits reduce cost
but never become a permanent architecture assumption.

## 11. Anicca canary

Anicca is the first observation and iteration canary:

1. Reconcile product-level RevenueCat, App Store Connect, product analytics,
   acquisition, refunds, and cost observations.
2. Fetch the exact current App Review message before changing the rejected
   build.
3. Convert each rejection into a `ReviewIssue`, test the smallest repair, and
   resubmit with a receipt.
4. Audit the onboarding rating request against Apple's review-request guidance.
   Removing or relocating it is a best-practice improvement, not a claimed
   rejection fix unless the live review message says so.
5. Identify the measured acquisition, activation, paywall, trial, paid,
   retention, or refund bottleneck.
6. Run one reversible experiment and make a keep/revert decision.

An older local rejection record lists subscription price presentation, an iPad
voice defect, missing account deletion, and missing EULA/privacy links. It does
not prove the cause of the current rejection.

## 12. Shipaton execution plan

| Window | Deliverable | Exit evidence |
|---|---|---|
| July 29–31 | Freeze this design, wire observation contracts, reconcile Anicca truth, collect opportunity evidence | approved design; source receipts; no public release |
| August 1–3 | Rank candidates and select exactly one | signed opportunity decision with all gates |
| August 4–7 | Build the thinnest complete native product and production purchase path | tests, RevenueCat sandbox verification, build receipt |
| August 8 | Builders Weekend: device validation, user observation, demo narrative | tested build and evidence-backed repair list |
| August 9–12 | Finish quality, privacy, accessibility, analytics, store assets, and reviewer notes | preflight passes |
| August 13–15 | Submit and target public release | ASC submission/review/public URL receipts |
| August 16–31 | Recover from rejection if needed; acquire first users; fix activation and purchase blockers | exact review resolutions; first complete cohorts |
| September 1–15 | Run one bounded product experiment and one bounded marketing experiment sequentially | keep/revert decisions; cost and attribution reconciliation |
| September 16–23 | Double down only on the measured winner; capture demo and case-study evidence | stable public build; verified metrics |
| September 24 | Freeze Devpost entry | all eligibility and asset checks pass |
| September 25–30 | Buffer for link, promo, asset, or review failures; submit before deadline | Devpost confirmation receipt |

The schedule freezes feature scope if the app is not in App Review by August
15. Reliability, purchase, privacy, review recovery, and distribution outrank
new features.

## 13. CFO portfolio and sale policy

The global CFO may choose:

| Decision | Condition |
|---|---|
| Double down | Positive reconciled contribution profit, acceptable retention/refunds, and a repeatable constrained acquisition channel |
| Hold | Stable value but insufficient evidence for more spend or engineering |
| Retire | Repeated failed value/retention evidence, no credible repair, and low strategic learning value |
| Sell | Stable transferable revenue, clean original IP, low founder-specific dependency, complete operations and Apple-transfer package, and sale value exceeds expected hold value |

Acquire is the primary general mobile-business marketplace adapter;
TrustMRR and Flippa remain optional adapters. The Exit Agent automates
valuation evidence, diligence, listing drafts, buyer qualification, transfer
readiness, and progress tracking. Apple Account Holder authentication, 2FA,
recipient acceptance, and final legal signatures remain explicit credential
or legal boundaries.

Apple app-transfer eligibility, source ownership, verified revenue,
dependencies, credentials, and operational history must be checked before
listing. The loop never clones a sold app or submits reskins.

## 14. Expected outcomes and falsification

| Scenario | Outcome |
|---|---|
| Best | One new app earns meaningful Shipaton traction, wins a prize category, has positive early contribution economics, and validates the reusable loop |
| Base | One high-quality app is live with first payers and a complete measured iteration; the reusable observation, review, experiment, and release contracts are proven |
| Worst | The app is rejected or gains no traction, but exact failure evidence is captured, no spam/account damage occurs, and the loop produces a reusable bounded postmortem instead of more submissions |

The strongest argument for shipping a direct Life Manager iOS app is speed:
Telegram behavior already exists, so a polished mobile surface could be ready
earlier. It is rejected as the default because speed does not supply unmet
demand, differentiation, or willingness-to-pay evidence.

The strongest argument for shipping the factory is category ambition: it
directly expresses the long-term vision. It is rejected as the entry because
the visible factory category already has credible competitors and the pilot
would have to prove both the tool and its generated product inside one window.

**Most likely way this decision is wrong:** the engine scope consumes the
August release window. The guardrail is absolute: if an engine capability is
not required to choose, ship, measure, or improve the one entry, defer it to
Order 37.

## 15. Implementation slices

These are design slices, not authorization to implement before review.
Slice IDs use the S prefix so they can never be confused with the §16
execution order (T prefix); the former shared P numbering was a defect,
fixed 2026-07-29.

| Slice | Scope | Done evidence |
|---|---|---|
| S0 — Truth and Anicca canary | Product registry, observations, review issues, costs, and one bounded existing-app decision | no missing metric is treated as zero; one exact rejection or funnel decision is reproducible |
| S1 — Opportunity selection | Source receipts, disqualifiers, RICE, unique/native/distribution gates | exactly one new app selected without manual preference override |
| S2 — Builder adapter | Map mobileapp-builder phases into durable jobs and receipts | clean worktree produces a tested native build from an approved spec |
| S3 — Release/review loop | RevenueCat, fastlane/ASC, preflight, review message classification, repair/resubmit | one TestFlight/App Review transition and one simulated message fixture pass; live effects are receipt-backed |
| S4 — Shipaton app | Product-specific build, store assets, privacy, accessibility, purchase, public release | public eligible store URL and complete Devpost asset pack |
| S5 — Measured improvement | Attribution, bottleneck decision, one product and one marketing experiment | keep/revert decisions and contribution-profit snapshot |
| S6 — CFO allocation | Global/business/mission/call envelopes, policy engine, usage settlement, and resource leases | a replayable CFO decision cannot exceed hard caps and reconciles actual token/API/Mac/cash use |
| S7 — Portfolio/exit | Double-down/hold/retire/sell policy and transfer pack | decision replay and diligence package pass |
| S8 — Order 37 port | Import proven contracts into the canonical Life Manager runtime | no duplicate scheduler; local/cloud job contracts and tenant boundaries pass |

## 16. Remaining TODO — execution SSOT

This table is the authoritative implementation order (T prefix; §15 design
slices use S). Dates are JST and align with the Shipaton window
(ship 2026-08-01 → 09-30 23:45 PDT; updates to previously released apps do
not qualify; multiple entries allowed; apps still in review are ineligible).
Reordered 2026-07-29 after the deep code hunt (§5.1): the shipping leg is
repaired by adopting `asc web` + the bundled 2FA script instead of building
new automation, and Mode B (iterate) is proven on Anicca before Mode A
(build-new) ships the Shipaton entry.

| Order | Window (JST) | Status | Work | Done evidence |
|---:|---|---|---|---|
| D0 | done | Complete | Research prior art, choose profit-loop entry, define CFO hierarchy, Product Cell, multi-agent roles, budgets, resource leases, and exit loop | this committed design and cited source set |
| D1 | done | Complete | Deep code hunt; adjudicate adopt/copy/build (§5.1); resolve §15/§16 numbering collision | §5.1 table committed |
| T1 | 07-30–31 | Pending | Repair the shipping leg by adoption: run `asc web auth login` + `get-apple-2fa-code.scpt` once for real; run `asc web privacy apply` and beta-app-localizations in correct order on one dead factory app | the app passes privacy + localization and reaches review submission with zero human 2FA entry |
| T2 | 07-31 | Pending | Push that dead app to public release (pipeline live-fire; deliberately outside the Shipaton window, never a Shipaton entry) | public App Store URL opens |
| T3 | 08-01 | Pending | Fetch Shipaton Official Rules; adjudicate AI-generated and multi-entry clauses; install a rules-watch job | written eligibility verdict + watch job firing |
| T4 | 08-01–05 | Pending | Build read-only Product Registry + Product Cell snapshot and connect first-party observations (ASC, RevenueCat, analytics, crashes, reviews, refunds, model/API cost) — Anicca first | one versioned snapshot with real data; unavailable distinct from zero |
| T5 | 08-03–08 | Pending | Prove Mode B (iterate) on Anicca: bottleneck → one hypothesis → one bounded change → re-release → measure → keep/revert; port ralphex patterns (fresh session per task, completed-plan archival) into ralph.sh | one full iteration receipt chain |
| T6 | 08-05–08 | Pending | Implement SELECT gate + market-evidence adapters (app-store-scraper, TikTok evidence, Mobbin) with the marketing veto: no distribution evidence, no build | three cited candidates ranked; gate rejects at least one |
| T7 | 08-08–20 | Pending | Mode A: ship the gate-winning new app as Shipaton entry #1 (mobileapp-builder → greenlight → RevenueCat IAP → asc → review recovery) | in-window public URL + one live RevenueCat purchase |
| T8 | 08-20–09-24 | Pending | Connect the marketing loop under Mission contracts: tiktok-uploader + MoneyPrinterTurbo posting, ASO (installed skills + scraper), searchads_api, paywall-ab/screenshot-ab; product and marketing experiments settle in the same contribution-profit ledger | one attributed marketing mission reaches keep/revert with settled acquisition cost |
| T9 | slack | Pending | Repeat Mode A for entries #2/#3 if envelope allows | additional in-window public URLs |
| T10 | 09-24–30 | Pending | Demo videos + Devpost submission for all entries | submission confirmation |
| T11 | 10-01+ | Pending | Implement global CFO allocation (Mission/BudgetEnvelope/AgentRunUsage/PolicyDecision/ResourceLease contracts + settlement) | replayable CFO decision cannot exceed hard caps and reconciles actual token/API/Mac/cash use |
| T12 | 10-01+ | Pending | Implement Exit Agent and transfer package | hold/sell decision, Acquire-ready diligence pack, Apple eligibility check, credential/legal handoff checklist pass |
| T13 | 10-01+ | Pending | Thin attribution layer: App Store custom product pages with distinct links, one E2E measurement | "post → install → purchase" chain measured on a real post |
| T14 | 10-01+ | Pending | Port proven contracts into Order 37 (canonical Life Manager runtime; local/cloud split; tenant boundaries) | canonical runtime owns scheduling and ledgers; no duplicate scheduler or truth source remains |

## 17. Sources

| Source | Core evidence |
|---|---|
| [RevenueCat — Announcing Shipaton 2026](https://www.revenuecat.com/blog/company/announcing-shipaton-2026) | “Shipaton 2026 runs for two full months: August 1 through September 30.” |
| [Shipaton Devpost rules status](https://revenuecat-shipaton-2026.devpost.com/rules) | Final Official Rules are not yet published; current submission period starts August 1 00:00 PDT |
| [Shipaton Devpost overview](https://revenuecat-shipaton-2026.devpost.com/) | “Updates to previously released apps won't qualify.” |
| [Shipaton Devpost prizes](https://revenuecat-shipaton-2026.devpost.com/) | Grand Prize is listed as `$100,000` and submission requirements are itemized |
| [Builders Weekend — Shipaton Special Edition](https://luma.com/c32o6i8l?tk=3yMWrF) | August 8 Shibuya event; the current page offers Replit Agent 4 credits |
| [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) | Guideline 4.3: “Don’t create multiple Bundle IDs of the same app.” |
| [Apple Developer Program enrollment](https://developer.apple.com/programs/enroll/) | App Store distribution membership is `$99` per membership year |
| [Apple — Requesting App Store reviews](https://developer.apple.com/documentation/storekit/requesting-app-store-reviews) | Ask for reviews at moments that make sense in the user experience |
| [Apple — Reply to App Review messages](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/reply-to-app-review-messages/) | Review messages can be read and answered in App Store Connect |
| [RevenueCat — State of Subscription Apps 2026, Utilities](https://www.revenuecat.com/state-of-subscription-apps-2026-utilities) | iOS download-to-paid median and renewal/refund comparisons inform, but do not set, internal gates |
| [RevenueCat — App portfolio vs. single app](https://www.revenuecat.com/blog/growth/app-portfolio-vs-single-app) | Portfolio risk diversification trades against focus and technical debt |
| [Intercom — RICE prioritization](https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/) | RICE uses reach, impact, confidence, and effort |
| [Lean Startup — Validated learning](https://lean.st/principles/validated-learning/) | Learning must be demonstrated through real behavior, not output volume |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | “Agents as tools / Handoffs: Delegating to other agents for specific tasks” |
| [OpenAI Financial Research Manager](https://github.com/openai/openai-agents-python/blob/main/examples/financial_research_agent/manager.py) | Deterministic plan, parallel search, specialist tools, evidence verification, one revision, and fail-closed completion |
| [OpenAI Agents SDK context](https://github.com/openai/openai-agents-python/blob/main/docs/context.md) | Local context is not sent to the LLM; usage and serializable run state remain runtime concerns |
| [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py) | The project recommends the “supervisor pattern directly via tools” for most cases |
| [Temporal OpenAI Agents samples](https://github.com/temporalio/samples-python/tree/main/openai_agents) | Temporal workflows provide orchestration/state while Agents SDK provides bounded agent/tool interaction |
| [Temporal Resource Pool](https://github.com/temporalio/samples-python/tree/main/resource_pool) | The sample serializes access to scarce resources across long-lived workflows |
| [Nodenester AppFactory](https://github.com/Nodenester/AppFactory) | Existing prior art for `observe → prioritize → act → learn`, market discovery, build, test, and submit |
| [App Store Scraper](https://github.com/facundoolano/app-store-scraper) | MIT implementation for app search, rankings, details, reviews, ratings, screenshots, and version history |
| [AppReply App Store MCP](https://github.com/appreply-co/mcp-appstore) | Agent tools for app search, keyword competition, app details, review analysis, and pricing |
| [Apple App Reviews Scraper](https://github.com/glennfang/apple-app-reviews-scraper) | MIT review ingestion with delay and backoff for larger evidence sets |
| [Mobbin official MCP](https://github.com/mobbin/mobbin-mcp-server) | Official remote MCP for real-world mobile and web screen/flow references |
| [ASO App Store Screenshots](https://github.com/adamlyttleapps/claude-skill-aso-appstore-screenshots) | Deterministic scaffold plus bounded enhancement for App Store assets |
| [Daisuke134/mobileapp-builder](https://github.com/Daisuke134/mobileapp-builder) | Existing native iOS build-to-submission baseline |
| [bes-dev/etnamute](https://github.com/bes-dev/etnamute) | Open lifecycle for spec, build, improve, fix, test, market, and release |
| [fastlane](https://github.com/fastlane/fastlane) | Open-source mobile build and release automation |
| [AppFlight](https://appflight.dev/) | Direct commercial proof that native AI build/submission/rejection automation is already a product category |
| [Factory App](https://factoryapp.dev/) | Quality-gated app factory prior art centered on single-shot generation |
| [Apple — Initiate an app transfer](https://developer.apple.com/help/app-store-connect/transfer-an-app/initiate-an-app-transfer) | App transfer requires preserving relevant app and business records |
| [Apple — App transfer criteria](https://developer.apple.com/help/app-store-connect/transfer-an-app/app-transfer-criteria) | A transferable app must have at least one released App Store version and meet account, status, and product constraints |
| [Acquire — Mobile apps for sale](https://acquire.com/mobile-apps-for-sale/) | Buyers evaluate rankings, DAU, session length, subscription retention, update history, stack, and dependencies |
| [TrustMRR FAQ](https://trustmrr.com/faq) | RevenueCat/Superwall revenue can be verified for marketplace listings |
| [Flippa — What apps can be sold](https://support.flippa.com/hc/en-us/articles/360000682816) | Original source is required; clones and reskins are not accepted |

## 18. Self-review

| Check | Result |
|---|---|
| Decision | One recommendation: profit loop as the engine, one evidence-selected new consumer app as the Shipaton entry |
| Scope | The pilot proves one vertical mobile loop; the CFO contracts are global, while Web and other Business Managers remain outside this implementation |
| Agent ownership | Durable Product Cells and workflows preserve continuity; no resident LLM is required per app |
| Budget safety | Global, business, mission, and call envelopes plus resource leases prevent free-form overspend and conflicting mutations |
| Apple safety | Originality, quality, privacy, review-request timing, exact rejection reading, and WIP limits are explicit |
| Economics | Contribution profit, retention, refunds, attribution, and variable cost outrank app count and vanity metrics |
| Evidence honesty | Prize totals retain source-specific scopes; pending Official Rules are explicit; no Codex hardware prize is claimed; old Anicca rejection evidence is not presented as current |
| Runtime consistency | The pilot cannot alter schedulers or production ledgers before Order 26; porting occurs through Order 37 |
| TODO consistency | Section 16 is the sole ordered execution list; only design/research is complete |
| Placeholder scan | No unresolved design placeholders; all runtime work is explicitly marked Pending |
