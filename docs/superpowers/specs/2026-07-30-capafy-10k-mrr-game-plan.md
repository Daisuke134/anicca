# Capafy → $10k/mo game plan (SSOT)

**Date**: 2026-07-30
**Status**: active. Tasks #1–#6 registered.
**Trigger**: Dais asked (a) is the Capafy loop working, (b) why is marketing not creating accounts / posting daily, (c) how much money are we wasting on router API keys, (d) the whole game plan to $10k MRR selling skills, (e) how to make dev + marketing loops self-improving.

All numbers below are **measured** on 2026-07-30 by five parallel read-only audits (loop logs/state, live Capafy dashboard via the running CloakBrowser daily-driver, live marketplace parsing, 20 web/gh sources). Anything inferred is labelled INFERENCE.

---

## 1. Measured state

### 1.1 Loops

| Loop | Fires | Does its job | Root cause | Evidence |
|---|---|---|---|---|
| `capafy-loop-daily` (dev) | 08:10 daily, rc=0 | **NO** — 0 new skills since 07-28 | one orphan draft (agent `9470213182`) consumes 100% of every 900s pass; CP2 hosted-key step exits 1 with no fallback | `drive_checkpoint2.py:161`; `capafy-loop-daily.sh:17`; `agent-runner-evidence/capafy-marketplace/1785366604-51504/attempt-01.result.json` |
| `capafy-goal-monitor` | 09:00 daily | measure-only | `goal_a.pass:false` for 12 days, no remediation branch | `capafy-goal-monitor.out` |
| `capafy-ig-marketing-daily` | 16:00 daily, **rc=0** | **NO — 11 days zero posts (07-19→07-30)** | `IG_PROVISION_PORT="9332"` hardcoded; nothing in the repo ever launches a browser on 9332 | `capafy-ig-marketing-daily.sh:98`; `agent-runner-evidence/capafy-ig-marketing/1785308429-77606/attempt-01.result.json`: `Provision stopped at preflight: dedicated CDP port 9332 was unavailable` |
| `capafy-marketing-warmup` | 11:20 +jitter | **NO** | blocks on the above: `capafy warmup: no active account -> PROVISION on daily pass` ×7 | `capafy-marketing-warmup.err.log` |
| `clip-loop` | daily | **YES** (IG only) | — | `clip-earn-ledger.jsonl` (117 rows) |
| X leg | — | never posted | ledger file exists, 0 bytes, no launchd job | `capafy-marketing-x-ledger.jsonl` |
| TikTok leg | — | never existed | no ledger, no loop | `launchctl list` |

Account creation **is** wired (`capafy-ig-marketing-daily.sh:32-34`, `:92-108`) and the gate fires correctly (`provision_needed=yes reason=cooked-marker`). It dies at the port preflight and then **exits 0** — which is why 8 days of failure were silent. 9 account rows are dead: 7 `provision_failed` (07-22…07-29), 1 `poisoned`, 1 `session_failed` (`~/.cloak/clip-accounts-capafy.json`).

Life-manager marketing is **already** the same poster (`marketing-engine/poster.py`, listing rotated by `scripts/select_listing.py`); the `ai.anicca.life-manager-*` jobs are payout/ledger only. Nothing to unify — it is starved by the identical cause.

### 1.2 Cost — the premise was wrong

| | Measured | Evidence |
|---|---|---|
| Loop LLM path | codex `gpt-5.6-terra`, `auth_mode=chatgpt` OAuth; runner **pops** `ANTHROPIC_*`/`OPENAI_API_KEY` from child env | `~/.codex/auth.json`; `agent_runner.py:316-322` |
| Metered burn | **$0.00/day** — 42/42 attempts `cost_tier:"subscription"` | `agent-runner-evidence/*capafy*/*/attempts.jsonl` |
| The $1.47/day in ledgers | `cost_basis: api_equivalent_estimate` — shadow, never billed | same |
| clawrouter | `Wallet empty ($0.00), falling back to free model` | clawrouter log |

**The real leak is the opposite direction**: `CAPAFY_HOST_ANTHROPIC_KEY` / `_OPENAI_KEY` / `_OPENROUTER_KEY` are injected as CP2 config keys into published listings (`drive_checkpoint2.py`, `key_health_gate.sh`), so **every subscriber's run bills our keys** — uncapped and unlogged, while the runner budget guard reports `{"status":"disabled","reason":"budget_not_configured"}` on every pass. This bill grows exactly when marketing starts working. Must be capped **before** traffic scales. UNVERIFIED: actual provider dollar usage — no local usage log exists and no billing API was called.

### 1.3 Revenue and funnel

| Metric (7d, 07-22→07-28) | Value |
|---|---|
| Impressions | 1.2K (−17.2%) |
| Detail page views | 110 (+11.1%) |
| Conversion rate | **0.00%** |
| New buyers / units | 0 / 0 |
| Traffic: category | 439 imp → 4 visits |
| Traffic: search | 343 imp → 16 visits |
| Traffic: featured | **0 imp → 0 visits** |
| Direct | 46 visits |
| External referral | 1 visit |
| Promotion link "marke" | 0 clicks, $0.00 |
| Paid ad links / ad account | never created |
| Agents live / draft / review-failed | 27 / 1 / 1 |
| Lifetime | 1 order, $9.99 gross, **$8.00 pending, $0.00 realized** |
| Payout | threshold $100 — **$92.00 short** |

110 views at an expected ~2.5% conversion = 2.75 expected sales, so 0 sales is **not yet a copy problem — it is a volume problem, ~25× short** (INFERENCE from the 2.5% figure).

Note: `capafy.ai/developer/growth` is **not our metrics** — it is Capafy's marketing case-study page; its 200K views / 13,900% / $4,200 belong to publisher **Otata**. Our real data is at `/developer/overview`.

---

## 2. What actually sells (70 live listings parsed, 2026-07-30)

| Pattern | Number |
|---|---|
| Top 1 listing | **57% of all 4,889 sales** |
| Top 5 | 79% |
| Median listing | 11 sold |
| Under 10 sold | 33/70 |
| Winning verticals | **recurring-event data**: football fixtures (2,788 sold, $99.99/yr), stock tracking ($9.99/wk, 781), X/KOL tracking, video gen |
| Winning price | $9.99/**week** (modal), $1.99/day |
| Free-trial packaging | 36/70 by count, **0 of the ≥100-sold tier** |
| Winning copy | named-expert proof line ("500M views", "10+ yrs HR") |
| Packaging | closed-source Subscription > Download (Download hands over source) |

Contract (`capafy.ai/publisher-agreement` §7.3): `Publisher Earnings = (user price − Platform Sandbox Fee) × 80%`. Cert fee $0.99 once. Sandbox On-Demand $2/mo, $0.50/wk, $0.07/day. Unlike GPT Store's invite-only pilot, this rev-share is **contractual**.

**Our defect**: 27 listings are generic one-shot B2B doc writers (performance-review, ESG scoper, sales-objection, job-description). A one-shot document has no reason to renew a weekly subscription. Winner-take-most means 27 mediocre listings lose to 1 strong listing in a hot vertical.

---

## 3. The $10k math

Net publisher earnings, 4.33 wk/mo:

| Packaging | Net/sub/mo | Active subs needed |
|---|---|---|
| $9.99/week | $32.87 | **304** (INFERENCE) |
| $1.99/day | $46.08 | 217 (INFERENCE) |
| $29.99/month | $22.39 | 447 (INFERENCE) |

Reachable: top listing has 2,788 cumulative sold; `capafy.ai/earn` lists a live **$10,000+/mo** skill (KOL Hunter Pro). Feasibility gate (INFERENCE): 304 subs at ~2.5% visitor→paid needs **~12,000 qualified visitors/mo** — a volume only in-store search + programmatic SEO supply. X and Product Hunt cannot (PH median ~115 signups/7d; HN ~9,700 visitors one day at 94% bounce, ~0 next day).

Distribution ranking (cited): (1) in-store search/ASO — name-first rename moved one product 2,400→8,100 impressions/wk, installs 120→380/30d (unaudited author); (2) indexing communities — Qiita 1,247 clicks with 14-day tail vs X 342 clicks decaying in 3 days; (3) pSEO — Zapier 800,632 pages → 306,000 organic/mo; (4) PH; (5) HN; (6) X.

---

## 4. Plan, ranked by leverage

| # | Task | Gate metric |
|---|---|---|
| P0 (#2) | Cap `CAPAFY_HOST_*` keys, enable the disabled runner budget, log $/subscriber-run | cap enforced + cost/listing measurable |
| P1 (#1) | Dynamic/leased provisioning CDP port + real browser launch + loud non-zero failure + GC junk account rows | preflight passes; account created; warmup day1-2, commercial day3 |
| P2 (#3) | Budget-split the dev pass (orphan ≤1/3), agentic CP2 screenshot loop, handle `review_rejected` orphans, fix browser-lane timeout + coconala lease collision | `isConfirmedConfigKeys=1` observed + ≥1 brand-new skill per pass |
| P3 (#4) | Portfolio pivot: renewal test, recurring-event niches, $9.99/wk closed-source sub, keyword-first names + proof line | impression→detail-view CTR |
| P4 (#5) | Traffic engine: short-video→name-search, pSEO catalog, tracked promo links + ad-account sync, X + TikTok legs on the existing poster | qualified visitors/mo → 12,000 |
| P5 (#6) | Self-improving: daily `sitemap-agents-*.xml` crawl + Δ Sold/category = revealed demand; Thompson sampling over listings by revenue/impression; next skill from the winning arm; alert on N silent failures | net earnings/mo per category |

Copy+tweak, do not rebuild: `Capafy/Capafy-skills` (official publisher API, MIT, 30★), `fidelity/mabwiser` (bandit), `ngo275/app-agent` (listing optimizer), `agamm/pseo-next`, `charlesdove977/search-console-mcp`, `manojahi/serpiq`.

---

## 5. Self-improving loop (each step named by its gate)

1. **Mine demand from the store** — crawl `sitemap-agents-*.xml` (1,056 listings) daily, diff `Sold`. Gate: **Δ Sold/day per category**. Build only into rising categories.
2. **Publish into the winning category** via `capafy-publisher`. Gate: **≥1 new listing/day**; kill after two review rejections.
3. **Name-first title + proof line, priced at the observed mode.** Gate: **impression→detail CTR**; rename until it rises.
4. **External traffic via pSEO + indexing communities.** Gate: **organic clicks/page** from Search Console; kill pages below floor.
5. **Allocate attention by Thompson sampling, not fixed A/B.** Gate: **revenue per listing per impression**.
6. **Next skill from the winning arm's category, never a guess.** Gate: **net earnings/mo per category**; terminate at $10k, else back to step 1.

Two operational invariants this fixes: both loops **exited rc=0 while dead** (8 and 11 days), and `capafy-goal-monitor` measured `pass:false` for 12 days without acting. Silent success is the bug class — every gate above must fail loudly.

---

## 6. Honest gaps

- Provider dollar usage for `CAPAFY_HOST_*` keys: **UNVERIFIED** (no local log, no billing call).
- Where Capafy's own traffic comes from: **UNVERIFIED** — instrument promo links before trusting any in-store vs external split.
- The 2,400→8,100 impressions and $3,700 MRR case numbers come from self-promoting, unaudited authors.
- Whether our 27 listings offer free trials: **UNVERIFIED** on the dashboard.
- Exact clip-loop post dates: `clip-earn-ledger.jsonl` rows carry no `ts` field.
