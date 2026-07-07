# Phase 1c Spec Review — anicca-agent-economy — iteration 2

**Verdict: FAIL**

## What was checked

Fresh-context, disk-only re-review of `specs/behavioral-spec.md` and
`specs/verification-architecture.md` (revision "iteration 2"), specifically against iteration-1's
six findings (FIND-001..FIND-006), plus a fresh full-spec pass looking for new issues introduced by
the revision. Every claim the revised spec makes about the current on-disk codebase was
re-verified by directly reading the referenced files:

- `/Users/anicca/anicca/skills/economy/gig/lib/lock.mjs`
- `/Users/anicca/anicca/skills/economy/gig/__tests__/lock.test.mjs` (structure only, not re-read
  line by line this pass — FIND-004's resolution is at the spec-text level, not test-file level)
- `/Users/anicca/anicca/runtime/loop/liquidity.mjs`
- `/Users/anicca/anicca/runtime/loop/prompt.mjs` (full file)
- `/Users/anicca/anicca/runtime/loop/context.mjs`
- `/Users/anicca/anicca/runtime/loop/tier.mjs`
- `/Users/anicca/anicca/runtime/loop/index.mjs` (registry read, balance fetch, positionsSummary
  computation, context assembly — lines ~100-263)
- `/Users/anicca/anicca/skills/registry.json` (all 18 slot entries)
- `/Users/anicca/anicca/skills/earn/hl-trade/hl.py`
- `/Users/anicca/anicca/skills/earn/run.sh`

## iteration-1 findings: resolution status

| Finding | Status | Basis |
|---|---|---|
| FIND-001 (missing BOOTSTRAP_RESERVE_USDC default) | **RESOLVED** | Literal default `20` now documented, `Number(process.env.X) \|\| 20` idiom matches the verified `COMPUTE_RESERVE_USDC` pattern in `context.mjs:39` (default `5`). Ordering invariant (`20 >= 5`) is explicit. |
| FIND-002 (no signal to distinguish always-available from risky) | **RESOLVED** | New, independent `alwaysAvailableOf(slotName)` input added to `filterCatalog`'s signature with explicit unconditional precedence. `sleep`'s independence re-verified directly against `prompt.mjs::getToolDefinitions` (unconditionally appends `SLEEP_TOOL`). |
| FIND-003 (hl_trade close-position deadlock vs. liquidityDirective) | **PARTIALLY RESOLVED — reopens as FIND-102** | The deadlock is correctly *narrated* and the carve-out mechanism (`hasOpenRiskPositionOf`) is a sound *design*, but its stated data source ("already-fetched... same bookkeeping that populates `ctx.positionsSummary` today") is factually false — see FIND-102. |
| FIND-004 (isLockStale extraction not binding) | **RESOLVED** | REQ-101 now contains an explicit BINDING clause; a Phase 3 adversary finding the comparison still inlined must fail REQ-101 regardless of integration test results. |
| FIND-005 (prompt.mjs baseline mischaracterized as "you decide") | **RESOLVED** | Re-read the actual file; the spec's quoted baseline text is accurate at the cited lines. New REQ-204 requires retiring the block; PROP-203b/PROP-204a now mandate a full-file read, not diff-only. |
| FIND-006 (round-3 self-report accepted as Tier 3 proof) | **RESOLVED** | REQ-103 and PROP-103b/the Gate section now explicitly forbid accepting the same-builder, same-day self-report as satisfying the Tier 3 obligation; independent re-execution is now binding. |

Five of six prior findings are genuinely, substantively resolved — not reworded. FIND-003's
underlying design intent is preserved, but re-verification against the real codebase surfaces a
new, concrete defect in how the fix's data dependency is characterized (FIND-102).

## New findings (this iteration)

### FIND-101 (spec_fidelity, critical) — registry fail-closed default contradicts REQ-201's own worked example

REQ-201's EARS clause and worked example require `economy/gig`, `economy/ubi`, `self/*`, and
`report` to remain visible to a broke instance. Its own edge case makes the opposite the binding
default: an untagged live slot in `registry.json` is treated as capital-risking and excluded. The
real, current `registry.json` has **zero** risk/alwaysAvailable tags on any slot — including
`economy/gig` itself. Only `report`/`cook` get the new `alwaysAvailable: true` carve-out anywhere
in the spec. A Phase 3 implementation that satisfies every stated acceptance criterion literally
would hide `economy/gig` (the feature's own headline $0-capital bootstrap mechanism) from every
broke instance the moment this gate ships — directly contradicting the requirement's own intent.

### FIND-102 (verification_readiness, critical) — hasOpenRiskPositionOf's "already-fetched" data does not exist

Both `behavioral-spec.md` and `verification-architecture.md` assert `hasOpenRiskPositionOf` reads
data "the same underlying position bookkeeping that populates `ctx.positionsSummary` today." Direct
inspection of `index.mjs`'s `positionsSummary` computation shows it filters ledger entries to
`source.startsWith('yield')` only — `hl_trade` ledger entries (`source: 'hl-trade'`, verified in
`skills/earn/run.sh`) are structurally excluded. The only code that knows live HL position state is
a real Hyperliquid API call inside `hl.py`, not wired anywhere into the wake loop's context
assembly. This is a brand-new, unspecified live-I/O dependency with a completely unaddressed
failure mode (fail-open defeats the gate; fail-closed can reopen the exact deadlock FIND-003's
carve-out claims to close).

## Dimension verdicts

| Dimension | Verdict | Findings |
|---|---|---|
| spec_fidelity | FAIL | FIND-101 |
| verification_readiness | FAIL | FIND-102 |

**Overall verdict: FAIL** (2 new blocking critical findings; route both to Phase 1a/1b for a third
revision).
