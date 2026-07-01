# VCSDD Phase 1c Spec-Review Verdict — eval-driven-earning (iteration 2, lean)

**OVERALL VERDICT: FAIL**

Fresh-context adversary, disk-only, re-review of commit `16ec1cc`. The 13 iteration-1 findings
are substantively resolved; 3 NEW/residual findings remain (2 high, 1 medium). Round 2 of 3 (lean).

## Dimension verdicts

| dimension | verdict | findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-015 |
| edge_case_coverage | FAIL | FIND-016, FIND-015 |
| implementation_correctness | PASS | — (positive evidence recorded) |
| structural_integrity | FAIL | FIND-014 |
| verification_readiness | FAIL | FIND-014 |

## Iteration-1 fix verification (each fix confirmed REAL against disk)

| iter-1 finding | claim | verdict | evidence |
|---|---|---|---|
| FIND-001 | INV-7 dangling ref → INV-8 | RESOLVED | INV-7 has 0 matches in specs; INV-8 cited at behavioral-spec.md:54,70,80,171-173; INV-8 is the real skeleton settled-payout gate (skeleton line 54, enforced REQ-B3 line 216) |
| FIND-003 | survival ADVISORY; B4 sole kill-switch owner | RESOLVED | REQ-S5 (255-288): appends only to lessons.jsonl; "SHALL NOT independently write loop.disabled or call self-recover.sh survival-bankruptcy. There is NO survival-bankruptcy Group-J handler." Skeleton REQ-B4 confirmed sole owner |
| FIND-002 | income normalized to income_usd (JPY/FX + USDC) | RESOLVED | REQ-S2(c):173 `income_usd=(cumulative_jpy_earned/FX)+cumulative_usdc_earned`; income_usdc/net_usdc/cost_usdc = 0 matches; mixed-currency acceptance ¥1500+0.5USDC→10.5 (197-199) |
| FIND-004 | cost_usd no double-FX; correct acceptance | RESOLVED | REQ-S1(d):135-139 tokens×USD-rate/1e6, no FX; acceptance 13500/1e6=0.0135 USD (157); REQ-S2(b) JPY/FX path consistent (skeleton stores token_cost_jpy=USD×FX) |
| FIND-005/006 | decideActivity pure, injected BanditStats, deterministic epsilon-greedy, no RNG/file | RESOLVED | REQ-DA1:372-396 injected BanditStats; "Thompson" mislabel removed (REQ-M2:334); NFR-ED1:846-850 + anti-slop 5b/5c ban os/subprocess/random/open in eval_spine.py |
| FIND-008 | rubricScore has verifiable_result precedence | RESOLVED | REQ-EV1:494-531 5-param signature + precedence order; PROP-EV3/EV3f (verification 81-82) test rubricScore directly, phantom rubricEval gone |
| FIND-009 | curation does a REAL payout_api_check probe | RESOLVED (mitigated) | REQ-CU3(a):713-720 real HTTP probe, missing field → FAIL, unreachable → FAIL, allowlist-membership criterion; residual "reachable≠earns" is backstopped by skeleton REQ-G2 3-check runtime gate before any earnings.jsonl append |
| FIND-010 | trading-polymarket not grandfathered; null admitted_at_ts blocks exploit | RESOLVED (but see FIND-015) | EDGE-M1a:309-315 removes trading-polymarket from bootstrap; REQ-DA2:406-411 makes null admitted_at_ts NEVER exploit-eligible, novelty_tried conjunction dropped |
| FIND-007 | 1a/1b signature drift | RESOLVED for function signatures | verification 29-32 aligns all 6; BUT menu.json schema field names still drift → FIND-014 |
| FIND-011 | alpha cap contradiction | RESOLVED | REQ-M2(a):331 clip(...,0,1) is the canonical definition; EDGE-M2a:352-354 subsumed |
| FIND-012 | window_secs unimplementable | RESOLVED | calibrationDrift(scores,realized_usd,min_pairs) — window_secs dropped; EDGE-X3:884-888 windowing caller-side |
| FIND-013 | test asserted 10/10 exploit vs mandatory explore quota | RESOLVED | verification 189-191: "arm-B in ≥9 of 10" + "≥1 of 10 mode==explore"; bandit_stats updated in-loop |

## NEW / residual findings (open)

- **FIND-014 (high, structural_integrity + verification_readiness).** Currency rename is
  INCOMPLETE — the FIND-007 drift class is re-opened. The canonical MenuEntry schema still uses
  the old `_usdc` suffix for three fields while every consumer uses the new `_usd` name:
  `expected_usdc_per_wake` (schema 98/110, REQ-M1 302/323) vs `expected_usd_per_wake`
  (REQ-M2 342, REQ-DA1 396, REQ-DA2 407/423, PROP-DA5, PROP-M4, integration test 181-198);
  `cost_estimate_usdc` (schema 104, REQ-DA4 464) vs `cost_estimate_usd` (EDGE-DA2b 418,
  EDGE-DA3a 449, REQ-CU3 737); `realized_usdc` (schema 102/111, verification E2E 231) vs
  `realized_usd` (REQ-M2, REQ-EV4). The JSON-Schema validation test and the pure-function
  property tests would bind DIFFERENT field names for the same quantity → unbuildable.

- **FIND-015 (high, spec_fidelity + edge_case_coverage).** EDGE-X2's null-admitted backstop
  contradicts the EDGE-M1a cold-start path introduced by the FIND-010 fix. EDGE-M1a
  bootstraps a new slot with the 4 default earn types all `admitted_at_ts=null` (reachable only
  via explore), but EDGE-X2 (878-882) unconditionally excludes ANY null-admitted pick and
  re-runs. On a fresh slot where every entry is null-admitted, each explore pick is excluded
  until the menu empties → `discover-first` radar sentinel → the slot never executes its own
  bootstrap earn types. EDGE-X2 excludes exactly the entries EDGE-M1a relies on; the spec never
  scopes EDGE-X2 to exploit-only. Cold-start liveness is unresolved.

- **FIND-016 (medium, edge_case_coverage).** EDGE-DA3b (450-452) is self-contradictory: it
  states `explore_due=True` while its own shown computation yields False, and recommends
  "use ceiling" against REQ-DA1's canonical `floor()` quota (393) and the DA3 acceptance
  criterion (457-458). floor-vs-ceil is left unresolved despite the spec's claim of a fully
  deterministic pure decision rule.

## Targeted hunt results (per manifest questions)

- **FIND-002 currency** — income_usd normalizes JPY(/FX)+USDC; no `_usdc`-only income remains. RESOLVED.
- **FIND-004 cost** — no double-FX; REQ-S1 direct-USD and REQ-S2 JPY/FX paths are consistent. RESOLVED.
- **FIND-001/003 survival ADVISORY** — INV-8 anchored, advisory-only, B4 sole `loop.disabled` owner, no invented handler. RESOLVED.
- **FIND-005/006 decideActivity pure** — injected BanditStats, deterministic epsilon-greedy, no RNG/file. RESOLVED (but EDGE-DA3b text garbled → FIND-016).
- **FIND-010 trading-polymarket** — removed from bootstrap; null admitted_at_ts blocks exploit permanently. RESOLVED (but EDGE-X2/M1a contradiction → FIND-015).
- **FIND-008/009 rubricScore + curation probe** — verifiable_result precedence in the pure fn; REAL payout_api_check reachability probe + allowlist + adversary. RESOLVED (reachable≠earns backstopped by skeleton REQ-G2).

## Gate outcome

Spec is NOT ready for Phase 2. Route FIND-014/FIND-015/FIND-016 back to Phase 1a (schema field
rename completion + EDGE-X2/EDGE-M1a reconciliation + EDGE-DA3b floor/ceil correction). All three
are localized, mechanical fixes. Re-review required (lean: round 3 of 3 remaining).
