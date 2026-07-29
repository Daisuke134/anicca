# Life Manager Portable Runtime + Finance + Self-Improving Marketing Platform Design

**Status:** Proposed for review  
**Scope owner:** Life Manager  
**First production products:** Anicca iOS and Honne AI  
**Primary outcome:** every retained loop runs from Life Manager with zero
OpenClaw dependency, first locally and then from the same runtime in the cloud.

## 1. Executive decision

Life Manager becomes the single control plane for personal health and autonomous
income loops. Financial health ships first. The first income loop migrated is a
general mobile-app marketing loop, proven with Anicca iOS and Honne AI.

The selected architecture is portable local/cloud with cloud as the default
hosted mode:

| Plane | Runtime | Responsibility |
|---|---|---|
| Portable application | The same Life Manager services and OCI images | accounts, products, schedules, jobs, ledgers, attribution, experiments, reports, panel, Telegram |
| Local deployment | Docker Compose plus `life-manager` CLI | private/self-hosted operation on Mac/Linux without any OpenClaw process or folder |
| Cloud deployment | Railway initially; provider-neutral worker pools | always-on multi-tenant operation, horizontal scaling, failover, phone-first use |
| Data plane | PostgreSQL in both modes | immutable events, financial snapshots, content lineage, metrics, experiments, job state |
| Object plane | local object adapter or S3-compatible storage | media, evidence, exports, signed migration archives |
| Secrets | OS keychain/encrypted local vault or tenant-scoped cloud vault | credentials and browser sessions; never stored in prompts, job payloads, logs, or Git |

The migration order is mandatory:

```text
OpenClaw-dependent local
  → Life Manager-owned local
  → portable local/cloud parity
  → cloud-default production
```

OpenClaw, Profitable Claude, and repository-specific launchd jobs are migration
sources only. Every retained script, asset, prompt, schedule, state file, and
credential reference moves behind Life Manager-owned contracts and paths
before cloud migration begins. Legacy repositories remain intact until parity
and rollback evidence pass.

## 2. Goal and non-goals

### Goal

`done = true` only when all of the following are true:

1. Every OpenClaw cron entry and relevant launchd job is classified as
   `migrate`, `replace`, or `retire`; no enabled or loaded job is unowned.
2. Stopping `ai.openclaw.gateway` and denying access to `~/.openclaw` does not
   interrupt any retained Life Manager loop.
3. Runtime code, config, schedules, secrets, assets, and state contain no read,
   execute, import, or fallback dependency on `~/.openclaw`,
   `/Users/anicca/profitable-claude`, or `/Users/anicca/anicca`.
4. `life-manager runtime up --mode local` runs all retained loops locally from
   Life Manager-owned code and data.
5. The same versioned services run with `--mode cloud`; moving a tenant between
   modes changes deployment adapters, not loop behavior or business logic.
6. The Life Manager panel and Telegram show the same reconciled financial
   snapshot, including freshness and unavailable-source states.
7. Every published mobile creative has lineage:
   `product → campaign → experiment → format → hook → artifact → publication
   → platform metrics → install → trial → paid revenue`.
8. A learning promotion changes one bounded rule, passes a canary, is consumed
   by the next generation run, and can be reverted from a durable receipt.
9. Anicca iOS and Honne AI each have independent product packs, goals,
   attribution, metrics, and learned weights.
10. A new user can connect a product and run the same engine without Anicca
   names, paths, accounts, or credentials.
11. In cloud mode, powering off the Mac Mini does not interrupt any production
   loop; Codex on the Mac is an optional command client, not an executor.
12. Cloud worker capacity scales horizontally with tenant demand and enforces
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
| Local-only Life Manager | Maximum privacy and simplest first migration | Lights-out, earthquakes, and machine failure stop production; cannot host thousands of tenants | Supported deployment, not the default |
| Cloud-only Life Manager | Always on and commercially scalable | Blocks the required safe migration path and excludes privacy/self-hosting users | Rejected as the only mode |
| Permanent split runtime where cloud requires a local worker | Reuses local browser sessions | Cloud uptime still depends on the user's machine | Rejected |
| One portable runtime with local and cloud deployment adapters | Removes OpenClaw first, preserves self-hosting, then adds always-on scale without rewriting loop logic | Requires strict adapter contracts and parity tests | Selected |

## 6. Target architecture

```text
                         COMMAND + REPORT SURFACES
       ┌───────────────┬──────────────────┬────────────────────┐
       │ Telegram bot  │ Web/PWA panel    │ CLI / Codex client │
       └───────┬───────┴─────────┬────────┴──────────┬─────────┘
               └─────────────────┼───────────────────┘
                                 ▼
                    LIFE MANAGER PORTABLE CORE
       ┌───────────────────────────────────────────────────────┐
       │ API/auth · tenant/product registry · policy engine   │
       │ scheduler · leased jobs · receipts · event ledgers   │
       │ finance projector · experiment/learning controller   │
       │ connector + loop + storage + secret interfaces       │
       └───────────────┬───────────────────────┬───────────────┘
                       │ same contracts/images │
          ┌────────────▼────────────┐  ┌──────▼────────────────────────┐
          │ LOCAL DEPLOYMENT        │  │ CLOUD DEPLOYMENT             │
          │ Docker Compose          │  │ Railway control plane        │
          │ local API/panel         │  │ managed PostgreSQL           │
          │ PostgreSQL              │  │ S3-compatible object store   │
          │ local object adapter    │  │ tenant cloud secret vault    │
          │ OS keychain/vault       │  │ autoscaled worker pools      │
          │ local worker pools      │  │ multi-tenant fair queue      │
          └────────────┬────────────┘  └──────┬────────────────────────┘
                       └──────────────┬────────┘
                                      ▼
       ┌───────────────────────────────────────────────────────┐
       │ API │ browser │ media │ publish │ observe │ learn    │
       │ finance │ mobile marketing │ writer │ gig │ Capafy   │
       └──────────────────────────┬────────────────────────────┘
                                  ▼
       App Store · RevenueCat · Moneytree · Stripe · social platforms
                                  │
                                  ▼
                    receipts → metrics → decisions
```

Local and cloud are deployment profiles, not separate products. Local mode is
fully functional and OpenClaw-free. Cloud mode uses the same versioned
application packages and adds managed availability, tenant isolation, and
horizontal worker scaling. Codex running on the Mac may submit commands through
the authenticated API or CLI, but scheduled production work does not depend on
that Codex session or the Mac when the tenant uses cloud mode.

### 6.1 Canonical repository layout

All new canonical code lives in the current Life Manager monorepo:

```text
apps/life-call/
  api/
  panel/
  reports/
  telegram/
  worker/
  cli/
packages/
  loop-core/
  job-protocol/
  runtime-adapters/
  finance-engine/
  marketing-engine/
  connector-contracts/
  product-packs/
    anicca-ios/
    honne-ai/
deploy/
  local/
    compose.yaml
  railway/
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
| `resource_class` | cpu/memory/gpu/browser requirements used for placement |
| `deployment_id` | local or cloud runtime that owns the lease |
| `input_refs` | immutable database/blob references, never embedded secrets |
| `lease_owner`, `lease_until` | single-writer worker claim |
| `attempt`, `max_attempts` | bounded retry |
| `effect_class` | read, draft, publish, money |
| `status` | queued, leased, succeeded, failed, dead-lettered |
| `receipt_ref` | immutable evidence of the real effect |

Workers advertise capabilities and heartbeat. The scheduler never knows
whether a worker is local or cloud, nor whether the implementation is Claude,
Codex, Hermes, or deterministic code. OpenClaw is not an adapter or fallback.

### 6.3 Runtime adapter contract

| Interface | Local implementation | Cloud implementation |
|---|---|---|
| Database | Docker PostgreSQL | managed PostgreSQL |
| Queue/leases | PostgreSQL claims | the same PostgreSQL claim protocol |
| Objects | local filesystem adapter or MinIO | S3-compatible object storage |
| Secrets | OS keychain or encrypted local vault | tenant-scoped cloud vault |
| Browser profile | encrypted local profile | encrypted tenant-scoped cloud profile |
| Scheduler | Life Manager scheduler service | the same scheduler service |
| Workers | local service containers | autoscaled service containers |
| Observability | local logs/receipts in panel | centralized logs/receipts in panel |

Business logic may depend only on these interfaces. It may not branch on
OpenClaw paths, machine usernames, or repository locations. Migration tests
run with `~/.openclaw` inaccessible.

### 6.4 Multi-tenant execution rules

| Concern | Required behavior |
|---|---|
| Isolation | every job, object, secret, browser profile, artifact, and receipt carries `tenant_id`; authorization fails closed |
| Fairness | tenant queues use weighted fair scheduling; one tenant cannot consume every worker |
| Limits | per-tenant publish, browser, rendering, spend, and connector rate limits |
| Idempotency | scheduler retries may create attempts, never duplicate external effects |
| Browser state | encrypted, tenant-scoped cloud profiles; ephemeral execution containers; no shared cookies |
| Scaling | each worker pool scales independently from queue depth and job age |
| Recovery | leases expire; another eligible worker in the same deployment reconciles before retrying an unknown effect |

Local mode keeps the same `tenant_id` boundary even for a single user. This
prevents local-only shortcuts from breaking later cloud migration.

### 6.5 Connector contract

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
                         TELEGRAM TO-BE

 /start
   │
   ├─ identity + tenant
   ├─ choose Local or Cloud
   ├─ connect Finance / Health / Products
   ├─ choose timezone + report times
   └─ first source-health check
             │
             ▼
 ┌──────────────────────────────────────────────────────────┐
 │ LIFE MANAGER · TODAY                                     │
 ├──────────────────────────────────────────────────────────┤
 │ Financial   72 ▲4   ¥30,200 profit today                 │
 │ Physical    64 ▼3   sleep is the limiting factor         │
 │ Mental      78 ▲6   focus recovered                      │
 │ Income      59 ▲2   2 loops growing · 1 blocked          │
 ├──────────────────────────────────────────────────────────┤
 │ Next report: Financial Health at 20:00 JST               │
 │ Runtime: Cloud · healthy · Mac not required              │
 ├──────────────────────────────────────────────────────────┤
 │ [Financial] [Physical] [Mental]                          │
 │ [Income loops] [What changed?] [Open web panel]          │
 └──────────────────────────────────────────────────────────┘
             │
             ├─ scheduled separate reports
             ├─ user-requested drill-down
             └─ material exception alert
```

Report ownership is tenant-scoped:

| Recipient | Receives |
|---|---|
| Personal user | only their financial, physical, mental, products, loops, actions, and connector health |
| Business/product operator | their product funnel, revenue, publishing, experiments, and blocked actions |
| Life Manager platform owner/admin | aggregate SaaS MRR, active tenants, infrastructure cost, job reliability, and anonymized system health; never another tenant's raw ledger or health data |

The daily set is:

| Report | Core fields |
|---|---|
| Financial Health | net worth, cash, runway, income, costs, profit, MRR, source freshness, material deltas |
| Physical Health | sleep duration/quality, HR/HRV when available, steps/activity, recovery trend, one highest-leverage action |
| Mental Health | mood, stress, focus, screen time, habits/reflections, risk trend, one bounded intervention |
| Income & Growth | revenue and funnel by business; jobs attempted/won; posts, reach, installs, trials, paid, retention; best/worst experiment; rule kept/reverted |
| Runtime Health | local/cloud mode, last successful cycle, failed connectors, blocked jobs, stale data, required authorization |

Financial Health example:

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

Income & Growth example:

```text
┌──────────────────────────────────────────────┐
│ LIFE MANAGER · INCOME & GROWTH               │
│ Today · compared with 7-day baseline         │
├──────────────────────────────────────────────┤
│ TOTAL        ¥30,200 profit    MRR $1,240    │
├──────────────────────────────────────────────┤
│ MOBILE APPS                                  │
│ Anicca   8 posts · 38 installs · 2 trials    │
│           1 paid · $620 MRR · CPA ¥—         │
│ Honne    6 posts · 21 installs · 1 trial     │
│           0 paid · $180 MRR                   │
│ Best: H-17 confession hook · +42% installs   │
│ Next: test a distinct demo-first challenger  │
├──────────────────────────────────────────────┤
│ OTHER LOOPS                                  │
│ Gig       12 applied · 2 replies · 1 won     │
│ Capafy     4 published · ¥8,400 attributed   │
│ Writer     1 published · ¥0 confirmed        │
│ Crypto     ¥1,900 realized · risk within cap │
├──────────────────────────────────────────────┤
│ AUTONOMOUS CHANGES                           │
│ ✓ kept H-17 after 72h revenue canary         │
│ ↩ reverted F-04 after trial conversion drop  │
│ ⚠ Instagram session needs authorization      │
├──────────────────────────────────────────────┤
│ [Apps] [Experiments] [Loops] [Fix account]   │
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
| 20:10 | Income & Growth | product funnels, loop earnings, experiments, autonomous changes |
| 21:00 | Mental Health | mood/stress/attention summary and reflection |
| Immediate | Material exception only | source failure, payment failure, abnormal revenue/spend, blocked effect |
| Sunday 20:30 | Weekly CEO/CFO review | week-over-week financial, product, loop, health, and priority review |
| Month close | Monthly statement | net-worth change, P&L by business, MRR bridge, costs, taxes/reserves, retained learnings |

Users can disable or reschedule any non-critical digest. Immediate messages are
limited to material exceptions and authorization requests; successful
background jobs appear in the next digest rather than generating notification
spam.

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
┌──────────────────────┬───────────────────────────────────────────────┐
│ LIFE MANAGER         │ TODAY                                         │
│                      │                                               │
│ ● Today              │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│ Health               │ │Finance │ │Physical│ │Mental  │ │Income  │ │
│   Financial          │ │72 ▲4   │ │64 ▼3   │ │78 ▲6  │ │59 ▲2  │ │
│   Physical           │ └────────┘ └────────┘ └────────┘ └────────┘ │
│   Mental             │                                               │
│ Income Loops         │ Net worth / runway / profit / MRR             │
│   Portfolio          │ Business contribution and mobile funnel       │
│   Mobile Apps        │                                               │
│   Web Apps           │ ┌───────────────────────────────────────────┐ │
│   Gig/Affiliate      │ │ Attention                                 │ │
│   Capafy/Writer      │ │ ASC stale · IG authorization · 1 blocked │ │
│   Crypto/Bounty      │ └───────────────────────────────────────────┘ │
│ Marketing Studio     │                                               │
│ Reports              │ Recent actions · receipts · source health     │
│ Connections          │                                               │
│ Settings             │ Runtime: Cloud  [Switch/export to Local]      │
└──────────────────────┴───────────────────────────────────────────────┘
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

### 10.6 Connections and deployment

Users connect App Store Connect with an API key, RevenueCat with a project
credential or OAuth when available, social platforms with OAuth/session
adapters, and banking through Moneytree LINK. Raw passwords are not a product
interface.

| Mode | User experience | Availability |
|---|---|---|
| Cloud, recommended | sign in from phone/web, authorize connectors, Life Manager remains online without a personal computer | managed multi-tenant services and autoscaled workers |
| Local/self-hosted | install Life Manager, run one command, use localhost/PWA and optional Telegram | runs only while that machine is online |
| Local→Cloud migration | export an encrypted tenant bundle, import it to cloud, reconcile cursors and receipts, then switch scheduler ownership | no loop runs from both schedulers during cutover |

The panel shows the active deployment, scheduler owner, last successful cycle,
and whether turning off the current machine would stop work. Mac Codex commands
use `life-manager` CLI or the authenticated API in either mode.

## 11. Failure handling

| Failure | Behavior |
|---|---|
| Source delayed | retain last good value, mark stale, exclude from fresh delta |
| Duplicate webhook | inbox idempotency key returns existing receipt |
| Local worker or cloud worker dies | lease expires; bounded retry on an eligible worker in the same deployment |
| Publish result unknown | reconcile platform before retry; never blind repost |
| Metrics unavailable | observation becomes insufficient; no learning change |
| Canary regression | restore prior weight hash and record revert |
| Cross-tenant/product evidence | reject and dead-letter |
| OpenClaw stopped during shadow | new path continues; any dependency failure blocks cutover |
| Local→cloud transfer interrupted | scheduler ownership remains with the source until import reconciliation succeeds |
| Internet/power loss in local mode | show offline/stale state; resume idempotently when available; do not claim always-on execution |
| Mac unavailable in cloud mode | no effect; API, workers, schedules, and reports continue in cloud |

## 12. Ordered delivery plan

The order below is the program source of truth. Milestone A is a hard gate:
cloud migration work does not begin until every retained loop is demonstrably
OpenClaw-independent and running under Life Manager locally.

| Order | Deliverable | Exit evidence |
|---:|---|---|
| 1 | Freeze all scheduler/runtime inventory | machine-readable inventory covers all 316 OpenClaw store rows, every enabled row, relevant launchd labels, command, cadence, environment source, latest receipt |
| 2 | Decide every legacy job | each row is marked `migrate`, `replace`, or `retire` with Life Manager owner and rollback action; no unowned enabled/loaded job |
| 3 | Define portable domain contracts | tenant/product/business/loop/job/artifact/publication/source-event/receipt schemas and adapter interfaces pass contract tests |
| 4 | Create Life Manager local deployment | one command starts API, panel, scheduler, PostgreSQL, object adapter, and workers without OpenClaw |
| 5 | Establish Life Manager-owned paths | code, prompts, media templates, state, logs, and config live in the monorepo or configured Life Manager data root; dependency scan rejects legacy absolute paths |
| 6 | Move secrets out of OpenClaw | every retained connector reads OS keychain/encrypted Life Manager vault references; `~/.openclaw/.env` is inaccessible in tests |
| 7 | Implement durable local scheduler and job protocol | enqueue, claim, heartbeat, retry, dead-letter, idempotency, effect reconciliation, and receipts pass restart tests |
| 8 | Extract reusable Profitable Claude contracts | registry, schemas, learner, canary, terminalizer, and dashboard logic run from Life Manager packages |
| 9 | Migrate Telegram command/report delivery | Life Manager owns bot routing, tenant mapping, digest schedules, buttons, receipts, and anti-spam policy |
| 10 | Migrate existing financial-report loop | current x402/TaskMarket/USDC daily and weekly outputs run locally from Life Manager with matching snapshot hashes |
| 11 | Migrate Larry/ReelClaw Anicca and Honne | all retained slideshow/video generation, rendering, posting, schedules, assets, and sessions run through Life Manager jobs |
| 12 | Migrate Capafy, clipping, writer, gig, bounty, and other income loops | every retained income job produces a Life Manager receipt and no legacy-path read |
| 13 | Migrate retained personal, school, comedy, SEO, mail, memory, and maintenance jobs | all remaining retained enabled/loaded workflows are Life Manager loops or explicitly retired |
| 14 | Switch local scheduler ownership | launchd, if retained only as a boot trigger, starts Life Manager; no launchd command invokes OpenClaw or legacy repositories |
| 15 | Prove Milestone A: OpenClaw-free local | stop gateway, deny/rename `~/.openclaw`, run seven expected cycles, reconcile real effects, scan zero runtime references, preserve signed rollback inventory |
| 16 | Archive legacy sources | create signed read-only archive and retention policy; no production fallback to archived code |
| 17 | Add financial connector framework | cursors, freshness, original currency, FX provenance, transfer handling, and explicit unavailable states |
| 18 | Add Moneytree, RevenueCat, and App Store Connect | bank balance plus per-product installs, trials, paid, churn, proceeds, and connector health |
| 19 | Add Stripe and read-only crypto/investment assets | net worth and business P&L reconcile across supported sources |
| 20 | Ship Financial Health UI and Telegram | panel and Telegram render the same snapshot hash with daily, weekly, monthly, and exception receipts |
| 21 | Create Anicca and Honne product packs | independent JA/EN offers, attribution, rewards, weights, accounts, and forbidden claims |
| 22 | Complete publication lineage | every Larry/ReelClaw artifact joins product, campaign, experiment, publication URL, and real effect receipt |
| 23 | Add metric collectors and app attribution | 2h/24h/72h/7d platform metrics join installs, trials, paid users, proceeds, and retention without converting unavailable to zero |
| 24 | Build viral-format intake and variation gates | source/right receipts, format DNA, duplicate hooks, semantic similarity, format concentration, proof, locale, and visual/transcript gates |
| 25 | Activate bounded self-improvement | one-rule blame, challenger, canary, keep/revert, and next-run consumption proof work for Anicca and Honne separately |
| 26 | Package supported local/self-hosted mode | versioned installer/Compose bundle, upgrade, backup/restore, health check, and local documentation pass on a clean machine |
| 27 | Implement cloud deployment adapters | managed PostgreSQL, object storage, tenant vault, isolated browser profiles, and provider-neutral worker placement pass the same contracts |
| 28 | Deploy cloud control plane and worker pools | Railway API/panel/scheduler plus API/browser/media/publish/observe/learn/report workers operate from the same release version |
| 29 | Add multi-tenant isolation, fairness, and autoscaling | row/secret/profile isolation, quotas, rate limits, weighted scheduling, queue-depth scaling, and noisy-neighbor tests pass |
| 30 | Implement local→cloud tenant migration | encrypted export/import preserves IDs, cursors, artifacts, receipts, settings, and secrets; exactly one scheduler owns each loop |
| 31 | Shadow cloud against local | cloud replays read-only/duplicate-safe work and matches local artifacts, metrics, reports, and decision hashes |
| 32 | Canary and cut over Dais to cloud | real Anicca/Honne posts and finance reports run in cloud; local scheduler is stopped after reconciled parity |
| 33 | Prove cloud-default availability | Mac Mini powered off through seven expected cycles; reports, posts, metrics, learning, and alerts continue without duplicates |
| 34 | Ship commercial onboarding and billing | phone/web signup, cloud connector authorization, plans, quotas, source health, export/delete, and self-host option |
| 35 | Prove 1,000-tenant scale and recovery | synthetic workload demonstrates fair scheduling, credential isolation, idempotent effects, worker loss recovery, and bounded queue age |
| 36 | Add Physical and Mental Health | separate daily messages, dashboard sections, source freshness, risk policy, and one-action interventions |
| 37 | Design and build mobile-app development loop | metrics and feedback drive bounded app iteration before generalized creation/release |
| 38 | Generalize web-app development loop | reuse portable runtime, product, finance, marketing, experiment, and deployment contracts |

## 13. Cutover gates

No legacy job is disabled until its replacement passes:

1. Seven consecutive expected runs have complete receipts.
2. At least one real publication per selected account is reconciled to a
   platform URL.
3. Financial panel and Telegram share a snapshot hash.
4. Local worker restart does not create duplicate effects.
5. OpenClaw dependency scan is empty for migrated runtime paths.
6. Forced OpenClaw shutdown plus denied access to `~/.openclaw` does not
   interrupt local Life Manager.
7. Rollback restores the prior scheduler state from a signed inventory.

Cloud becomes Dais's scheduler owner only after:

1. The same release passes local and cloud contract tests.
2. Local and cloud shadow outputs reconcile.
3. One scheduler-owner lease prevents double execution during transfer.
4. Real posting and Telegram delivery succeed from cloud.
5. A powered-off Mac does not interrupt seven expected cloud cycles.

## 14. Security and commercial constraints

| Constraint | Requirement |
|---|---|
| Tenant isolation | every row and job is tenant-scoped; cross-tenant joins fail closed |
| Credentials | encrypted at rest; references only in jobs; redacted in logs and reports |
| Local secrets | OS keychain or encrypted Life Manager vault; never `.env` files inherited from OpenClaw |
| Cloud secrets | tenant-scoped vault with audited access and rotation |
| Bank access | Moneytree LINK/OAuth; no raw MUFG credentials |
| Apple access | App Store Connect API keys/delegated roles; no stored Apple ID password |
| Financial action | read-only in this spec |
| Publishing | explicit connector authorization and auditable publication receipt |
| Data export/delete | user-controlled export and deletion without deleting financial audit records required by law |
| Claims | no guaranteed income or “automatic $10k MRR” promise |

## 15. Success metrics

| Layer | Metric |
|---|---|
| Independence | retained loops with zero OpenClaw/legacy-path references; unowned scheduler entries |
| Portability | contract suite passing unchanged in local and cloud modes; tenant export/import reconciliation |
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
| Internal consistency | One portable core and job protocol run in local and cloud deployments; Telegram/panel are projections of the same PostgreSQL-ledger contracts |
| Scope | Program is decomposed into OpenClaw independence, financial/growth closure, cloud deployment, SaaS scale, and later health/development loops |
| Ambiguity | Local is a supported full deployment; cloud is Dais's eventual default; cloud never requires a local worker; OpenClaw is neither adapter nor fallback |
| Evidence honesty | Current ASC snapshots are marked inconsistent; current RevenueCat numbers are project-level |
