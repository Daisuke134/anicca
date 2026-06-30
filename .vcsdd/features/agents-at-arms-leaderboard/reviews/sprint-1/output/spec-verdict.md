# VCSDD Phase 1c Spec-Review Verdict (ROUND 4 / RE-REVIEW) — agents-at-arms-leaderboard

- Feature: `agents-at-arms-leaderboard` (lean mode)
- Review scope: `reviews/sprint-1/` (behavioral spec gate, v4 spec)
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Round: 4 (re-review of the v4 rewrite)
- Timestamp: 2026-07-01
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md` (v4)

## Overall verdict: **FAIL**

v4 is converging — **four of the six round-3 findings are genuinely resolved on disk** (R3-FIND-002,
-003, -004, -005): the served-file producer is now named (R11), the all-unverified headline renders `—`
not `$0` (R4), `revenue_today_usd` is sign/relationally constrained (R9), the `reader` interface is
defined (lines 22-28), `revenue_by_source` is typed (R9), and an `earn_src` indicator is added to the UI
(R6). **But the feature's core guarantee is still not delivered, and v4's new exclusion construct
actively breaks it for the exact population the board exists to rank:**

1. **Anti-buy is still hollow + the new exclude-set is incoherent.** The ranked figure is still raw
   inbound USDC transfers minus a *known* exclusion set, not the design's recorded earn-ledger — so any
   inbound transfer from a non-enumerated wallet (donation/airdrop/fresh sybil wallet) still counts as
   "earnings" (R3-FIND-001, STILL-OPEN). Worse, v4 defines `EXCLUDED_FROM_EARNINGS` as a *checked-in
   constant* that "includes the agent's own id" — impossible for a single static set across many agents —
   so for a hackathon entrant (`id ∉ OUR/SEED`) the entrant's own id is NOT excluded and self-transfers
   DO pump rank (R4-FIND-002, NEW critical).
2. **`net_worth_usd` is not implementable as written** (R4-FIND-001, NEW): the reader returns ETH `wei`
   and USDC `atomic` bigints, the spec sums them as "USD" with no ETH/USD price source and no decimal
   scaling.
3. **A second, deployed producer serves un-verified rankings** (R4-FIND-003, NEW): the live netlify
   `dashboard-sync.js` returns `aggregate(rows)` of raw self-reported figures with no `enrichOnChain`,
   directly contradicting INV-NOFAKE; v4 R11 governs only the Dais-owned render and never reconciles it.

| Dimension | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| 1. Spec Fidelity | FAIL | FAIL | FAIL | **FAIL** |
| 2. Edge Cases | FAIL | FAIL | FAIL | **PASS** |
| 3. Impl Correctness (testability) | FAIL | FAIL | FAIL | **FAIL** |
| 4. Structural Integrity | FAIL | FAIL | FAIL | **FAIL** |
| 5. Verification Readiness | FAIL | FAIL | FAIL | **FAIL** |

---

## Round-3 must-fix disposition (every item re-checked against disk)

| R3 finding | Status in v4 | Evidence |
|---|---|---|
| R3-FIND-001 / -006 (ranked figure un-buyable; anti-buy proof) | **STILL-OPEN (partial)** | v4 excludes self/seed/OUR (`behavioral-spec.md:17-19,44-49`) and adds a self/seed=0 proof (`:87`) — real progress. But the value is still raw inbound USDC transfers (`:26`), not the design's earn-ledger (`design...:64-66`); a fresh attacker-controlled wallet's inflow still counts as "earnings," and the spec falsely calls this "un-buyable"/"earn-ledger inflows" (`:98-101`). The proof only covers known addresses, so it gives false confidence. See R3-FIND-001 (carried) + R3-FIND-006 (carried). |
| R3-FIND-002 (producer writes leaderboard into the SERVED `/dashboard.json`) | **RESOLVED** | R11 names the Dais-owned dashboard-sync render as the writer of the served `apps/landing/public/dashboard.json`, forbids Anicca writing it, and adds an R11 integration proof that the consumed file carries `leaderboard` (`behavioral-spec.md:73-76,95`); header acknowledges the real static file (`:13-14`). |
| R3-FIND-003 (all-unverified `—` not `$0`; constrain `revenue_today_usd`) | **RESOLVED** | R4 makes empty-metric totals `undefined`→`—`, never `0` (`:50-53`); R9 adds `revenue_today_usd ≥0 and ≤ revenue_mo_usd` + `revenue_by_source ≥0` with 1b proofs (`:68,88,93`). |
| R3-FIND-004 (define `reader` interface) | **RESOLVED** (but exposes R4-FIND-001) | Interface defined: `nativeBalanceWei`, `usdcBalanceAtomic`, `externalInflowsUsd`, throw⇒unverified, Base mainnet + USDC contract (`:22-28,20`). Mock is now non-tautological for the inflow path. The `net_worth_usd` USD math it wires to is broken — see R4-FIND-001. |
| R3-FIND-005 (ownership; type `revenue_by_source`; surface `earn_src`) | **RESOLVED** | Owner named (R11 `:73-76`); `revenue_by_source: Record<string,number>` typed (`:68`); `earn_src` indicator in R6 (`:56-60`). (Residual netlify-function reconciliation → R4-FIND-003.) |

---

## Dimension 1 — Spec Fidelity: FAIL

### R3-FIND-001 (critical, CARRIED / STILL-OPEN) — "un-buyable earnings" still reads inbound transfers, not the earn-ledger
- v4 R3 sets `revenue_mo_usd = reader.externalInflowsUsd(id, monthStart, EXCLUDED_FROM_EARNINGS)`
  (`behavioral-spec.md:45-46`), and the reader defines that as *"Σ USDC Transfer(value) to addr where
  from ∉ excludeSet"* (`:26`). The design mandates revenue be computed from *"the on-chain realized-earn
  **ledger** (INV-7 rows from the earn skeleton)"* with *"self-reported numbers … never the ranked
  figure"* (`design...:64-66`). Inbound transfers ⊋ earned money: a donation, an airdrop, or USDC pushed
  in from a fresh wallet the operator controls all count as "earnings."
- The spec then asserts the opposite of what it delivers: INV-NOFAKE calls this *"un-buyable external
  earnings"* and *"earn-ledger inflows"* and states *"Buying rank with your own/seed money is
  impossible"* (`:98-101`). That is true only for the enumerated self/seed/OUR addresses; it is false for
  any non-enumerated wallet. Asserting an impossibility the spec does not deliver is a fidelity defect.
- **Fix**: adopt the design's recorded-earn-ledger (count only provenance-tagged earn events:
  trading/gig/x402/bounty) as the ranked figure, OR downgrade the INV-NOFAKE claim to its true scope
  (self/seed/own only) and document the residual sybil hole. Do not label raw transfers "earn-ledger."

### R4-FIND-002 (critical, NEW) — `EXCLUDED_FROM_EARNINGS` constant cannot exclude an entrant's own id
- v4 defines `EXCLUDED_FROM_EARNINGS` as a **checked-in constant** `Set<string>` =
  `{ the agent's own id } ∪ OUR_INSTANCE_IDS ∪ SEED_ADDRESSES` (`behavioral-spec.md:17-19`), and R3
  passes that single literal to every per-id call (`:46`). One static set cannot hold "the agent's own
  id" for arbitrary agents.
- For a hackathon entrant (`id ∉ OUR_INSTANCE_IDS`, `id ∉ SEED_ADDRESSES` — the precise population the
  board ranks), the entrant's own id is therefore NOT excluded ⇒ self-transfers from its own wallet
  inflate `revenue_mo_usd` and rank. The anti-buy proof (`:87`) can only pass if the test builds a
  per-row set containing `row.id`, which contradicts the constant definition at `:17-19`. Internally
  inconsistent; the core guarantee fails for external entrants.
- **Fix**: compute the exclude set per-row at enrich time — `excludeSet(row) = { row.id } ∪
  OUR_INSTANCE_IDS ∪ SEED_ADDRESSES` (only the latter two are checked-in constants) — and have
  `enrichOnChain` pass `excludeSet(row)` (update `:46`). Use a hackathon-entrant fixture in the 1b proof.

---

## Dimension 2 — Edge Cases: PASS

Positive evidence reviewed on disk:
- All-unverified headline: R4 makes empty-metric totals `undefined`→`—`, never `$0`
  (`behavioral-spec.md:50-53`), with a 1b "all-unverified ⇒ undefined, never NaN" proof (`:88`). Resolves
  R3-FIND-003 part (1).
- `revenue_today_usd` now constrained `≥0 and ≤ revenue_mo_usd`; `revenue_by_source` values `≥0`
  (`:68`), with 1b proofs `today>mtd ⇒ ok:false` and `negative source ⇒ ok:false` (`:93`). Resolves
  R3-FIND-003 part (2).
- Unverified ordering deterministic (`id` asc, never out-ranking verified) (`:42`); empty filtered set →
  explicit empty-state (`:64`).
(Note, non-blocking: the existing schema does not constrain `revenue_mo_usd ≥ 0`
(`telemetry-schema.js:12`), so `today ≥0 ∧ today ≤ revenue_mo` is unsatisfiable if `revenue_mo` is ever
negative; tighten in Phase 2.)

## Dimension 3 — Impl Correctness / Testability: FAIL

### R4-FIND-001 (major, NEW) — `net_worth_usd = usdc + native` is dimensionally meaningless
- R3 computes `net_worth_usd = usdc(id)+native(id) (USD)` (`behavioral-spec.md:47-48`), but the reader
  returns `nativeBalanceWei` (ETH wei, 1e18) and `usdcBalanceAtomic` (6-dec, 1e6) (`:24-25`). Neither is
  USD; there is no ETH/USD price method anywhere, and no decimal scaling is given. Summing a 1e6 bigint
  and a 1e18 wei bigint as "USD" is arithmetically meaningless, and `net_worth_usd` is the R2 ranking
  tie-breaker (`:41`) + a displayed headline — so the value, the RED mock, and the ranking are all
  non-deterministic.
- **Fix**: add `ethUsdPrice()` to the reader (source + throw⇒unverified) and specify
  `net_worth_usd = usdcAtomic/1e6 + (nativeWei/1e18)*ethUsd`, OR scope net worth to USDC-only this slice.

## Dimension 4 — Structural Integrity: FAIL

### R4-FIND-003 (major, NEW) — second deployed producer serves un-verified rankings
- v4 R11 governs only the Dais-owned render (`behavioral-spec.md:73-76`), but the live netlify function
  `apps/landing/netlify/functions/dashboard-sync.js:14` returns `JSON.stringify(aggregate(rows))` of raw
  Supabase rows with **no `enrichOnChain`** — i.e. a public endpoint ranking self-reported, gameable
  `net_worth_usd`/`revenue_mo_usd` (`telemetry-aggregate.js:2-3,10`), exactly what INV-NOFAKE forbids
  (`:98-101`). The spec never says this function is removed, repurposed to enrich, or otherwise
  prevented from serving un-verified rankings — two leaderboard code paths coexist unreconciled.
- Minor compounding: `revenue_by_source` is signed (`:69`), typed (`:68`) and carried (`:38`), and the
  design renders it in drill-down (`design...:78`), but R6's render contract (`:56-60`) never specifies
  rendering it or labelling its self-reported provenance.
- **Fix**: state the netlify function's fate (remove, or run `enrichOnChain` before `aggregate`);
  guarantee a single enriched source; add `revenue_by_source` (with a self-reported indicator) to R6.

## Dimension 5 — Verification Readiness: FAIL

### R3-FIND-006 (critical, CARRIED / STILL-OPEN) — anti-buy proof gives false confidence
- The 1b R3 proof (`behavioral-spec.md:87`) asserts only that a row whose inflows are *self/seed*
  transfers → `revenue=0`. Because the ranked figure is raw inbound transfers (R3-FIND-001) and the
  exclude set cannot contain an entrant's own id (R4-FIND-002), the proof passes while the board remains
  buyable for the population it ranks — a green proof coexisting with a gameable feature is precisely the
  AI-slop failure mode this gate exists to catch.
- **Fix**: once R3-FIND-001/R4-FIND-002 are fixed (earn-ledger and/or per-row exclude set), add a 1b
  proof with a *hackathon-entrant* fixture (`id ∉ OUR/SEED`) whose only inflows are its own/fresh-wallet
  transfers, asserting `revenue_mo_usd` does NOT increase and rank does NOT move.

---

## Must-fix before Phase 2 (RED) — load-bearing only
1. **R4-FIND-002 + R3-FIND-001/-006**: make the exclude set per-row (`{row.id} ∪ OUR ∪ SEED`) AND base
   the ranked figure on the design's recorded earn-ledger (or downgrade the "un-buyable" claim to its
   true self/seed/own scope and document the residual sybil hole). Add a hackathon-entrant anti-buy proof.
   This is the feature's entire point and is still gameable for external entrants.
2. **R4-FIND-001**: make `net_worth_usd` implementable — add an ETH/USD price method + explicit decimal
   scaling, or scope net worth to USDC-only this slice.
3. **R4-FIND-003**: reconcile the live netlify `dashboard-sync.js` (which serves un-enriched, self-reported
   rankings) with the Dais-owned enriched render; ensure a single enriched leaderboard source.
