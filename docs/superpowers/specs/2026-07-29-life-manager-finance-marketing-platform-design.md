# Life Manager Finance + Self-Improving Marketing Platform Design

**Status:** Proposed for review  
**Scope owner:** Life Manager  
**First production products:** Anicca iOS and Honne AI  
**Primary outcome:** OpenClaw can be stopped without stopping financial reporting or mobile-app marketing.

## 1. Executive decision

Life Manager becomes the single control plane for personal health and autonomous
income loops. Financial health ships first. The first income loop migrated is a
general mobile-app marketing loop, proven with Anicca iOS and Honne AI.

The selected architecture is cloud-only and multi-tenant:

| Plane | Runtime | Responsibility |
|---|---|---|
| Control plane | Life Manager on Railway | accounts, products, schedules, job leases, ledgers, attribution, experiments, reports, panel, Telegram |
| Worker plane | Horizontally scalable cloud workers | API collection, isolated browser sessions, media rendering, posting, metric collection, learning, report generation |
| Data plane | PostgreSQL | immutable events, materialized financial snapshots, content lineage, metrics, experiments, job state |
| Object plane | S3-compatible storage | generated media, immutable evidence, exports, and signed legacy archives |
| Secrets | encrypted tenant-scoped cloud vault | connector credentials and browser-session material; never stored in prompts, job payloads, logs, or Git |

OpenClaw, Profitable Claude, and repository-specific launchd jobs are migration
sources, not runtime dependencies. They remain intact until parity and cutover
evidence pass. A temporary Mac bridge may mirror legacy effects during
migration, but it is not part of the target system or completion state. No
repository is deleted during the first migration.

## 2. Goal and non-goals

### Goal

`done = true` only when all of the following are true:

1. Stopping `ai.openclaw.gateway` does not interrupt Life Manager reports,
   financial collection, Anicca marketing, or Honne marketing.
2. Runtime code for the migrated paths contains no read, execute, or import
   dependency on `~/.openclaw`, `/Users/anicca/profitable-claude`, or
   `/Users/anicca/anicca`.
3. The Life Manager panel and Telegram show the same reconciled financial
   snapshot, including freshness and unavailable-source states.
4. Every published mobile creative has lineage:
   `product → campaign → experiment → format → hook → artifact → publication
   → platform metrics → install → trial → paid revenue`.
5. A learning promotion changes one bounded rule, passes a canary, is consumed
   by the next generation run, and can be reverted from a durable receipt.
6. Anicca iOS and Honne AI each have independent product packs, goals,
   attribution, metrics, and learned weights.
7. A new user can connect a product and run the same engine without Anicca
   names, paths, accounts, or credentials.
8. Powering off the Mac Mini does not interrupt any production loop; no
   production job requires launchd, a local browser profile, a local keychain,
   or a `/Users/...` path.
9. Worker capacity scales horizontally with tenant demand and enforces
   per-tenant quotas, rate limits, concurrency limits, and fair scheduling.

### Non-goals for the first release

| Deferred item | Reason |
|---|---|
| Autonomous mobile-app creation and App Store submission | Prove growth of existing apps before generalizing the development loop |
| Physical- and mental-health automation | Their report shells are defined now; implementation follows financial health |
| Deleting OpenClaw or legacy repositories | Disable only after shadow, canary, restart, and dependency tests |
| Trading with user funds | Financial health is read-only reporting; execution requires a separate risk and authorization spec |
| Accepting raw Apple IDs or passwords | App Store Connect API keys and delegated authorization are safer and automation-compatible |
| Claiming guaranteed `$10k MRR` | `$10k MRR` is a measurable target with explicit assumptions, not a promise |

## 3. Evidence: current state

### 3.1 Measured runtime state

| System | Measured state | Consequence |
|---|---|---|
| Local OpenClaw gateway | Running as `ai.openclaw.gateway` | OpenClaw is still running |
| OpenClaw scheduler | Store reports 316 jobs; 92 are marked enabled; `nextWakeAtMs` is null and `cron list` returns zero jobs | Configured entries are not evidence of active scheduling |
| macOS launchd | Marketing, writing, finance, gig, Capafy, and other jobs are loaded and producing current logs | launchd is the actual scheduler for the observed loops |
| Profitable Claude marketing engine | Registry, schemas, bounded learning, canary keep/revert, observation terminalizer, and dashboard exist | Reuse these contracts |
| Marketing runtime store | About 20 KB; dashboard and logs only; no run, publication, metric, experiment, or observation ledgers | The production feedback loop is not closed |
| Life Manager Railway | `/health` returns 200 from `life-call-production.up.railway.app` | A functioning cloud control plane already exists |
| Life Manager panel | Timeline, connection, score, gate, API cost, and limited financial-ledger projections exist | Extend; do not build a second dashboard |
| Financial report loop | launchd checks every five minutes, sends daily after 20:00 JST and weekly Sunday after 20:05 JST | Scheduling works locally but is not cloud-owned |
| Financial report scope | x402/TaskMarket/USDC earnings, fees, losses, API costs, payout reserve | Bank, App Store, RevenueCat, Stripe, broader crypto, and business P&L are absent |
| RevenueCat | One project, seven app/store entries; current project overview is `$20 MRR`, five active subscriptions, zero trials | Baseline is tiny and currently not reliably split per product |
| Moneytree connector | One connected Japanese bank account is readable | Bank balance can seed the personal balance sheet; account identifiers must stay private |
| Historical Anicca metrics | 299 seven-day downloads on 2026-05-15; subsequent snapshot showed zero due to ASC collection failure; historical trial start rate about 3.5–3.8% | Data quality must be first-class; zero and unavailable cannot be conflated |

### 3.2 Marketing jobs actually loaded in launchd

The table lists the revenue-relevant daily families, not every unrelated
machine-maintenance job.

| Family | Current cadence | Current boundary | Latest observed condition |
|---|---|---|---|
| Larry Anicca slideshows | Multiple EN/JA accounts, 1–4 posts per account/day | Profitable Claude wrapper; several scripts return to `~/.openclaw` | Active; some library-post jobs exit 3 |
| ReelClaw Anicca videos | Card/widget EN/JA, 1–2 posts per variant/day | Mostly `~/.openclaw/skills/_dispatcher` and ReelClaw scripts | Active; several jobs exit 1 |
| Honne videos | EN at 07:00/11:00/20:30; JA at 08:30/12:30/21:30 | `~/.openclaw` ReelClaw scripts | Active with recent logs |
| Larry strategy learning | 05:10 daily | Reads OpenClaw content metrics and library state | Latest exit 2 |
| Capafy core | 08:10 daily | `/Users/anicca/anicca` | Active |
| Capafy goal/marketing | 09:00, 11:20, 16:00 | `/Users/anicca/anicca` | Active; latest marketing rows show zero engagement |
| Clipping | Every 86,400 seconds | `/Users/anicca/anicca` | Active; latest recorded asset was below quality floor |
| Writer/article | craft train and article resume/daily/learning jobs are loaded; standalone writer daily/learn plists exist but are not currently loaded | Profitable Claude plus local writer CLI | Mixed; loaded jobs include successes and failures |
| Shared marketing metrics | Every 15 minutes | Profitable Claude engine | Runs successfully but has no production ledgers to observe |
| Shared marketing dashboard | Every 15 minutes | Profitable Claude engine | Runs successfully but projects an empty runtime |
| Life Manager financial report | Every five minutes; send gates at 20:00 daily and Sunday 20:05 weekly | Separate `life-manager-main` checkout and `~/.openclaw/.env` | Active; still local and OpenClaw-env-dependent |

The OpenClaw store also contains enabled entries for Larry, ReelClaw, app
reviews, Capafy publishing, CFO sync, and other jobs. Because the scheduler
currently exposes no active jobs and no next wake, these are treated as stale
configuration until a real run receipt proves otherwise.

### 3.3 Evidence and inference are separate

**Evidence:** launchd logs show real posts and executions; the shared marketing
runtime has no ledgers.

**Inference:** repetition is not primarily a prompt-quality problem. The
production generators cannot consume learned weights that were never produced
from attributed observations.

**Evidence:** the existing financial report is based on a wallet ledger and API
cost ledger.

**Inference:** it is an agent-economy P&L report, not yet a personal net-worth
or whole-business financial-health report.

## 4. External constraints and sources

| Source | Core statement | Design consequence |
|---|---|---|
| [Apple Analytics Reports](https://developer.apple.com/documentation/analytics-reports) | “Apple does not generate reports until you create a valid Analytics Report Request.” | Connector setup creates the request once, then polls and downloads all segments; missing requests are an explicit setup state |
| [RevenueCat Webhooks](https://www.revenuecat.com/docs/integrations/webhooks) | “We recommend that apps defer processing until after the response has been sent.” | Webhook endpoint authenticates, stores an inbox row, returns quickly, then processes idempotently in a worker |
| [Railway Cron Jobs](https://docs.railway.com/reference/cron-jobs) | “Services configured as cron jobs are expected to execute a task, and terminate as soon as that task is finished.” | Railway cron only enqueues bounded jobs; long rendering, browser, and learning work runs in leased workers |
| [Telegram Bot API](https://core.telegram.org/bots/api) | “The Bot API is an HTTP-based interface” | Telegram is a delivery surface, not the financial source of truth |
| [Moneytree LINK](https://docs.link.getmoneytree.com/docs) | Moneytree LINK exposes standardized financial data after user authorization and uses OAuth 2.0 Authorization Code Grant with PKCE | Production users connect through Moneytree LINK/OAuth; raw bank credentials never enter Life Manager |

## 5. Alternatives considered

| Approach | Strength | Fatal weakness | Decision |
|---|---|---|---|
| Railway-only monolith | Simple deployment and multi-user SaaS | API, scheduler, browser, rendering, and posting contend for one failure and scaling boundary | Rejected |
| Local-only profitable harness | Reuses current sessions and assets | No reliable 24/7 control plane, weak multi-tenancy, poor commercial onboarding | Rejected |
| Permanent hybrid cloud + customer/local workers | Can reuse local sessions and hardware | A Mac/user device remains a production dependency and cannot serve thousands of tenants reliably | Rejected as final architecture; allowed only as a migration bridge |
| Cloud-native control plane + specialized worker pools | No customer machine dependency; independent scaling and tenant isolation | Requires cloud browser/session migration, a credential vault, and workload-specific workers | Selected |

## 6. Target architecture

```text
Telegram ───────────────┐
Web panel ──────────────┼──> Life Manager API on Railway
Webhooks ───────────────┘          │
                                   ├── PostgreSQL event + finance + growth ledgers
                                   ├── scheduler emits jobs
                                   ├── report projector
                                   └── experiment controller
                                            │
                              lease / heartbeat / receipt
          ┌───────────────────┼────────────────────┬─────────────────────┐
          │                   │                    │                     │
     API workers       Browser workers       Media workers       Effect workers
     source sync       isolated tenant       FFmpeg/Remotion     publish/platform
     webhooks          profiles + 2FA        image/video         reconciliation
          └───────────────────┼────────────────────┴─────────────────────┘
                              │
                  object storage + tenant secret vault
```

Railway hosts the initial control plane and worker services. The contracts are
provider-neutral so a saturated pool can later move to Kubernetes, ECS, or a
specialized browser/render provider without changing product or ledger logic.
There is no local execution mode in the commercial product.

### 6.1 Canonical repository layout

All new canonical code lives in the current Life Manager monorepo:

```text
apps/life-call/
  api/
  panel/
  reports/
  telegram/
  worker/
packages/
  loop-core/
  job-protocol/
  finance-engine/
  marketing-engine/
  connector-contracts/
  product-packs/
    anicca-ios/
    honne-ai/
```

The actual implementation follows existing repository conventions instead of
forcing this exact folder shape where it would create churn. Responsibility
boundaries are mandatory even if paths differ.

### 6.2 Job protocol

Every action is a durable job:

| Field | Meaning |
|---|---|
| `job_id` | globally unique idempotency key |
| `tenant_id` | owner boundary |
| `loop_id` | finance, marketing, writer, gig, or another registered loop |
| `capability` | collect, research, generate, render, publish, observe, learn, report |
| `worker_pool` | api, browser, media, publish, observe, learn, or report |
| `resource_class` | cpu/memory/gpu/browser requirements used for cloud placement |
| `input_refs` | immutable database/blob references, never embedded secrets |
| `lease_owner`, `lease_until` | single-writer worker claim |
| `attempt`, `max_attempts` | bounded retry |
| `effect_class` | read, draft, publish, money |
| `status` | queued, leased, succeeded, failed, dead-lettered |
| `receipt_ref` | immutable evidence of the real effect |

Workers advertise capabilities and heartbeat. The scheduler never knows
whether the implementation is Claude, Codex, Hermes, deterministic code, or a
future OpenClaw adapter.

### 6.3 Multi-tenant execution rules

| Concern | Required behavior |
|---|---|
| Isolation | every job, object, secret, browser profile, artifact, and receipt carries `tenant_id`; authorization fails closed |
| Fairness | tenant queues use weighted fair scheduling; one tenant cannot consume every worker |
| Limits | per-tenant publish, browser, rendering, spend, and connector rate limits |
| Idempotency | scheduler retries may create attempts, never duplicate external effects |
| Browser state | encrypted, tenant-scoped cloud profiles; ephemeral execution containers; no shared cookies |
| Scaling | each worker pool scales independently from queue depth and job age |
| Recovery | leases expire; another eligible cloud worker reconciles before retrying an unknown effect |

### 6.4 Connector contract

Every source implements:

```text
connect() -> authorization state
sync(cursor) -> immutable source events + next cursor
health() -> freshness, last success, actionable error
normalize(events) -> canonical ledger rows
```

Initial connectors:

| Domain | Connectors |
|---|---|
| Cash and net worth | Moneytree LINK, manual balance, exchange/wallet read-only APIs |
| Mobile apps | App Store Connect Analytics/Sales, RevenueCat webhooks and API, Mixpanel |
| Web products | Stripe |
| Autonomous income | uGig, Capafy, clipping affiliate, writer, x402, bounty |
| Distribution | TikTok, Instagram, YouTube, X through OAuth/API where available and isolated cloud-browser adapters where necessary |

An unavailable connector returns `unavailable` with its last successful
snapshot. It never returns a fabricated zero.

## 7. Financial-health model

### 7.1 Canonical statements

| Statement | Contents |
|---|---|
| Personal balance sheet | cash, investments, crypto, receivables, liabilities, net worth |
| Daily cash flow | money in, money out, transfers, fees, realized gains/losses |
| Business P&L | revenue, refunds, platform fees, API/compute/ad costs, contribution profit by business |
| Recurring revenue | MRR, active paid, trials, new MRR, expansion, contraction, churn |
| Liquidity and risk | runway, tax reserve, emergency reserve, concentration, stale sources |

Every amount stores original currency, original amount, FX rate source,
converted amount, and timestamp. Transfers are excluded from income. Unrealized
asset appreciation is separated from earned business income.

### 7.2 Business dimensions

Initial business keys are:

`life_manager`, `anicca_ios`, `honne_ai`, `gig_work`, `capafy`,
`clipping_affiliate`, `writer`, `nisa`, `crypto_yield`,
`crypto_trading`, `x402`, and `bounty`.

The list is data, not code. Users can add products and businesses without a
deployment.

### 7.3 Telegram financial report

Daily report time defaults to 20:00 in the user's timezone, after the existing
financial-report convention. A morning delivery preference can be added per
tenant.

```text
FINANCIAL HEALTH · 2026-07-29

Net worth          ¥X       today +¥Y
Liquid cash        ¥X       30-day runway N months
Income today       ¥X       month ¥Y
Costs today        ¥X       month ¥Y
Operating profit   ¥X       margin Z%

Business           Today    Month    MRR
Life Manager       ...
Anicca iOS         ...
Honne AI           ...
Gig / Capafy       ...
Crypto / x402      ...

Mobile growth
Anicca: installs N · trials N · paid N · MRR $N
Honne:  installs N · trials N · paid N · MRR $N

Data health
Moneytree fresh · RevenueCat fresh · ASC delayed 1d

Action taken
Promoted hook rule H-17 after 72h canary; paused format F-04.
```

Delivery policy:

| Message | Cadence |
|---|---|
| Financial health | Daily |
| Weekly CFO review | Sunday evening |
| Month close | First complete day after month-end data is available |
| Exception | material source failure, unexpected spend, payment failure, abnormal revenue drop |
| Physical health | Separate daily message in a later release |
| Mental health | Separate daily message in a later release |

The daily message stays concise. Details open the authenticated panel.

### 7.4 Telegram UI/UX

Telegram is the daily command surface; the web panel is the detailed system of
record. The bot sends one scheduled digest per health domain plus
exception-only alerts, rather than narrating every background job.

```text
┌──────────────────────────────────────────────┐
│ LIFE MANAGER · FINANCIAL HEALTH              │
│ Wed, Jul 29 · data through 19:58 JST         │
├──────────────────────────────────────────────┤
│ HEALTH SCORE  72 / 100        ▲ 4 today      │
│ Net worth     ¥12,340,000     ▲ ¥31,400      │
│ Cash runway   14.2 months     Healthy        │
│ MRR           $1,240          ▲ $84 MTD      │
├──────────────────────────────────────────────┤
│ TODAY                 MONTH                  │
│ Income   ¥42,100       ¥611,300              │
│ Costs    ¥11,900       ¥203,800              │
│ Profit   ¥30,200       ¥407,500              │
├──────────────────────────────────────────────┤
│ BUSINESSES                                   │
│ Life Manager      ¥18,400  MRR $620          │
│ Anicca iOS         ¥7,900  38 installs       │
│ Honne AI            ¥3,100  21 installs       │
│ Gig / Capafy       ¥10,800                    │
│ Crypto / x402       ¥1,900                    │
├──────────────────────────────────────────────┤
│ NEEDS ATTENTION                              │
│ ⚠ App Store data is 26h old                  │
│ ↓ Honne install→trial fell 18% vs 7d base    │
├──────────────────────────────────────────────┤
│ LIFE MANAGER DID                             │
│ ✓ Published 8 creatives                      │
│ ✓ Kept hook H-17 after 72h canary            │
│ ↩ Reverted format F-04                       │
├──────────────────────────────────────────────┤
│ [Open dashboard] [Explain changes]           │
│ [Mobile apps]   [Fix connection]             │
└──────────────────────────────────────────────┘
```

Conversation flow:

```text
/start
  → Create tenant
  → Connect money sources
  → Add products/businesses
  → Connect App Store + RevenueCat + channels
  → Choose timezone/report times
  → First reconciled snapshot

Scheduled digest
  → scan health and exceptions in under 30 seconds
  → tap a problem or business
  → receive a compact drill-down
  → open the authenticated web panel for ledger/experiment detail

Exception alert
  → state what changed, financial impact, and evidence
  → offer only safe actions: explain, retry sync, pause loop, open panel
  → money movement or expanded public broadcast requires its own authorization
```

Default delivery:

| Time | Message | Interaction |
|---|---|---|
| 08:00 | Physical Health | sleep/activity/recovery summary and one action |
| 20:00 | Financial Health | net worth, income, business P&L, mobile funnel, actions, data health |
| 21:00 | Mental Health | mood/stress/attention summary and reflection |
| Immediate | Material exception only | source failure, payment failure, abnormal revenue/spend, blocked effect |

## 8. Self-improving mobile marketing loop

### 8.1 Loop

```text
Observe market
  → extract viral format DNA
  → generate diverse candidates
  → quality + policy gates
  → publish with lineage
  → collect 2h / 24h / 72h / 7d metrics
  → attribute installs / trials / paid revenue
  → blame one bounded rule
  → challenger canary
  → keep or revert
  → next run proves it consumed the new weight
```

### 8.2 What is shared and what is isolated

| Shared across products | Isolated per product/channel/audience |
|---|---|
| job protocol, ledgers, experiment controller, canary/revert, dashboards, connector interfaces | promise, proof, offer, forbidden claims, hook weights, format library, platform account, locale, attribution, reward |

This prevents an Anicca hook winner from silently changing Honne output.

### 8.3 Format DNA

The engine learns structure, not verbatim creative:

| Slice | Examples |
|---|---|
| Hook | confession, contradiction, threat, curiosity gap, specific outcome |
| Narrative | problem–agitation–proof, before/after, demo, reaction, list |
| Visual grammar | first-frame text density, cuts, slide count, product reveal timing |
| Audio | voice, music energy, silence, sound-effect timing |
| CTA | install, comment, save, trial, direct proof |

Each format records source URL, observed date, public metrics, extracted
structure, allowed reuse, and similarity fingerprints. Copyrighted assets are
not copied into the product.

### 8.4 Variation gates

A candidate fails before rendering when:

1. Its normalized hook equals a hook used by the same account in the recent
   exclusion window.
2. Semantic similarity to a recent hook exceeds the configured product limit.
3. The same format family would exceed its rolling share cap.
4. Product proof, locale, platform, or CTA does not match the product pack.
5. The visual checksum or transcript is effectively a duplicate.

Variation is measured, not requested with a prompt.

### 8.5 Reward hierarchy

| Horizon | Signal | Use |
|---|---|---|
| 2 hours | valid publication, views, first-frame hold | detect delivery or creative failure |
| 24 hours | hold, completion, saves, profile/product clicks | rank hooks and formats |
| 72 hours | attributed installs and activated users | promote acquisition winners |
| 7–35 days | trials, paid users, proceeds, retention | promote revenue winners |

The optimizer uses the deepest available reward. Views cannot override a
measured loss in paid conversion. Missing revenue remains unknown rather than
zero.

### 8.6 Anicca and Honne product packs

| Pack | Required proof |
|---|---|
| Anicca iOS | notification/Nudge experience, actual intervention outcomes, supported problem types, real paywall and price |
| Honne AI | real product demo, language-matched assets, actual transformation, real store/paywall path |

Each pack owns JA and EN audiences separately. Existing Larry and ReelClaw
producers become adapters behind the same artifact/publication contracts.

## 9. `$10k MRR` operating model

Current measured RevenueCat overview is `$20 MRR` and five active
subscriptions across the shared project. Because product-level allocation is
not yet reliable, the plan does not pretend that Anicca or Honne owns a
specific share.

Twelve-month scenarios:

| Scenario | Blended MRR / active subscriber | Install→paid | Monthly churn | Active subscribers needed | New paid/month needed | Installs/month needed |
|---|---:|---:|---:|---:|---:|---:|
| Best | $8.00 | 5.0% | 5% | 1,250 | 136 | 2,714 |
| Base | $6.00 | 3.0% | 8% | 1,667 | 211 | 7,021 |
| Worst | $4.17 | 1.5% | 12% | 2,399 | 367 | 24,449 |

These are target mechanics, not forecasts. The first growth gate is not
“post more”; it is:

1. Restore trustworthy per-product install and revenue collection.
2. Establish one complete attribution chain from publication to paid.
3. Raise the number of genuinely distinct tested hooks per week.
4. Improve the weakest measured funnel step.
5. Scale publishing only after a challenger beats its product-specific
   baseline without retention or revenue regression.

## 10. To-Be Life Manager UI/UX

### 10.1 Navigation

```text
Today
Health
  Financial
  Physical
  Mental
Income Loops
  Portfolio
  Mobile Apps
  Web Apps
  Gig / Affiliate / Capafy / Writer / Crypto / Bounty
Marketing Studio
Reports
Connections
Settings
```

### 10.2 Today

The first screen answers three questions:

1. Am I financially healthier than yesterday?
2. What made or lost money?
3. What did Life Manager do, and what needs attention?

Top cards:

| Card | Content |
|---|---|
| Net worth | current value, day/month delta, freshness |
| Income | today and month-to-date |
| Operating profit | revenue minus attributable costs |
| Recurring revenue | total MRR and target progress |
| Attention | failed connector, anomaly, blocked job, required authorization |

Below the cards: business contribution, mobile growth funnel, recent autonomous
actions, and source-health strip.

### 10.3 Financial Health

Four tabs:

| Tab | Contents |
|---|---|
| Overview | net worth, liquid cash, runway, income, expenses, profit |
| Businesses | P&L and MRR by product/business |
| Assets | bank, NISA, crypto, yield positions, liabilities |
| Ledger | reconciled transactions, classifications, provenance, freshness |

All numbers show source and last sync. Unknown values display “Unavailable”,
never `0`.

### 10.4 Mobile Apps

Portfolio row per app:

`installs → activation → paywall → trial → paid → retained → MRR`

App detail includes acquisition by channel/creative, store conversion,
subscription cohorts, experiment history, content calendar, and the current
bottleneck. Anicca and Honne never share learned weights.

### 10.5 Marketing Studio

| Area | User sees |
|---|---|
| Queue | planned, rendering, scheduled, published, observing |
| Format library | source, format DNA, product fit, recent usage, performance |
| Experiments | control, challenger, reward, horizon, confidence/evidence |
| Learning | changed rule, blame evidence, canary, keep/revert, consumption proof |
| Accounts | platform health, last successful post, rate/quality limits |

The UI exposes receipts, not agent narration. A green state requires a real
publication URL or verified metric row.

### 10.6 Connections

Users connect App Store Connect with an API key, RevenueCat with a project
credential or OAuth when available, social platforms with OAuth/session
adapters, and banking through Moneytree LINK. Raw passwords are not a product
interface. Every connector and loop runs in the Life Manager cloud. Users
authorize accounts in the web app; they do not install a worker or keep a
computer online.

## 11. Failure handling

| Failure | Behavior |
|---|---|
| Source delayed | retain last good value, mark stale, exclude from fresh delta |
| Duplicate webhook | inbox idempotency key returns existing receipt |
| Worker dies | lease expires; bounded retry on an eligible worker |
| Publish result unknown | reconcile platform before retry; never blind repost |
| Metrics unavailable | observation becomes insufficient; no learning change |
| Canary regression | restore prior weight hash and record revert |
| Cross-tenant/product evidence | reject and dead-letter |
| OpenClaw stopped during shadow | new path continues; any dependency failure blocks cutover |

## 12. Ordered delivery plan

The order below is the program source of truth.

| Order | Deliverable | Exit evidence |
|---:|---|---|
| 1 | Freeze and export current scheduler inventory | machine-readable OpenClaw and launchd inventory with owner, cadence, command, state, latest receipt |
| 2 | Define canonical IDs and ledgers | tenant/product/business/campaign/artifact/publication/source-event schemas with migrations and contract tests |
| 3 | Implement leased job protocol | enqueue, claim, heartbeat, retry, dead-letter, receipt, worker-pool routing |
| 4 | Ship financial connector framework | source cursor, freshness, original currency, FX provenance, unavailable-state tests |
| 5 | Migrate current agent-economy financial report | existing x402/TaskMarket/USDC report emitted from Life Manager cloud path |
| 6 | Add Moneytree personal balance sheet | OAuth/connector ingestion, transfer-safe ledger, bank balance in panel and Telegram |
| 7 | Add RevenueCat and App Store Connect | per-product installs, trials, paid, churn, proceeds, data-quality health |
| 8 | Add Stripe and read-only crypto assets | total net worth and business P&L reconcile across sources |
| 9 | Ship Financial Health UI and daily Telegram report | same snapshot hash rendered in panel and Telegram; daily/weekly/monthly receipts |
| 10 | Extract Profitable Claude marketing contracts | registry, schemas, bounded learner, canary, observations moved behind Life Manager packages |
| 11 | Create Anicca and Honne product packs | independent JA/EN packs, attribution, rewards, weights, forbidden claims |
| 12 | Wire run and publication lineage | existing Larry/ReelClaw outputs create real run, artifact, publication receipts |
| 13 | Wire platform metric collectors | 2h/24h/72h/7d metric receipts with unknown-safe terminalization |
| 14 | Close app attribution | publication/campaign IDs join installs, trials, paid, proceeds |
| 15 | Build viral-format intake | source receipts, format DNA, rights metadata, product-fit scoring |
| 16 | Enforce variation gates | duplicate hook, semantic similarity, format share, locale, proof, visual/transcript checks |
| 17 | Activate bounded self-improvement | one-rule blame, challenger, canary, keep/revert, next-run consumption proof |
| 18 | Build specialized cloud worker pools | API, isolated browser, media, publish, observe, learn, and report pools with tenant-scoped secrets |
| 19 | Add multi-tenant fairness and autoscaling | quotas, weighted scheduling, rate limits, queue-depth scaling, noisy-neighbor tests |
| 20 | Migrate browser profiles and media assets | encrypted cloud profiles, 2FA recovery flow, object storage, zero local-path dependency |
| 21 | Shadow legacy schedules | cloud jobs observe and render without duplicate publishing; compare receipts |
| 22 | Canary real publishing | one Anicca account and one Honne account publish through Life Manager cloud |
| 23 | Cut over all Anicca/Honne marketing | disable corresponding legacy launchd/OpenClaw entries only after parity |
| 24 | Mac/OpenClaw-off verification | Mac powered off through seven daily cycles, cloud restart test, no local/OpenClaw runtime references |
| 25 | Archive legacy code | signed manifest and rollback bundle; no deletion until retention window passes |
| 26 | Multi-tenant commercial onboarding | billing, quotas, connector health, cloud session authorization, export/delete controls |
| 27 | Scale and isolation test | synthetic 1,000-tenant workload; fair scheduling, credential isolation, effect idempotency, recovery evidence |
| 28 | Migrate writer, clipping, Capafy, gig, bounty | each becomes a registered cloud loop using the same job/ledger/report contracts |
| 29 | Add physical and mental health reports | separate daily messages and dashboard sections |
| 30 | Design the mobile-app development loop | feedback/metrics-driven app iteration, then generalized creation and release |
| 31 | Generalize web-app development loop | reuse product, finance, marketing, and worker contracts |

## 13. Cutover gates

No legacy job is disabled until:

1. Seven consecutive expected runs have complete receipts.
2. At least one real publication per selected account is reconciled to a
   platform URL.
3. Financial panel and Telegram share a snapshot hash.
4. Cloud worker restart and deployment do not create duplicates.
5. OpenClaw dependency scan is empty for migrated runtime paths.
6. Forced OpenClaw shutdown and a powered-off Mac do not interrupt the migrated path.
7. Rollback restores the prior scheduler state from a signed inventory.

## 14. Security and commercial constraints

| Constraint | Requirement |
|---|---|
| Tenant isolation | every row and job is tenant-scoped; cross-tenant joins fail closed |
| Credentials | encrypted at rest; references only in jobs; redacted in logs and reports |
| Bank access | Moneytree LINK/OAuth; no raw MUFG credentials |
| Apple access | App Store Connect API keys/delegated roles; no stored Apple ID password |
| Financial action | read-only in this spec |
| Publishing | explicit connector authorization and auditable publication receipt |
| Data export/delete | user-controlled export and deletion without deleting financial audit records required by law |
| Claims | no guaranteed income or “automatic $10k MRR” promise |

## 15. Success metrics

| Layer | Metric |
|---|---|
| Reliability | expected jobs with valid receipts; duplicate effects; stale sources |
| Variety | unique hook fingerprints; format concentration; duplicate rejection rate |
| Acquisition | attributed installs per 1,000 impressions and per publication |
| Monetization | install→trial, trial→paid, paid retention, MRR, proceeds |
| Learning | scorable observations, kept challengers, reverted regressions, consumed weight receipts |
| Finance | reconciled net worth coverage, classified income coverage, source freshness |
| Product | users whose measured monthly benefit/revenue exceeds subscription cost |

## 16. Spec self-review

| Check | Result |
|---|---|
| Placeholder scan | No unresolved implementation placeholders |
| Internal consistency | Railway enqueues bounded jobs; specialized cloud workers own long effects; Telegram/panel are projections of PostgreSQL |
| Scope | Program is decomposed; the first implementation cycle ends at Financial Health, followed by the Anicca/Honne marketing cycle |
| Ambiguity | The target has zero local execution; a Mac bridge is migration-only; OpenClaw is disabled only after gates |
| Evidence honesty | Current ASC snapshots are marked inconsistent; current RevenueCat numbers are project-level |
