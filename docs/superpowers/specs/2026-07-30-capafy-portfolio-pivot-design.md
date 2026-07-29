# Capafy portfolio pivot — from one-shot doc writers to recurring-input subscriptions

**Date**: 2026-07-30 · **Status**: prompt/criteria changes SHIPPED, revenue effect UNPROVEN until the
next loop pass · **Scope**: file/prompt work only (no browser, no live-listing edits, no loop run)

---

## 1. Problem statement (one line)

Our 27 live Capafy listings are generic **one-shot B2B document writers**; a one-shot document has no
reason to renew a weekly subscription, so the catalog is structurally unable to earn — independent of
copy quality, price, or icon.

## 2. Measured evidence (live marketplace parse, 2026-07-30)

| dimension | measured value | implication |
|---|---|---|
| distribution | top 1 listing = **57% of all 4,889 sales**; top 5 = **79%** | winner-take-most; being "present" earns $0 |
| median listing | **11 sold**; 33 of 70 listings under 10 sold | the tail is the default outcome |
| winning verticals | **recurring-event data**: football fixture analysis (2,788 sold @ $99.99/yr), stock tracking ($9.99/wk, 781 sold), X/KOL tracking, video generation ($9.99/wk) | recurrence, not sophistication, is the driver |
| winning price | **$9.99/week** (modal); $1.99/day (runner-up) | short paid cycles |
| platform floors | $2/day · $5/week · $8/month | never price below |
| fee structure | publisher earnings = `(price − sandbox fee) × 0.80`; sandbox On-Demand $2/mo · $0.50/wk · $0.07/day | net math below |
| free trial | **36 of 70** listings by count, **ZERO** of the ≥100-sold tier | trial-on-front-door = long-tail marker |
| winning copy | **named-expert proof line** ("500M views", "10+ yrs HR", "ex-McKinsey") | credibility anchor required |
| packaging | closed-source **Subscription** beats **Download** | Download hands the buyer our source |
| ★ our 27 listings | performance-review-writer, esg-compliance-scoper, sales-objection, job-description-writer … **all `recentSales=0`, marketplace CVR 0.00%** | the defect is the SHAPE |

## 3. The renewal test (the actual gate, as shipped)

Both halves must be true **before a single file is written**:

- **(R1) RECURRING INPUT** — the buyer holds a **new instance of the input on a fixed daily/weekly
  schedule** and pastes it in themselves. The subject is a repeating **event** or a moving **number**:
  this week's fixtures + team news, today's positions/watchlist, this week's KOL/timeline posts, this
  week's ad-performance export.
- **(R2) STALE-IN-A-WEEK OUTPUT** — last cycle's output is worthless to them this cycle.

Then, literally: **"On day 8, why has this buyer NOT cancelled?"** The only passing answer is *"a new
event/number happened and last week's output is now stale."* Anything shaped like *"they might need
another one someday"* is a **FAIL** → discard the idea. **Copy never rescues a broken shape.**

**★ HARD REJECTION** — one-shot document generators are forbidden: performance review, job
description, resume, ESG scoping memo, sales-objection sheet, policy, business plan, board deck,
speech, or any document needed once per person/company.

### Why this is honest inside a pure-LLM sandbox (the §6 reconciliation)

The measured winners *frame* themselves around live data, which `lint_listing.py` correctly blocks
(the C4 rejection). The resolution: **the buyer supplies the freshness.** We sell the recurring
**analysis** of data the buyer pastes each cycle — never a fetch, never "live"/"real-time"/"retrieval".
This keeps the recurring-revenue shape and the honesty rules simultaneously satisfied. It is the
load-bearing insight of the pivot; a generated skill that instead claims to *pull* the recurring data
will be rejected at audit.

### Few-shot examples baked into the prompt

| verdict | niche | reason |
|---|---|---|
| ✅ | Football fixture/matchup analysis | new matchday weekly; last week's read dies at the whistle (2,788 sold) |
| ✅ | Stock / portfolio position review | buyer pastes today's positions; numbers move daily (781 sold @ $9.99/wk) |
| ✅ | X / KOL post tracking | buyer pastes this week's timeline; last week's narrative is gone |
| ❌ | `performance-review-writer` (ours) | reviews happen 1–2×/yr; the review is a durable artifact — `recentSales=0` |
| ❌ | `esg-compliance-scoper` (ours) | CSRD scoped once, memo valid a year; big TAM, zero renewal reason — `recentSales=0` |

## 4. Packaging defaults (SSOT = `~/.openclaw/skills/capafy-autopublish/references/pricing.md`)

| knob | default | source |
|---|---|---|
| mode | closed-source `run_online` **Subscription** (never Download) | measured: Download hands over source, ends the relationship |
| plans | **ONE paid `week` plan** | measured modal shape |
| price | **$9.99 / week** | modal winning price |
| cap | **20 / week** | profitability constraint below |
| trial | **No Free Trial** (explicit choice, keeps CP1 price tab green) | 0 of the ≥100-sold tier use a trial |

**Net math**: `(9.99 − 0.50) × 0.80 = $7.592/week` → **≈ $32.9 net per subscriber per month**
(×4.333 wk/mo). Note: the brief's `$32.87` implies ≈4.3296 wk/mo; either convention lands on the same
subscriber count.

**$10k/month target** ⇒ `10,000 / 32.9 ≈ **304 concurrent weekly subscribers**` (equivalently
$10,000 / $32.87 = 304). At the measured median of 11 sold per listing that is unreachable by volume
of listings; it requires **one listing in the winner tier**, which is why the gate is a hard reject
rather than a preference.

**Cap profitability constraint** (kept from the prior SSOT, re-plugged):
`(API cost/call × cap) + sandbox fee ≤ cyclePrice × 0.80 / 2`
→ default: `(0.12 × 20) + 0.50 = $2.90 ≤ $4.00` ✅ (~2.6:1). Cap 40 = `$5.30 > $4.00` ❌.

## 5. Listing-copy requirements (SSOT = `references/agent_card_templates.md`)

1. **Keyword-first title** — open with the subject noun a buyer would type/scan, then em-dash benefit,
   ≤50 chars. `Football Match Analyst — Weekly Fixture Read` ✅ / `Ocup Analysis` ❌.
2. **Credibility proof line** — one concrete, **checkable** anchor in the first two lines of
   shortDescription. ★ It must be TRUE: inventing a credential/employer/view-count/conversion-lift is
   a §6 honesty violation the linter cannot catch. Allowed, in order: (a) the named method/framework
   the skill actually applies, (b) a real countable property of the output, (c) a real number from our
   own verified records.
3. **A renewal section** in detailedDescription ("Every week / Every day") stating what new input
   arrives each cycle and why last cycle's output is stale.

## 6. How the next skill gets chosen (demand data, not guesses)

```
sales_selector.py  ──signal=sales──▶ build next in OUR proven winner category
        │
        └──signal=none──▶ measured marketplace sold-counts (BEST_PRACTICES §10–§13)
                             │
                             ▼
              rank candidates by observed demand (sold counts / price / recurrence)
                             │
                             ▼
              RENEWAL GATE (R1/R2/day-8) applied by the model, per candidate
                             │
              PASS ──▶ highest-demand recurring-input vertical NOT already in our catalog
              FAIL ──▶ discard, next candidate
```

Recorded in the LISTING.md internal notes (required block, above `## Title`, never submitted):

```
RENEWAL GATE (§1b)
R1 recurring input : <what the buyer pastes, and on what schedule a NEW one exists>
R2 staleness       : <why last cycle's output is worthless this cycle>
day-8 answer       : <the one-sentence reason this buyer has not cancelled>
demand evidence    : <the measured vertical / sold-count / winner id this is derived from>
```

**If `demand evidence` cannot be filled with a real observed number, the niche is a guess → pick
another.** Judgment stays in the model: **no regex/keyword allowlist of "good niches" was added**, and
none may be (per `building-agents`). The gate is criteria the model applies, and `niche_picker.py` does
not exist and must not be resurrected.

## 7. Files changed

| file | change |
|---|---|
| `~/anicca/skills/self/capafy-loop/capafy-loop-daily.sh` (PROMPT, L17) | renewal gate + hard rejection + demand-ranked selection + packaging/copy defaults injected into the DESIGN step; kept model-agnostic |
| `~/.openclaw/skills/capafy-autopublish/BEST_PRACTICES.md` | new §1b RENEWAL TEST + few-shots; §0 gate ordering; §2 pricing default; §3 trial default; §7 copy requirements; §8 required gate block; new §13 measured evidence |
| `…/references/pricing.md` | rewritten SSOT: $9.99/wk closed-source sub, cap 20, no trial, floors, net math, $10k arithmetic |
| `…/references/agent_card_templates.md` | keyword-first title + checkable credibility proof line + renewal section |
| `…/SKILL.md` | renewal test section, recipe step 0 (gate + demand ranking), stale canonical-path/niche_picker lines corrected |
| `…/DAILY_LOOP.md` | drainer step 4 fails closed on missing gate block / one-shot shape / packaging mismatch |

**Not touched** (owned by other tasks): `drive_checkpoint2.py`, `inventory_status.py`, orphan/CP2
logic, `scripts/daily_loop.sh` (had an unrelated pre-existing local modification — left uncommitted),
and every live listing.

## 8. Verification status

| check | result |
|---|---|
| `bash -n capafy-loop-daily.sh` | rc=0 |
| PROMPT re-parsed from the file, key phrases asserted present | RENEWAL GATE / R1 / R2 / day 8 / one-shot FORBIDDEN / recentSales=0 / 9.99/week / No Free Trial / NEVER Download / KEYWORD-FIRST / CREDIBILITY PROOF LINE / DEMAND DATA — all PRESENT; PROMPT_LEN=9878 |
| model-agnostic scan of the PROMPT (Opus/Sonnet/GPT/Claude/Gemini/Grok) | no model name present |
| markdown edits | re-read in place; §1b, §13, few-shots, counter-examples confirmed present |

**UNPROVEN until the next loop pass**: that the loop actually obeys the gate; that a generated
recurring-input listing lints clean under §6 and survives Capafy audit; and above all that any of this
produces a sale. No listing was created, repriced, submitted, or run for this change. The next
`ai.anicca.capafy-loop-daily` pass is the first real evidence.

## 9. Known baseline (pre-existing, not introduced here)

- `~/.claude/skills/capafy-autopublish` does not exist though `SKILL.md` claimed it was canonical
  (corrected in this change; single SSOT = `~/.openclaw/skills/capafy-autopublish`).
- `POST /agent/agents/search` is server-broken, so marketplace demand data comes from the recorded
  sweeps (§10–§13), not a live ranking endpoint.
- `scripts/daily_loop.sh` carries an unrelated uncommitted local modification from another task.
