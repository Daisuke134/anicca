# Iteration-3 Fix Note — eval-driven-earning spec

Builder: VCSDD Builder (Claude claude-sonnet-4-6)
Round: 3 of 3 (lean)
Based on: iteration-2 verdict `16ec1cc`, FIND-014/FIND-015/FIND-016

## Fixes applied

### FIND-014 (high) — Currency rename complete; MenuEntry schema now consistent with all consumers

All three `_usdc`-suffix MenuEntry schema fields renamed to `_usd` in both spec files:

| old field | new field | locations patched |
|---|---|---|
| `expected_usdc_per_wake` | `expected_usd_per_wake` | behavioral-spec.md lines 98, 110, 302, 323 |
| `cost_estimate_usdc` | `cost_estimate_usd` | behavioral-spec.md lines 104, 464 |
| `realized_usdc` | `realized_usd` | behavioral-spec.md lines 102, 111; verification-architecture.md line 231 |

Post-fix grep confirms 0 remaining `expected_usdc_per_wake`, `cost_estimate_usdc`, or
`realized_usdc` occurrences in either spec file. Schema, all REQ/EDGE references, all PROPs,
and the E2E verification step now use the same `_usd` names.

Fields NOT renamed (skeleton fields, unrelated to MenuEntry):
`cumulative_usdc_earned`, `amount_usdc` — these are skeleton cumulative.json / earnings.jsonl
fields that are intentionally different from MenuEntry fields.

### FIND-015 (high) — EDGE-X2 scoped to exploit path only; cold-start liveness restored

EDGE-X2 (behavioral-spec.md, cross-cutting section) rewritten to scope the null-admitted
backstop guard to `mode="exploit"` picks ONLY. Key clarifications added:
- EXPLORE picks with `admitted_at_ts=None` are NORMAL intended behavior (the cold-start
  bootstrap path EDGE-M1a depends on).
- proactive-loop.sh checks `admitted_at_ts` ONLY when `mode="exploit"`; explore picks bypass
  this guard entirely.
- On a brand-new slot (all entries null-admitted), REQ-DA1 step 4 always returns `mode="explore"`
  (no arm has attempt_count >= K_MIN_EXPLOIT), so EDGE-X2 is never triggered.
- No path deploys real capital on a null-admitted entry: REQ-DA2 gates exploit on non-null
  `admitted_at_ts`, and EDGE-X2 is the defensive backstop for that same exploit path only.

### FIND-016 (medium) — EDGE-DA3b self-contradiction removed; floor() is canonical throughout

EDGE-DA3b (behavioral-spec.md, REQ-DA3 edge cases) rewritten:
- Shows the correct arithmetic: `floor(0.1 × 1) = floor(0.1) = 0`, so `explore_due = (0 < 0) = False`.
- States clearly that the quota check does NOT trigger explore on wake 1.
- Explains that REQ-DA1 step 4 (all arms unproven) is the mechanism that guarantees explore on
  wake 1 — independently of the quota.
- Removes the self-contradictory "explore_due = True" claim and the ceiling recommendation.
- `floor()` is confirmed as the only formula; the acceptance criterion at line 462 already uses
  floor() consistently and is unchanged.

## Unchanged

All 13 iteration-1/2 fixes remain intact. No spec sections outside the three targeted locations
were modified.
