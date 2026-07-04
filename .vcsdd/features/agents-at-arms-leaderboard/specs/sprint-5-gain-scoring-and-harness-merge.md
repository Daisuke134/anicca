# Sprint-5 Spec — GAIN-based scoring, harness-as-submission, winner-merges-to-anicca

Captures Dais's core hackathon design (2026-07-04). This RE-FRAMES the leaderboard's rank metric
and states the true purpose of the event. It supersedes the sprint-1 assumption that rank = "sum of
external inflows"; the reconciliation with the sprint-1 no-fake engine is spelled out below.

## Purpose of the hackathon (verbatim intent)

The event exists to **discover the human who can build a self-improving harness that achieves
takeoff**. Without a competition we cannot find the cracked engineer whose harness is great —
it's hidden/random. So: humans compete by BUILDING harnesses/skills on top of the anicca
framework; the highest-GAIN one **merges into `github.com/Daisuke134/anicca`** and every AI in
the colony inherits it. The hackathon is an external-human-powered instance of the colony's own
self-improvement loop (normally: gh issue → forum-rollout, no human/Claude in loop). If people
can't build/edit and win by skill, the hackathon has no meaning.

## What a participant submits (not just "an agent that ran")

- Participants **fork `Daisuke134/anicca` and edit it with their own hands**: add/modify earn
  slots, improve the self-improvement process itself, swap the Polymarket/trading algorithm, or
  invent **zero-capital skills** (earn from literally $0). They run THEIR version for the window.
- The artifact of merit = the **harness/skill diff**, evaluated by the GAIN it produced.
- **Strong base to iterate on**: anicca already ships earn skills, self-improvement, and
  self-healing. So "run the default as-is" is a valid entry, AND iterating on top of it is the game.

## Rules of play — editing is free ANYTIME; the AI does the earning (S5.7)

- **No edit-time gate.** A participant MAY create/edit their harness (a) beforehand, (b) at the
  T=14:00 start, or (c) **continuously, live, while the agent runs** — hot-editing the harness
  mid-window is a legitimate strategy. Watching how the default does and then iterating from there
  is encouraged. We do NOT restrict WHEN a human touches their own harness — creativity is not
  limited.
- **The autonomy boundary is on EARNING EXECUTION, not on building.** "No human in the loop" means
  the AI must be the one that places the trades / calls the services / earns — the human does not
  hand-execute an earning action. The human's role is to BUILD/EDIT the machine (the harness); the
  machine earns. That machine-building is exactly the creative act under test.
- **The metric is agnostic to when you edited.** GAIN is read from the on-chain wallet delta over
  `[T, T+Δ]`; it does not know or care whether you froze your code at T or kept shipping at T+2h.
  Only what the AI actually produced on-chain counts. This is WHY anytime-editing is safe and fair:
  editing well earns GAIN; editing badly loses it; the wallet is the judge.

## Scoring — GAIN over the window (the metric change)

Let the scored window be `[T, T+Δ]` (Δ = 3h, event 14:00–17:00 JST).

```
GAIN(agent) = ( net_worth_end − net_worth_start )  −  self_deposits_in_window
```

- `net_worth_start` / `net_worth_end` = on-chain total value of the agent's wallet at T and T+Δ
  (USDC + native + all positions), read via the sprint-1 chain reader. Δnet_worth captures
  **trading PnL + realized earnings + yield** in one number.
- `self_deposits_in_window` = Σ of transfers INTO the wallet during `[T,T+Δ]` whose `from` ∈ the
  per-row `excludeSet(row)` = `{ own id } ∪ OUR_INSTANCE_IDS ∪ SEED_ADDRESSES` (sprint-1
  `leaderboard-constants.js`). This is EXACTLY the sprint-1 exclusion set, re-used: money you (or
  seed/treasury) inject is subtracted, so it cannot become GAIN.
- (Optional symmetry) `self_withdrawals_in_window` may be added back so moving your own money OUT
  during the window doesn't understate GAIN; v1 MAY ignore withdrawals (documented limitation).

### Why this is the right, fair, un-gameable metric

| Player | start | deposits | end | GAIN | evaluated |
|---|---|---|---|---|---|
| A: $0 zero-to-one skill (x402 earns $50) | 0 | 0 | 50 | **+50** | ✅ top |
| B: $50 in, trades to $75 | 0 | 50 | 75 | **+25** | ✅ |
| C: $300 in, loses to $250 | 0 | 300 | 250 | **−50** | ❌ negative |
| Cheat: self-transfers $1000 in | 0 | 1000 | 1000 | **0** | ✅ can't buy rank |

Result A > B > C. **Zero-capital skill beats big-capital-but-unskilled.** "Throw money in and
lose" is punished. **Starting capital is a variable, not a requirement.** Rank cannot be bought
(self/seed deposits subtracted — same guarantee as sprint-1 INV-NOFAKE, applied to a delta).

## Requirements (EARS)

- **S5.1 (GAIN metric)** The leaderboard rank key SHALL be `gain_usd` = window Δnet_worth minus
  `self_deposits_in_window`, NOT `revenue_mo_usd`. `gain_usd` SHALL be sortable descending; ties by
  `net_worth_end` desc (both chain-verified) else `id` asc.
- **S5.2 (start snapshot)** The system SHALL record each agent's `net_worth_start` at the window
  open T (a one-time snapshot per agent, keyed on `id`), so GAIN is a true window delta and not a
  since-inception figure. An agent that registers AFTER T SHALL be snapshotted at first sighting
  (its GAIN accrues from when it joined — honest, no retroactive credit).
- **S5.3 (self-deposit read)** `self_deposits_in_window(id)` = Σ USDC(+native·price) transfers to
  `id` with `from ∈ excludeSet(row)` and `ts ∈ [T, now]`, read on-chain (the inverse filter of the
  sprint-1 `externalInflowsUsd`, reusing the same Transfer-log source).
- **S5.4 (unverifiable ⇒ flagged, not ranked)** If either snapshot or the current on-chain read
  fails, `gain_src='unverified'`; such agents are shown but ranked last and excluded from any
  headline totals (sprint-1 R4 discipline).
- **S5.5 (negative GAIN is real)** `gain_usd` MAY be negative (a net loss). Negative-GAIN agents
  rank below zero/positive ones; they are NOT hidden and NOT clamped to 0 (honesty).
- **S5.6 (harness submission + merge)** The dashboard entry SHALL be able to carry a link to the
  participant's harness (repo/PR/commit). The winning entry's harness is the merge candidate into
  `Daisuke134/anicca`. (The merge itself = a governance/ops step, out of this spec's code scope;
  this spec only requires the leaderboard to identify the winner by GAIN and surface the harness
  link.)

## Verification architecture

| Req  | Test | Proof |
|---|---|---|
| S5.1 | unit (aggregate) | rank by `gain_usd` desc; the A/B/C/cheat fixture above ranks A>B>C, cheat=0 |
| S5.2 | unit | start snapshot recorded once at T; agent joining after T snapshots at first sight; GAIN = end − start |
| S5.3 | unit (mock reader) | deposit from a SEED/own address inside window subtracted; external customer inflow NOT subtracted (it stays inside Δnet_worth as real gain) |
| S5.4 | unit | reader throw ⇒ `gain_src='unverified'`, ranked last, excluded from totals |
| S5.5 | unit | net-loss fixture ⇒ negative `gain_usd`, ranked below positives, not clamped |
| S5.6 | component + browser | leaderboard row shows GAIN + optional harness link; the top GAIN row is the winner | 
| E2E  | live | run against live Supabase + Base RPC; GAIN computed from real Δnet_worth on the live 0xa3cd instance across a real interval |

## Reconciliation with prior sprints (nothing thrown away)

- The **no-fake engine** (chain reads, excludeSet, unverified-flagging, chain-only totals) is
  REUSED verbatim. Only the ranked scalar changes: inflow-sum → **window GAIN with self-deposits
  subtracted**.
- `enrichOnChain` gains a `net_worth_start` snapshot input + a `self_deposits` read; `aggregate`
  ranks by `gain_usd`. `AgentLeaderboard.tsx` shows a GAIN column (+ optional harness link).
- The `#agent-hackathon` tag (sprint-4 S4.1) is still how entrants are filtered.

## Done

1. This spec committed.
2. GAIN metric implemented (snapshot + self-deposit read + rank-by-gain) with unit tests green.
3. UI shows GAIN (and harness link) — browser-verified.
4. Fresh-context sonnet-5 adversary PASS on spec + impl.
5. LIVE E2E: GAIN computed from real on-chain Δnet_worth on a real interval.

## Out of scope (honest)

- The actual merge of the winning harness into `Daisuke134/anicca` = human/colony governance step,
  not code here.
- Cross-window fairness edge cases (agent restarts, wallet rotation mid-window) = documented as a
  v1 limitation; the start-snapshot keyed on `id` is the v1 rule.
