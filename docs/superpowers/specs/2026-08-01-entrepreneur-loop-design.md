# Entrepreneur Loop — design spec (2026-08-01, updated 2026-08-02)

STATUS: ACTIVE. This spec is the SSOT for the entrepreneur loop.
Supersedes nothing; it IMPLEMENTS the unimplemented half of
`2026-06-20-anicca-earn-roadmap.md` (that spec's §4 PHASE-1 REFRAME line
"PHASE 1 verification is ANICCA's OWN job … no human in loop", and
`ceo/allocator.py:162,214` "task #13's future spawner").
Where the roadmap and this file disagree about HOW a new earner comes into
existence, THIS FILE WINS. The roadmap keeps owning WHAT the money rails are
(yield / trade / swap / x402 / token) and the spawn-a-whole-instance path.

---

## 1. Goal

Remove the human from the intake side of earning.

Today: Dais reads X, screenshots a way to make money, tells Claude, Claude
writes a loop. The human is the discovery organ and therefore the ceiling.

Target: a loop that (a) finds ways to make money by itself, (b) writes and
deploys new earn loops by itself, (c) kills the losers by revenue, and
(d) gets BETTER at (a)-(c) over time instead of staying static.

`done` (the only definition — nothing is "finished" before this is true):

> 14 consecutive days, zero routine human input inside a pre-authorized mandate,
> during which the entrepreneur loop
> ran intake → build → probation → kill on its own, produced **≥1
> self-discovered venture with finalized external revenue > 0 and realized net
> > 0 after every attributable cost**, wrote **≥30 lifecycle events** to
> `archive/runs.jsonl` (successes AND failures), and appended **≥10 lines**
> to `PLAYBOOK.md`, with a daily P&L delivered to Telegram every day.

"Zero routine human input" means Dais does not scroll X, submit ideas, choose
ventures, restart jobs, judge normal failures, or approve actions already
covered by the mandate. Account/KYC creation, a new public identity, a new
financial venue, leverage, token issuance, legal commitments, or a budget/cap
increase remain explicit approvals. An approval-waiting venture does not block
the rest of the portfolio. The 14-day proof starts after the mandate is fixed;
any manual repair, new approval, cap change or restart resets that proof clock.

Non-goals for this spec: spawning whole Anicca instances (`self/spawn`,
roadmap 3a), the GitHub-Issue social layer (3d), inter-Anicca funding (3e).
Those sit ON TOP of a working entrepreneur loop and are tracked in the roadmap.

## 2. Where it lives

| thing | path |
|---|---|
| loop | `~/anicca/skills/self/entrepreneur/` |
| builder staging | `~/anicca/skills/self/entrepreneur/staging/ev-<venture>/` |
| learning: executable skill library | `~/anicca/skills/earn/ev-<venture>/` |
| learning: attempt archive | `~/anicca/skills/self/entrepreneur/archive/runs.jsonl` |
| learning: playbook | `~/anicca/skills/self/entrepreneur/PLAYBOOK.md` |
| registry (roster SSOT) | `~/.anicca-founder/state/loop-registry.json` |
| founder money SSOT used by this loop | `~/.anicca-founder/state/earn-ledger.jsonl` (sole writer stays `record-earn.mjs`, INV-H2) |
| host | existing `ai.anicca.founder-loop-cadence` (30 min) calls it; no new daemon |

`~/anicca/skills/earn/state/earn-ledger.jsonl` remains the separate general
earn-engine ledger. EL-1 must not silently join these two files. It extends the
founder ledger used by this spec and gives every derived report an explicit
ledger path and freshness timestamp.

## 2.5 Host execution law — decided 2026-08-02

Two cron systems coexist on this Mac. They are not interchangeable. The live
OpenClaw cron store is currently dark/inconsistent: CLI views report 0 enabled
jobs while other views/disk counts disagree and `nextWakeAtMs` is null. The
entrepreneur therefore has exactly one scheduler.

### Layer 1 — scheduler: launchd only

- Existing `ai.anicca.founder-loop-cadence` wakes every 1800 seconds and calls
  `skills/self/founder-loop/founder-loop.sh`.
- That script calls `skills/self/entrepreneur/run.sh` once per wake.
- Every entrepreneur-created venture plist is named
  `~/Library/LaunchAgents/ai.anicca.ev-<venture>.plist`.
- The `ev-` prefix is mandatory: it makes the generated fleet enumerable and
  killable without mixing it with human-authored loops.
- Entrepreneur code never creates or depends on an OpenClaw cron job. Repairing
  the dark OpenClaw store is EL-14, separate and non-blocking.

### Layer 2 — executor: three tiers, T0 by default

| tier | meaning | allowed use |
|---|---|---|
| T0 | deterministic script, no LLM | intake fetch, ledger aggregation, gates, health, launchctl unload, reporting |
| T1 | one-shot LLM through `$LLM_CLI` | candidate scoring, venture generation, playbook reflection; at most 3 calls per entrepreneur cycle |
| T2 | KeepAlive daemon | forbidden for entrepreneur-created ventures; existing daemons only |

`LLM_CLI` is the only model-provider seam: e.g. `claude -p` or `codex exec`.
Changing provider must not change the loop code or scheduler topology.

### Layer 3 — storage: git is inheritance; runtime state is outside git

- Code and learned policy: `~/anicca/skills/self/entrepreneur/` (including
  staging and graveyard), generated `skills/earn/ev-*/`, `PLAYBOOK.md`, and
  `archive/runs.jsonl` are git-tracked.
- Money and live state: `~/.anicca-founder/state/` is not git-tracked.
- Logs: `~/.openclaw/logs/` is only a log sink. The entrepreneur never writes
  `~/.openclaw/cron/` or any other OpenClaw state.

Write boundary: the entrepreneur may write only its own directory,
`skills/earn/ev-*/`, `LaunchAgents/ai.anicca.ev-*.plist`, and schema-owned
entrepreneur files under `~/.anicca-founder/state/`. It never edits human-authored earners,
product repos, existing non-`ev-` plists, or OpenClaw state. Every generated
venture promoted out of staging is committed and pushed to the mother repo so
children inherit it through roadmap 3c.

## 3. Prior art we adapt — semantic differences are mandatory

| part | source | what we take |
|---|---|---|
| evolutionary selection | [jennyzzt/dgm](https://github.com/jennyzzt/dgm) `DGM_outer.py` | adapt its normalized score/child-count sampling idea only. Its `filter_compiled` means completed evaluation + non-empty patch, not a real-world side effect; `keep_better` compares against the initial score, not the direct parent. |
| curriculum | same | the sigmoid × child-count formula is permitted only after local fitness is explicitly normalized to [0,1]; otherwise use a cost-aware bandit over opportunity families |
| skill library | [MineDojo/Voyager](https://github.com/MineDojo/Voyager) | code + description on disk and promote only after success, but replace Voyager's LLM-critic `info.success` with an objective technical activation gate; economic success remains a later, separate gate |
| repair loop | [ShengranHu/ADAS](https://github.com/ShengranHu/ADAS) `_mmlu/search.py` | adapt only the `debug_max=3` stderr/exception repair loop. ADAS rewrites a JSON array and omits generation failures; our append-only, failure-complete JSONL is intentionally different. |
| playbook discipline | ACE [arXiv 2510.04618](https://arxiv.org/abs/2510.04618) | append-only itemized bullets. **Full rewrite = "context collapse". Rewriting PLAYBOOK.md is a bug, not a cleanup.** |
| failure feedback | [openevolve](https://github.com/algorithmicsuperintelligence/openevolve) | artifact side-channel: pipe stderr of the failed run into the next prompt |
| bounded execution | [SWE-agent](https://github.com/SWE-agent/SWE-agent) and [autoresearch](https://github.com/karpathy/autoresearch) | shared remaining-dollar budget, isolated/reset attempts, immutable evaluator, fixed wall-clock budget, baseline first, and keep/discard/crash record |
| budgets/governance | [Paperclip](https://github.com/paperclipai/paperclip) | scoped cost attribution, hard pause/cancel, atomic task ownership, lifecycle/audit patterns; improve it by reserving budget before an action so one late cost event cannot overshoot |
| business procedures | [Project Vend phase two](https://www.anthropic.com/research/project-vend-2) | structured procedures, CRM/inventory state, cost visibility, and prepayment improved performance; adding a same-model CEO did not reliably help |
| long-horizon realism | [AgencyBench](https://aclanthology.org/2026.acl-long.337/) | real workflows require long, expensive trajectories and remain far from reliable; keep the LLM at narrow judgment boundaries |
| payment authenticity | [x402 population study](https://arxiv.org/abs/2607.12575) | settlement count is not customer demand; require an independent payer, fulfilled delivery, retained payment, and repeat use |

Explicitly NOT copied: vector DB retrieval, MAP-Elites islands, tree search.
At N < 100 ventures, `grep` over SKILL.md descriptions + the child-count
novelty bonus is sufficient.

No inspected OSS project proves the complete loop from autonomous opportunity
discovery through external settled revenue, kill/retain, and cross-venture
learning. Auto-company, FreeTurtle, Paperclip and OneManCompany are orchestration
or governance references, not profitability evidence. README claims are never
accepted as economic proof.

## 4. Intake — the four endpoints (all verified 200, zero auth, 2026-08-01)

| source | number it returns | scale measured |
|---|---|---|
| Indie Hackers Firebase `https://indie-hackers.firebaseio.com/products.json` | `selfReportedMonthlyRevenue` + `selfReportedRevenueTimestamp` | 64,158 products |
| Flippa v3 `https://flippa.com/v3/listings?filter[profit_per_month][min]=1000` | `revenue_per_month`, `profit_per_month`, asking price = market multiple | 1,898 listings ≥$1k/mo |
| TrustMRR `https://trustmrr.com/` (SSR HTML, no JSON API) | **Stripe-verified** MRR, growth30d, ARPU | 986 startups |
| x402 Bazaar `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` | USDC price/call + `payTo` (join against Base transfers for realized) | 14,770 resources |

Demand-only (LLM extraction, never revenue proof): English and Japanese X,
HN Algolia, Reddit RSS (throttle: `.json` 403, second call 429), Zenn
`/api/books` (price), note `/api/v3`, brain-market (`price × sales_count`),
GitHub trending, YouTube and relevant public communities. Dais never needs to
read these feeds. Each item is untrusted data, is schema-constrained, keeps its
URL/language/timestamp, and cannot inject instructions into the builder.

Known-blocked, do not retry: Acquire.com (auth, `api.acquire.com` NXDOMAIN),
Product Hunt (Cloudflare; GraphQL needs token), Sensor Tower (paid),
toolify.ai (403), IH `/products` HTML (SPA shell — Firebase is the way in).

No OSS aggregator of these exists (largest = `xammen/trustmrrr-db`, 33★,
single-source). Building the join is itself defensible.

## 5. Architecture

```
INTAKE (6h)      4 revenue endpoints + bilingual demand signals
   │                 → candidate {buyer, problem, offer, market, channel,
   │                               monetization, evidence, capital, url}
   ▼
CURRICULUM       parent = sigmoid(10*(score-0.5)) * 1/(1+children_count)
   │             dedup against loop-registry.json + archive/runs.jsonl
   ▼
BUILDER          read bounded PLAYBOOK view → build in staging → tests/policy →
   │             canary side-effect → promote to skills/earn/ev-<name>/ →
   │             plist → registry → ledger → bounded seed → probation
   │             (or approval_required before the canary)
   │             retry ≤3 with stderr fed back (ADAS debug_max=3)
   ▼
LEDGER           {venture_id, gross, fees, refunds, spend, token_cost,
                  settled net, customer/fulfillment evidence}
   ▼
GATE  ①built: tests and policy checks pass
      ②externally_live: deployed/published side-effect exists
      ③revenue_verified: external payment + fulfilled delivery + retained funds
      ④graduated: realized external revenue > 0 AND fully-loaded net > 0
      default probation 14d; delayed-payout extension is deterministic and capped
      live → allocation weight ×1.05/day within hard dollar caps [expect most killed]
   │
   ├─ graduated → executable skill stays in skills/earn/ev-<name>/
   ├─ killed → skill + plist + death evidence move to entrepreneur/graveyard/
   └─ any transition → archive/runs.jsonl append-only lifecycle event
                          │
                          ▼
                  PLAYBOOK.md  (append-only provenance; reflection fires on an
                  importance budget counter, not every cycle)
                          │ bounded applicable rule view, never whole-file prompt
                          ▼ next BUILDER
                          │
                          ▼
                  TELEGRAM daily: alive N / killed N / month net / new playbook lines
```

The unit of entrepreneurship is not "a Threads agent" or "a YouTube agent".
A venture is the complete chain `buyer × problem × offer × acquisition channel
× fulfillment × payment rail × evidence`. Threads, X, SEO and YouTube are
distribution channels used by a venture; x402 and Stripe are payment rails.
Neither a channel nor a rail is a business by itself.

The three learning organs are PLAYBOOK + archive + curriculum. Without them
the loop only raises experiment count — an incinerator, not an entrepreneur.

## 6. Data contracts

`earn-ledger.jsonl` row (extended — task 1):
```json
{"event_id":"str","run_id":"str","ts":0,"venture_id":"str","source":"str",
 "currency":"USD","gross_usd":0,"fees_usd":0,"tax_usd":0,"refunds_usd":0,
 "spend_usd":0,"token_cost_usd":0,"net_usd":0,"cash_status":"pending|settled",
 "evidence_kind":"stripe|affiliate|x402|invoice|other","evidence_id":"str",
 "external_customer_hash":"str|null","fulfillment_id":"str|null",
 "counterparty_class":"external|related|self|unknown","idempotency_key":"str",
 "finalized":true,"misattributed":false}
```

`archive/runs.jsonl` row (task 6):
```json
{"id":"str","venture_id":"str","parent":"str|null","ts":0,
 "event":"selected|build_failed|staged|externally_live|revenue_verified|graduated|killed",
 "thought":"why this looked profitable",
 "candidate":{"buyer":"str","problem":"str","offer":"str","market":"en-US|ja-JP",
  "channel":"str","monetization":"str","observed_mrr":0,"url":"str",
  "evidence_class":"signal|reported|verified"},
 "fitness":0.0,"evidence_ids":["str"],"stderr_tail":"str|null"}
```

`loop-registry.json` row gains: `origin` (`"human"|"entrepreneur"`), `tier`,
`market`, `status`, `probation_started_ts`, `payout_window_days`,
`allocation_weight`, `capital_at_risk_usd`, `graveyard` (bool). Existing keys (incl. `fleet`,
reserved by the roadmap spawner) are preserved — allocator.py:214 already
promises this.

`meta.json` records the venture contract: buyer, problem, offer, market and
jurisdiction, acquisition channel, monetization, payout latency, T0/T1 tier,
credential requirements, allowed side effects, policy adapter, seed/caps,
origin, parent and probation start.

## 7. Kill gate parameters (single place, no duplication)

| knob | value | why |
|---|---|---|
| probation | 14 days default | fast-settle triage; delayed payout uses one predeclared, capped window |
| seed capital | $5 initial maximum per venture | hypothesis inside stricter action/daily/portfolio mandate caps; includes compute, infra, fees, gas and refundable exposure |
| graduate rule | finalized external gross > 0 AND fully-loaded realized net > 0 | a side effect or near-zero loss is not profit |
| winner scaling | experimental allocation weight ×1.05/day, clamp [0.3, 2.5], still subject to hard dollar caps | validate locally; not transferable profitability evidence |
| loser scaling | experimental allocation weight ×0.95/day then complete kill at probation end | validate locally; never override the profit gate |
| initial keep-rate hypothesis | ~30%; not a target and not transferable evidence | validate from this portfolio; never tune gates to manufacture it |
| build retries | 3 | ADAS `debug_max` |

DGM's `noise_leeway=0.1` is a normalized fitness tolerance, not ten cents. It
may be used only when comparing normalized curriculum fitness; copying it into
USD is a unit error.

Default probation is 14 days for fast-settling ventures. A delayed-payout
venture (affiliate/content/subscription) may receive one deterministic,
predeclared extension up to its `payout_window_days` only when it has objective
buyer evidence (for example a qualifying conversion, checkout, or paid pilot),
zero cap violation, and no LLM-written exception. No-signal ventures die at day
14. Graduation never happens before retained external cash is verified.

Before activation, a versioned mandate sets: allowed actions and identities,
allowlisted accounts/chains/contracts, per-action/per-venture/daily/portfolio
caps, maximum concurrent probation ventures, expiry, and emergency pause.
Checks are atomic and cumulative; splitting actions cannot evade a limit.

## 8. Scoring bias (task 5) — the thing that decides the ceiling

Reject a candidate outright when: ceiling < $10k/mo, revenue is per-hour
human-substitute work (gig/bounty/clip), an equivalent row already exists,
there is no identifiable buyer/payment path, it needs unavailable credentials,
it depends on spam/deception/non-delivery, or its only asset is one platform
account. Add weight for: recurring billing, sell-before-build evidence,
owned/portable customer data, bilingual asymmetry, a second acquisition
channel, deterministic fulfillment, and verified comparable revenue.

Rationale: MRR = E × p × L. Gig-shaped ventures cap L at ~$1-3k/mo no matter
how large E gets. The measured state today (`earn-ledger.jsonl`: 35 rows,
earn Σ 139.75, net +5.21; clip spend 31.32 / earn 0) is exactly that trap.

Every score separates three evidence classes: `signal` (complaint/engagement),
`reported` (seller/self-reported revenue), and `verified` (processor statement,
finalized payment, fulfilled order, retained/renewed revenue). Observed MRR of a
different company is market analogy evidence, never this venture's earnings.

## 8.5 Venture families the loop should search

Ranked starting portfolio:

1. bilingual B2B intelligence or monitoring subscriptions (JP facts for EN
   buyers and EN facts for JP buyers);
2. productized workflow pilots that become a narrow micro-SaaS only after paid
   demand exists;
3. change-monitoring datasets, alerts, and narrow paid APIs;
4. original bilingual toolkits, calculators, templates, and data products;
5. evidence-rich affiliate comparison products;
6. X/Threads/SEO/YouTube media loops only as acquisition for one of the above.

Trading/yield remain money rails owned by the roadmap, not businesses produced
by this loop. x402 is an optional payment rail, not proof of demand. Mass AI SEO,
generic prompt packs, repetitive faceless video, bulk cold outreach, and
unapproved autonomous replies are rejected or staged for explicit approval.

The four supplied X articles are useful discovery signals for the affiliate
funnel pattern (offer selection → education → trust → conversion → analytics),
especially cross-language localization. Their revenue claims are not used as
fitness evidence because the posts provide no processor statements or cohort
data and all lead to a LINE opt-in.

## 8.6 User experience and autonomy boundary

Dais gives the system one revocable standing mandate. Inside it, the system
researches, builds, launches, measures, kills, learns and reports without asking
for ideas. Outside it, the exact action is staged as `approval_required` and
defaults to deny on expiry; other ventures continue.

Automatic: public read-only research, local generation/tests, sandbox deploys,
bounded actions already named in the mandate, routine management, complete kill,
append-only learning and reports.

Approval/standing-mandate required: first public deployment or identity use,
social/customer communication, a new credential scope, customer/private data,
new recipient/contract/financial venue, refunds/subscriptions/legal promises,
or spend beyond a cap. Leverage, borrowing, token issuance and cap increases
always require an exact approval and cannot be approved by the model itself.

Every venture uses least-privilege venture-scoped credentials. It never inherits
the user's general shell environment, browser session, Telegram secret, wallet
master key, or unrelated product data. All external writes/payments have durable
idempotency keys. Emergency pause blocks new side effects synchronously while
preserving logs and allowing safe capital recovery.

Kill is complete only after: process stop, plist bootout, endpoint disablement,
venture credential revocation, subscription/DNS cleanup where applicable,
recoverable-capital reconciliation, graveyard archival, and verification.

## 8.7 Telegram and status UX

Daily 08:30 JST, including no-op days:

```text
🟢 Entrepreneur — Aug 2, 08:30 JST
No action needed.
24h: +$1.42 revenue -$0.31 venture spend -$0.08 compute = +$1.03 net
MTD: +$8.76 net | cash $42.10 | capital at risk $11.20 / $25 cap
Portfolio: 3 live | 4 probation | 1 killed | 0 approval-waiting
Funnel: scanned 1,284 → selected 2 → built 1 → launched 1
Winner: invoice-api +$0.94 | Killed: clip-bounty, 14d net -$1.12
System: healthy | last 08:01 | next 08:31 | ledger fresh 08:27
Evidence: 2 finalized payments, 1 fulfilled buyer receipt
```

The first line after the title is always `No action needed` or one exact action
needed. Values come from ledger/registry/launchd evidence, never model narration.
Urgent messages are reserved for already-paused safety events: unknown
transaction/publication, cap or guard failure, ledger mismatch, excess loss,
secret/identity compromise, harmful public behavior, crash loop, or missed
cadences. Ordinary build failures, zero-revenue days and expected kills stay in
the daily digest. Weekly Monday 09:00 reports cohort survival, per-venture P&L,
failure classes, reliability, new PLAYBOOK lines and the next autonomous plan;
it never asks Dais for ideas.

`~/.anicca-founder/state/entrepreneur-status.json` is written atomically with a
schema version, generated/freshness timestamps, semantic health
(`healthy|degraded|approval_required|paused|unsafe_paused`), last/next cadence,
portfolio, P&L, capital at risk, pending approvals and evidence IDs. Raw
`launchctl` state is diagnostic detail, not semantic health. Minimum controls:
pause all, pause/kill one venture, approve/reject one exact action, resume safely,
and inspect/export venture evidence. Telegram may pause/reject/approve a bounded
one-time action; raising caps or weakening policy requires a stronger local
control surface.

## 9. TODO — ordered, each with its acceptance test

Order is fixed. Do #N, prove #N, then #N+1. No asking which to start.

| # | task | acceptance (fresh evidence required) |
|---|---|---|
| 1 | ledger attribution/evidence schema (§6): migrate 35 existing founder rows without erasing corrections | per-venture settled P&L prints from the founder ledger alone; misattributed/related/self rows contribute $0; totals reconcile independently |
| 2 | **GATE + MANDATE + PAUSE**: lifecycle states, pre-spend reservations, caps, idempotency, emergency pause, complete kill, atomic semantic health and urgent safety report | deliberately seed a losing venture → pause blocks every new side effect; kill verifies cleanup/capital; duplicate wakes cannot double-act; builder remains disabled unless health is fresh and safe |
| 3 | registry writable: remove the 7-name hardcode, allocator reads dynamic roster | a hand-added row is picked up by `ceo-pass.sh` with no code edit |
| 4 | **INTAKE**: fetchers for IH Firebase / Flippa v3 / TrustMRR / x402 Bazaar + bilingual demand signals with untrusted-content isolation | one run emits ≥100 schema-valid candidates, each with buyer/problem/market, a number, provenance and URL; prompt-injection fixture cannot alter policy/tools |
| 5 | SCORE + dedup (§8 rules), market/jurisdiction/policy/evidence classification | zero duplicates; every selected candidate names buyer, offer, channel, payment, proof path and required credentials |
| 6 | `archive/runs.jsonl` append-only lifecycle events | every state transition writes exactly one idempotent event, failures included |
| 7 | `PLAYBOOK.md` append-only provenance + bounded applicable-rule view + importance-budget reflection | each rule has ID, evidence run IDs, applicability, support/contradiction counts and supersession state; full rewrite is impossible; builder prompt stays bounded |
| 8 | **BUILDER** compensating saga: isolated staging → test/policy scan → least-privilege credentials → canary → promote skill → `ai.anicca.ev-*` plist → registry/ledger → bounded start/approval; retry ≤3 with redacted/truncated stderr → commit+push | ★ one new venture reaches `externally_live` inside the mandate; crash tests at every boundary roll back without duplicate spend/post, leaked credential or non-`ev-` modification ★ |
| 9 | CURRICULUM `score_child_prop` | 10 consecutive cycles do not all pick the same branch |
| 10 | allocator handles entrepreneur-origin ventures (hard caps + allocation weight ×1.05/0.95) | a graduated venture's allocation rises without exceeding any dollar/concurrency cap |
| 11 | complete daily/weekly/urgent Telegram UX + exact approvals/controls (`ai.anicca.telegram-bot.plist` currently NOT loaded; helper exists), extending task 2's safety channel | daily message arrives on Dais's device even on a no-op day; pause/reject works; report values reconcile to files |
| 12 | repair required failing launchd jobs and prove entrepreneur health: recent successful cadence, non-overlap lock, reconciled ledger, report delivery, no crash loop | all required jobs last-exit 0 and `entrepreneur-status.json` says `healthy` from fresh evidence |
| 13 | **14-day unattended run** = §1 `done` | 14 consecutive mandate-stable days, ≥1 non-owner/non-related settled profitable venture surviving its refund window, total portfolio net > 0 after all costs, ≥30 lifecycle events, ≥10 evidenced PLAYBOOK lines, and 14/14 daily reports |
| 14 | separately repair/reconcile the dark OpenClaw cron live store | its three job counts reconcile and an enabled test job obtains a non-null next wake; this does not block EL-1–13 |

## 10. Failure modes we are pre-committing against

| # | documented failure | our guard |
|---|---|---|
| F1 | long-horizon collapse unrelated to context size ([Vending-Bench, arXiv 2502.15840](https://arxiv.org/abs/2502.15840)) | state lives in files (registry/ledger/archive), never in a conversation |
| F2 | nothing blocks a weak result before release ([autoresearch survey](https://haizhaoyang.github.io/research/autoresearch-survey.html): 56 systems, zero reached multi-project portfolio) | task 2 ships BEFORE task 8 — the gate exists before the builder |
| F3 | adding a manager agent made it worse ([Project Vend 2](https://www.anthropic.com/research/project-vend-2)) | no new supervisory layer; reuse the existing CEO pass |
| F4 | 30% autonomous task-completion ceiling ([TheAgentCompany, arXiv 2412.14161](https://arxiv.org/abs/2412.14161)) | if the gate reverts everything for 14 days, fall back to parameter evolution of existing earners (`skills/earn/self-improve/`) and say so out loud |
| F5 | context collapse from rewrite or from injecting an ever-growing file | PLAYBOOK is append-only provenance; builder reads a bounded, tagged derived view (task 7) |
| F6 | high-earning agents cheat (Vending-Bench 2 arena: price cartels, refund fraud) | scoring rejects any method whose margin depends on non-delivery; ledger requires a real tx/receipt |
| F7 | settlement/activity counts can be manufactured (x402 population study) | independent customer hash + fulfillment + retained payment; self-funded/wash/internal-cluster payments never count |
| F8 | platform content farms lose distribution/monetization | policy adapters + provenance/originality + owned list/data + second channel |
| F9 | launchd retry duplicates a post/payment | durable idempotency key on every external side effect |

## 11. Revenue path and honest expectations

`E × p × L` is a portfolio throughput proxy, not an accounting identity or
forecast: E = experiments/week, p = probation pass rate, L = typical retained
winner MRR. The builder raises E. PLAYBOOK + archive may raise p. Scoring and
distribution may raise L. Raising E alone burns tokens and returns $0.

| horizon | expected | binding variable |
|---|---|---|
| month 1-3 | build bounded experiments; most die; archive fills; first external dollar is the target | E + evidence |
| month 3-6 | repeated paid demand promotes one offer into subscription/API/micro-SaaS | p + retention |
| month 6-12 | scoring rejects gig/content-farm shapes; a winner may reach meaningful MRR | L + distribution |
| later | allocator concentrates effort/capital into retained winners and adds a second channel | compounding |

$10M is a direction, not a forecast or acceptance criterion. It does not come
from 1,000 small loops. It would require running experiments cheaply, proving
retention, and concentrating on a product with real distribution. The
defensible asset is verified learning plus disciplined kill/scale gates, not
the builder or an activity count.
