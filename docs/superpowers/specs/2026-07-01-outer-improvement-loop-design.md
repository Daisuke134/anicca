---
title: Outer Improvement Loop (OIL) — the discovery layer that VCSDD is not
status: DRAFT — awaiting Dais decision after comparing with other agent's research
mode: lean
created: 2026-07-01
supersedes: none (composes with HARD 0.37 VCSDD, HARD 0.40 GLVS)
---

# Outer Improvement Loop (OIL) — design draft

## Purpose

Sprint-4 shipped a full inner-correctness pipeline (spec → RED → GREEN →
fresh-context adversary → E2E, per HARD 0.37 VCSDD). But VCSDD answers
"is this code correct?" — not "what should we build next to make ¥ go up?".
The self-improving Anicca vision requires a DISCOVERY layer above VCSDD.

This spec sketches that outer layer. It is deliberately compact and
comparable to alternatives (Voyager / Reflexion / ADAS / Darwin-Gödel) so
Dais can pick.

## Non-goals

- Not replacing VCSDD. VCSDD stays as the correctness gate through which
  every candidate variant ships.
- Not competing with GLVS (HARD 0.40). GLVS is the harness (Goal→Loop→Verify
  →State) that wraps a single goal. OIL is what generates goals from
  production metrics.
- Not a benchmark eval. The metrics live in `~/loops/*/roi.jsonl` and
  friends; OIL reads them, does not construct them.

## Architecture (compact)

```
                            OIL (outer)
                     ┌──────────────────────┐
   metric trace ────▶│ 1. read metric       │
   (roi/settle/      │                      │
    apply/lesson)    │ 2. propose N variants│
                     │    (LLM w/ trace)    │
                     │                      │
                     │ 3. score variants    │
                     │    (fitness fn)      │
                     │                      │
                     │ 4. pick candidate    │
                     │                      │
                     │ 5. ship via VCSDD    │──▶ VCSDD (inner)
                     │                      │      ↓
                     │ 6. observe result    │◀── production loop
                     │    (24-72h window)   │      ↓
                     │                      │    roi.jsonl deltas
                     │ 7. keep or revert    │
                     └──────────────────────┘
                              │
                              └──▶ next iteration
```

## Requirements (EARS)

### Group M — Metric reading

- **REQ-M1**: OIL SHALL read the following per-slot metrics:
  - `~/loops/<slot>/roi.jsonl` (per-pass ROI: expected + realized)
  - `~/<slot>/applied.jsonl` (activity)
  - `~/<slot>/lessons.jsonl` (natural-language failure/success reflections)
  - `~/<slot>/earnings.jsonl` when it exists (real settle events)
- **REQ-M2**: OIL SHALL derive at least these fitness signals per slot:
  - `apply_rate` (applies/day over 7d window)
  - `accept_rate` (accepted/applied over 30d window)
  - `roi_realized_7d` (sum realized ¥ over 7d window)
  - `lesson_diversity` (unique outcomes per 7d window — proxy for exploration)
- **REQ-M3**: Reading MUST be pure (no writes to metric files). Snapshots
  land under `~/loops/<slot>/state/oil-snapshot.jsonl`.

### Group P — Proposal generation

- **REQ-P1**: An LLM (agnostic; default gpt-5.4-mini or grok-4.3, model
  chosen by ClawRouter free-path) SHALL be prompted with:
  - Slot ID + purpose one-liner
  - Last 30 metric snapshots
  - Last 50 lessons from `lessons.jsonl`
  - Current `strategy.json` (or equivalent per-slot config)
  - The instruction: "propose N (default 3) small, testable variants of
    strategy.json / STARTUP prompt / menu.json that could raise fitness"
- **REQ-P2**: Proposals MUST be structured JSON: `{variant_id, diff, hypothesis,
  expected_metric_delta, risk}`.
- **REQ-P3**: Diffs SHALL be VCSDD-compatible (spec-friendly, reviewable by
  fresh-context adversary). Proposals that require > 3 file changes or
  touch security surfaces are DEMOTED (not banned).

### Group S — Scoring + shipping

- **REQ-S1**: Each variant SHALL receive a fitness score = weighted sum of:
  - Expected `roi_realized_7d` delta (LLM-estimated, capped)
  - Adversarial-reviewability (heuristic: diff size + touch count)
  - Historical priors (variants similar to past winners score higher)
- **REQ-S2**: TOP-1 variant SHALL be shipped via VCSDD:
  - Spec derived from variant.hypothesis + variant.diff
  - RED test derived from variant.expected_metric_delta
  - GREEN impl = apply variant.diff
  - Fresh-context adversary review
  - Merge only when adversary PASS
- **REQ-S3**: OIL SHALL NOT auto-ship variants touching:
  - INV-1/P1/4 (LAYER C restart, slot-state writes)
  - Financial broadcasts (wallet key usage)
  - Public-visible outputs (X posts, articles) — those have separate
    review gates already

### Group O — Observation + keep-or-revert

- **REQ-O1**: After merge, OIL SHALL wait a slot-configurable observation
  window (default 72h) before scoring impact.
- **REQ-O2**: If observed fitness < baseline − epsilon (default 5%), OIL
  SHALL open a REVERT-CANDIDATE issue via bot2bot.sh — the actual revert
  goes through VCSDD (adversary confirms revert is safe first).
- **REQ-O3**: Winners are recorded in `~/loops/<slot>/state/oil-winners.jsonl`
  with the metric before/after and the hypothesis (this becomes the
  historical prior for REQ-S1).

### Group I — Invariants

- **REQ-I1** (GLVS composition): OIL runs as a menu item in each slot's
  proactive-loop with `min_cadence_seconds=86400` (once/day per slot).
- **REQ-I2** (VCSDD wrap): NO variant reaches production without passing
  through VCSDD Phase 6 convergence.
- **REQ-I3** (no human in loop): OIL never surfaces choices to Dais. If
  no variant scores above baseline, the tick is a no-op (`report: no-variant-
  above-baseline`).

## Comparison points for Dais's decision

| framework          | discovery engine        | correctness gate         | Anicca fit |
|--------------------|-------------------------|--------------------------|------------|
| VCSDD-only         | (none)                  | spec/adversary/E2E       | 0.5x       |
| OIL + VCSDD        | LLM proposes → fitness  | VCSDD (existing)         | 1.0x       |
| ADAS-lite          | LLM designs agents      | (needs bespoke eval)     | 0.7x       |
| Reflexion-lite     | verbal RL on lessons    | (weaker)                 | 0.6x       |
| Voyager-lite       | curriculum + skill lib  | env-simulator (missing)  | 0.4x       |
| Darwin-Gödel-lite  | code mutation           | full test suite (ours)   | 0.8x       |

Recommendation embedded above: **OIL + VCSDD**. But ready to compose with
Darwin-Gödel-style code mutation (our test suite is strong enough to be
the correctness selector for LLM-mutated code).

## Deployment plan (when Dais says go)

1. VCSDD lean pipeline: `oil-outer-improvement-loop` feature
2. Sprint 1: metric readers + proposal LLM (REQ-M/P)
3. Sprint 2: scoring + VCSDD-integrated shipping (REQ-S)
4. Sprint 3: observation window + revert path (REQ-O)
5. Sprint 4: menu item wire on gig (first slot); mirror to affiliate/
   bounty/clip once each has active earnings

## Block/wait state

- Dais evaluation of this vs other agent's research. No implementation
  proceeds without explicit direction.
- If Dais approves + names a preferred variant of OIL, sprint 1 starts
  immediately with the standard VCSDD pipeline.
