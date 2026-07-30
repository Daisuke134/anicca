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

---

## 7. Host-key cost containment

### 7.1 The leak, restated precisely

Our own loops cost **$0 marginal**. Codex runs `gpt-5.6-terra` on `auth_mode=chatgpt`
OAuth, and `agent_runner.py:316-322` pops `ANTHROPIC_BASE_URL` /
`ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` before
launch, so no pay-as-you-go key can be reached. 42/42 recorded attempts carry
`cost_tier:"subscription"`. The `$1.47/day` in the ledgers is
`cost_basis:"api_equivalent_estimate"` — **never billed**.

The real money runs the other way. `CAPAFY_HOST_OPENROUTER_KEY` is injected as a
CP2 hosted config key into every published listing
(`~/.openclaw/skills/capafy-autopublish/scripts/drive_checkpoint2.py:43-53`,
gated by `scripts/key_health_gate.sh`), so **every subscriber run of every
listing bills our OpenRouter account**. That spend was uncapped and unlogged.

### 7.2 Budget-guard mechanism (found in code, not invented)

| Where | What |
|---|---|
| `agent_runner.py:947-955` | Reads `ANICCA_BUDGET_SCOPE_ID`, `ANICCA_PASS_TOKEN_BUDGET`, `ANICCA_LOOP_DAILY_TOKEN_BUDGET`. `budget_enabled = all(...)`; any strict subset raises `token budget scope/pass/daily settings must be provided together`. |
| `agent_runner.py:960-962` | `ANICCA_BUDGET_REQUIRED=1` makes an unconfigured budget a hard refusal. |
| `agent_runner.py:967-969` | `ANICCA_BUDGET_DAILY_SCOPE` keys the daily pool to one caller (defaults to `--loop`, so callers sharing a loop name share a pool). |
| `agent_runner.py:970-976` | Reservation size comes from `task_classes.<class>.token_reservation` in `config.json` — already positive for every class, so it was never the blocker. |
| `agent_runner.py:977-980` | `ANICCA_TOKEN_BUDGET_LEDGER`, default `~/.local/state/anicca/telemetry/token-budget.jsonl`. |
| `agent_runner.py:1011-1013` | The literal source of the string: `last_budget` initialises to `{"status":"disabled","reason":"budget_not_configured"}` and is only replaced when `budget_enabled`. |
| `agent_runner.py:1024-1042` | `reserve()` per attempt; `status=="blocked"` breaks the candidate loop **before** any provider launches. |
| `agent_runner.py:1152-1168` | `settle()` replaces the reservation with measured usage; for codex the charge is `total_tokens - cached_input_tokens` (`agent_runner.py:196-212`). |

So the budget was **never configured**, not broken. Reference wiring already
existed at `profitable-claude/skills/gig-work/gig_pass.sh:211-227`.

### 7.3 What was configured

Sizing is from measured `charged_tokens` in
`~/.openclaw/state/agent-runner-evidence/capafy-*/*/attempts.jsonl`.

| Lane | Measured peak / mean charged | Pass limit | Daily limit | Daily scope |
|---|---|---|---|---|
| `capafy-loop-daily.sh` (money loop, `browser-lane-agent`) | 6,434,708 / 1,340,211 (n=5) | 16Mi = 16,777,216 (~2.6x peak) | 32Mi = 33,554,432 | `capafy-loop-daily` |
| `daily_loop.sh` (drainer, `tool-agent`) | 47,433 / 47,355 (n=2) | 2Mi = 2,097,152 | 8Mi = 8,388,608 | `capafy-drainer` |

`ANICCA_BUDGET_REQUIRED=1` was deliberately **not** set: these are revenue lanes
and a missing env var must not convert the money loop into a hard refusal. The
three required exports are unconditional in both scripts, so the breaker is armed
either way. Separate `daily_scope` values stop the drainer's small pool from
being charged against the money-loop pass (the exact bug called out in
`gig_pass.sh:222-225`).

### 7.4 Observed before/after (real runs, PATH stripped so no model was billed)

```
RUN A  before, no budget env:
  attempt 1 budget= {"status": "disabled", "reason": "budget_not_configured", "scope_id": null}
RUN B  after, exact exports now in capafy-loop-daily.sh:
  attempt 1 budget= {... "daily_scope": "capafy-loop-daily", "day": "2026-07-30",
                     "status": "allowed", "reason": null, "reservation_tokens": 24576,
                     "pass_limit_tokens": 16777216, "daily_limit_tokens": 33554432,
                     "charged_tokens": 24576, "pass_consumed_after_tokens": 24576}
RUN C  breaker trips (pass limit forced to 1000):
  summary budget= {... "status": "blocked", "reason": "pass_token_budget_exceeded"}
  attempts recorded = 0        rc=75      <- no provider ever launched
```

### 7.5 What is now logged

`~/.openclaw/skills/capafy-autopublish/scripts/host_key_usage_log.py` appends to
**`~/.openclaw/state/capafy-host-key-usage.jsonl`**, called once per pass from
both `capafy-loop-daily.sh` and `daily_loop.sh` (placed before the
DRAINED/CAP_FULL early exit, so healthy-idle passes still sample). Non-fatal by
design. First real row, 2026-07-30:

```json
{"attribution":"account_level_only","key_env":"CAPAFY_HOST_OPENROUTER_KEY",
 "listings_online_ledger":8,"provider":"openrouter","remaining_usd":20.223932,
 "status":"ok","total_credits":25.0,"total_usage_usd":4.776067671,"note":"bootstrap-verify"}
```

Second sample confirmed `delta_usd` / `delta_seconds` populate against the prior
row. **Host-key spend to date = $4.78 of $25 credit.** Measurable now: total
host-key spend, and spend per sampling interval (daily, once the loops run).

### 7.6 What is still NOT measurable, and why (do not fake it)

Per-listing / per-subscriber-run cost attribution is **impossible from our side
today**. Probed live 2026-07-30:

| Endpoint | Result |
|---|---|
| `GET openrouter.ai/api/v1/credits` | **200** `{"data":{"total_credits":25,"total_usage":4.776067671}}` — account-level cumulative only, no listing or run dimension. |
| `GET openrouter.ai/api/v1/activity` | **403** `Only management keys can fetch activity for an account` — the per-day/per-model feed needs a management (provisioning) key we do not hold. |
| `GET openrouter.ai/api/v1/keys/current` | **401** `Invalid management key`. |

Two independent blockers: (1) Capafy's runtime makes the model call server-side
and never returns an OpenRouter generation id, so `/api/v1/generation?id=...` —
the only per-request cost endpoint — cannot be joined to a subscriber run;
(2) all 27+ listings share **one** key, so even with a management key there is no
listing dimension. The log therefore records `attribution:"account_level_only"`
plus `attribution_blocker`, and never allocates a per-listing number.

**UNVERIFIED:** the daily `delta_usd` figure — no loop pass has run since the
wiring landed, so only the two manual bootstrap samples exist (`delta_usd: 0.0`
over 8s). Also UNVERIFIED: `CAPAFY_HOST_ANTHROPIC_KEY` / `_OPENAI_KEY` spend —
only the OpenRouter key is read by `key_health_gate.sh` and
`drive_checkpoint2.py`; whether the other two are live in any listing's CP2
config was not confirmed from our side, and neither has a balance endpoint wired.

### 7.7 Provider-dashboard steps a later task MUST perform (hard caps)

Not done here — out of scope, and no browser was touched.

1. **OpenRouter → Settings → Credits**: set an account-level spend limit. Today
   the only ceiling is the $25 prepaid balance; there is no per-day cap.
2. **OpenRouter → Settings → API Keys**: for the existing
   `CAPAFY_HOST_OPENROUTER_KEY`, set a per-key **credit limit**. This is the one
   true hard cap and it is dashboard-only.
3. **One key per listing.** Mint a separate OpenRouter key per listing, each with
   its own per-key limit, and inject it at CP2. This is what makes per-listing
   attribution real *and* blast-radius bounded — a single runaway listing then
   cannot drain the shared pool. Requires re-driving CP2 for live listings, so it
   must be staged, not bulk-applied.
4. **Do NOT rotate** `CAPAFY_HOST_ANTHROPIC_KEY` / `_OPENAI_KEY` /
   `_OPENROUTER_KEY` — they are live inside 27 published listings; rotating
   breaks paying subscribers. Add limits to the existing keys instead.
5. Verify each by reading `remaining_usd` in
   `~/.openclaw/state/capafy-host-key-usage.jsonl` before and after.

### 7.8 Residual risk

A subscriber-side runaway can still burn the entire remaining $20.22 OpenRouter
balance between two daily snapshots, because the only hard cap available is the
prepaid balance and the only alerting is `key_health_gate.sh`'s once-per-day
low-balance Telegram — item 7.7.2 is the actual fix.
