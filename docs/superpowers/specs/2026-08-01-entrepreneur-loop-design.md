# Entrepreneur Loop — design spec (2026-08-01)

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

> 14 consecutive days, zero human input, during which the entrepreneur loop
> ran intake → build → probation → kill on its own, produced **≥1
> self-discovered venture with net > 0**, wrote **≥30 rows** to
> `archive/runs.jsonl` (successes AND failures), and appended **≥10 lines**
> to `PLAYBOOK.md`, with a daily P&L delivered to Telegram every day.

Non-goals for this spec: spawning whole Anicca instances (`self/spawn`,
roadmap 3a), the GitHub-Issue social layer (3d), inter-Anicca funding (3e).
Those sit ON TOP of a working entrepreneur loop and are tracked in the roadmap.

## 2. Where it lives

| thing | path |
|---|---|
| loop | `~/anicca/skills/self/entrepreneur/` |
| learning: skill library | `~/anicca/skills/earn/<venture>/` (already the convention) |
| learning: attempt archive | `~/anicca/skills/self/entrepreneur/archive/runs.jsonl` |
| learning: playbook | `~/anicca/skills/self/entrepreneur/PLAYBOOK.md` |
| registry (roster SSOT) | `~/.anicca-founder/state/loop-registry.json` |
| money SSOT | `~/anicca/skills/earn/state/earn-ledger.jsonl` (sole writer stays `record-earn.mjs`, INV-H2) |
| host | existing `ai.anicca.founder-loop-cadence` (30 min) calls it; no new daemon |

## 3. Prior art we copy verbatim (no invention)

| part | source | what we take |
|---|---|---|
| kill gate | [jennyzzt/dgm](https://github.com/jennyzzt/dgm) `DGM_outer.py:151-190` | `filter_compiled()` then `keep_better(noise_leeway=0.1)` — admit only if `score >= parent - leeway` |
| curriculum | same, `DGM_outer.py:50-148` | `score_child_prop = sigmoid(10*(score-0.5)) * 1/(1+children_count)` — exploit + novelty in ~40 lines |
| skill library | [MineDojo/Voyager](https://github.com/MineDojo/Voyager) | code + description on disk; **write only on success** (`if info["success"]: add_new_skill`) |
| attempt archive | [ShengranHu/ADAS](https://github.com/ShengranHu/ADAS) `_mmlu/search.py:147` | ONE append-only JSON of `{thought, name, code, fitness}`; `debug_max=3` repair rounds |
| playbook discipline | ACE [arXiv 2510.04618](https://arxiv.org/abs/2510.04618) | append-only itemized bullets. **Full rewrite = "context collapse". Rewriting PLAYBOOK.md is a bug, not a cleanup.** |
| failure feedback | [openevolve](https://github.com/algorithmicsuperintelligence/openevolve) | artifact side-channel: pipe stderr of the failed run into the next prompt |
| capital allocation | [atlas-gic](https://github.com/chrisworsey55/atlas-gic) | winners ×1.05/day, losers ×0.95, clamp [0.3, 2.5]; observed keep-rate 30% |

Explicitly NOT copied: vector DB retrieval, MAP-Elites islands, tree search.
At N < 100 ventures, `grep` over SKILL.md descriptions + the child-count
novelty bonus is sufficient.

## 4. Intake — the four endpoints (all verified 200, zero auth, 2026-08-01)

| source | number it returns | scale measured |
|---|---|---|
| Indie Hackers Firebase `https://indie-hackers.firebaseio.com/products.json` | `selfReportedMonthlyRevenue` + `selfReportedRevenueTimestamp` | 64,158 products |
| Flippa v3 `https://flippa.com/v3/listings?filter[profit_per_month][min]=1000` | `revenue_per_month`, `profit_per_month`, asking price = market multiple | 1,898 listings ≥$1k/mo |
| TrustMRR `https://trustmrr.com/` (SSR HTML, no JSON API) | **Stripe-verified** MRR, growth30d, ARPU | 986 startups |
| x402 Bazaar `https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources` | USDC price/call + `payTo` (join against Base transfers for realized) | 14,770 resources |

Demand-only (no numbers, LLM extraction, never the ranking key): HN Algolia,
Reddit RSS (throttle: `.json` 403, second call 429), Zenn `/api/books` (price),
note `/api/v3`, brain-market (`price × sales_count`), GitHub trending.

Known-blocked, do not retry: Acquire.com (auth, `api.acquire.com` NXDOMAIN),
Product Hunt (Cloudflare; GraphQL needs token), Sensor Tower (paid),
toolify.ai (403), IH `/products` HTML (SPA shell — Firebase is the way in).

No OSS aggregator of these exists (largest = `xammen/trustmrrr-db`, 33★,
single-source). Building the join is itself defensible.

## 5. Architecture

```
INTAKE (6h)      4 revenue endpoints + demand signals
   │                 → candidate {method, observed_mrr, multiple, capital_needed, url}
   ▼
CURRICULUM       parent = sigmoid(10*(score-0.5)) * 1/(1+children_count)
   │             dedup against loop-registry.json + archive/runs.jsonl
   ▼
BUILDER          read PLAYBOOK.md → spec → skills/earn/<name>/ → plist →
   │             registry row → ledger wiring → seed $5 → start
   │             retry ≤3 with stderr fed back (ADAS debug_max=3)
   ▼
LEDGER           {venture_id, earn_usd, spend_usd, token_cost, tx}
   ▼
GATE  ①filter_compiled: real side-effect? (tx / POST_ID / inbound USDC)
      ②probation 14d: net >= -0.1 → live, else unload plist + registry graveyard
      live → capital ×1.05/day (clamp 0.3–2.5)          [expect ~70% killed]
   │
   ├─ success → skills/earn/<name>/ stays = SKILL LIBRARY
   └─ any outcome → archive/runs.jsonl (1 row, always)
                          │
                          ▼
                  PLAYBOOK.md  (append-only; reflection fires on an importance
                  budget counter, not every cycle)  → next BUILDER reads it
                          │
                          ▼
                  TELEGRAM daily: alive N / killed N / month net / new playbook lines
```

The three learning organs are PLAYBOOK + archive + curriculum. Without them
the loop only raises experiment count — an incinerator, not an entrepreneur.

## 6. Data contracts

`earn-ledger.jsonl` row (extended — task 1):
```json
{"ts":0,"venture_id":"str","source":"str","earn_usd":0,"spend_usd":0,"token_cost_usd":0,"tx":"0x…|null"}
```

`archive/runs.jsonl` row (task 6):
```json
{"id":"str","parent":"str|null","ts":0,"thought":"why this looked profitable",
 "candidate":{"method":"str","observed_mrr":0,"url":"str"},
 "outcome":"built|build_failed|killed|alive","fitness":0.0,"stderr_tail":"str|null"}
```

`loop-registry.json` row gains: `origin` (`"human"|"entrepreneur"`),
`probation_started_ts`, `graveyard` (bool). Existing keys (incl. `fleet`,
reserved by the roadmap spawner) are preserved — allocator.py:214 already
promises this.

## 7. Kill gate parameters (single place, no duplication)

| knob | value | why |
|---|---|---|
| probation | 14 days | shorter than a monthly billing cycle; long enough for a real payout |
| seed capital | $5 | one loss ≈ one day of token floor |
| admit rule | `net_usd >= -0.1` | DGM `noise_leeway=0.1` |
| winner scaling | ×1.05/day, clamp [0.3, 2.5] | ATLAS |
| loser scaling | ×0.95/day then unload at probation end | ATLAS |
| expected keep rate | ~30% | ATLAS measured 16 keep / 37 revert |
| build retries | 3 | ADAS `debug_max` |

## 8. Scoring bias (task 5) — the thing that decides the ceiling

Reject a candidate outright when: ceiling < $10k/mo, or revenue is per-hour
human-substitute work (gig/bounty/clip), or an equivalent row already exists in
registry or archive. Add weight for: recurring billing, agent-to-agent demand
(x402), and existing verified-revenue evidence in the intake row.

Rationale: MRR = E × p × L. Gig-shaped ventures cap L at ~$1-3k/mo no matter
how large E gets. The measured state today (`earn-ledger.jsonl`: 35 rows,
earn Σ 139.75, net +5.21; clip spend 31.32 / earn 0) is exactly that trap.

## 9. TODO — ordered, each with its acceptance test

Order is fixed. Do #N, prove #N, then #N+1. No asking which to start.

| # | task | acceptance (fresh evidence required) |
|---|---|---|
| 1 | ledger attribution: add `venture_id` + `token_cost_usd`, migrate 35 existing rows | per-venture P&L printed for all ventures from the ledger alone |
| 2 | **GATE**: `filter_compiled` + `keep_better` + probation + plist unload + graveyard | deliberately seed a losing venture → observe it auto-killed and its plist unloaded |
| 3 | registry writable: remove the 7-name hardcode, allocator reads dynamic roster | a hand-added row is picked up by `ceo-pass.sh` with no code edit |
| 4 | **INTAKE**: fetchers for IH Firebase / Flippa v3 / TrustMRR / x402 Bazaar | one run emits ≥100 candidates, each with a number and a URL |
| 5 | SCORE + dedup (§8 rules) | zero candidates that duplicate an existing registry/archive entry |
| 6 | `archive/runs.jsonl` | every run writes exactly one row, failures included |
| 7 | `PLAYBOOK.md` append-only + importance-budget reflection trigger | full-rewrite is impossible by construction; counter resets after reflection |
| 8 | **BUILDER**: candidate → skill dir → plist → registry → ledger → seed → start, retry ≤3 with stderr feedback | ★ one new venture goes live with a real side-effect, zero human touches ★ |
| 9 | CURRICULUM `score_child_prop` | 10 consecutive cycles do not all pick the same branch |
| 10 | allocator handles entrepreneur-origin ventures (seed cap + ×1.05/0.95) | a profitable venture's capital rises day over day in the registry |
| 11 | Telegram daily P&L (`ai.anicca.telegram-bot.plist` currently NOT loaded; helper `skills/_shared/send-telegram.sh` exists) | message arrives on Dais's device |
| 12 | repair failing launchd jobs: `life-manager-payout`, `life-manager-x402-ledger`, `life-manager-selfbuild`, `life-manager-dev`, `life-manager-financial-report` (exit 1), `sync-memory` (exit 127) | `launchctl list` shows last-exit 0 for all of them |
| 13 | **14-day unattended run** = §1 `done` | the four numbers in §1, read off the files |

## 10. Failure modes we are pre-committing against

| # | documented failure | our guard |
|---|---|---|
| F1 | long-horizon collapse unrelated to context size ([Vending-Bench, arXiv 2502.15840](https://arxiv.org/abs/2502.15840)) | state lives in files (registry/ledger/archive), never in a conversation |
| F2 | nothing blocks a weak result before release ([autoresearch survey](https://haizhaoyang.github.io/research/autoresearch-survey.html): 56 systems, zero reached multi-project portfolio) | task 2 ships BEFORE task 8 — the gate exists before the builder |
| F3 | adding a manager agent made it worse ([Project Vend 2](https://www.anthropic.com/research/project-vend-2)) | no new supervisory layer; reuse the existing CEO pass |
| F4 | 30% autonomous task-completion ceiling ([TheAgentCompany, arXiv 2412.14161](https://arxiv.org/abs/2412.14161)) | if the gate reverts everything for 14 days, fall back to parameter evolution of existing earners (`skills/earn/self-improve/`) and say so out loud |
| F5 | context collapse from summarizing learnings | PLAYBOOK append-only (task 7) |
| F6 | high-earning agents cheat (Vending-Bench 2 arena: price cartels, refund fraud) | scoring rejects any method whose margin depends on non-delivery; ledger requires a real tx/receipt |

## 11. Revenue path (why this ends at $10M MRR)

`MRR = E × p × L` where E = experiments/week, p = probation pass rate,
L = winner MRR. The builder raises E. Only PLAYBOOK + archive raise p. Only the
§8 scoring bias raises L. Raising E alone burns tokens and returns $0 — that is
the entire content of the F2 finding.

| horizon | expected | binding variable |
|---|---|---|
| month 1-3 | ~20 built, ~19 killed, archive fills | E |
| month 3-6 | p climbs toward ~30% as PLAYBOOK learns what dies | p |
| month 6-12 | scoring rejects gig-shaped work; one venture reaches $1k+/mo | L |
| month 12-24 | allocator compounds capital into the single winner (×1.05/day) | compounding |
| month 24-36 | winner is productized into Life Manager and sold to humans: 10k users × $100/mo = **$10M MRR** | distribution |

$10M does not come from 1,000 small loops. It comes from running experiments
cheap enough that killing 70% is free, then pouring everything into the one
that works. The defensible asset is the kill gate, not the builder.
