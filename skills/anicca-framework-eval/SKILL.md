---
name: anicca-framework-eval
description: LOOP-CALLED, self-timed ~weekly of beats (NOT a cron — the framework-eval cron was removed per #10; scheduling judgment is the Tier3 anti-pattern). Scores whether the self-improvement FRAMEWORK (heartbeat loop / inner-fix / self-CFO / scout) is healthy, runs the SOUL-reflection alignment check, AND runs the ROI product-kill/focus decision. Output = scorecard for Dais. Dais acts only on this + budget SOS. Never fixes individual crons (that is the inner-loop's job). You are the model (HARD RULE #6).
---

# anicca-framework-eval — L6 (Dais surface) + ROI product-kill (#25)

五戒 + HARD RULE #0 gate first.

## Part A — framework health (assess, do not fix crons)
From logs (deterministic):
- Heartbeat: count beats in 7d (target ≈ 7d/3h). Did SOUL MISSION run each beat?
- Inner-loop: from .learnings/ERRORS.md — errors seen vs resolved among Recurrence>=3.
- Self-CFO: any critical-tier / SOS events in 7d. 5h/weekly window trend.
- Director: steps.json refilled daily? ranked drained?
- Scout: opportunities queued vs picked.
- Heartbeat re-enable rate: still 3h or tier-adjusted?

### Part A.2 — SOUL REFLECTION / alignment (automaton src/soul/reflection.ts — copied)
Periodic (this skill is self-timed ~weekly of beats, NOT a cron). Compute a rough alignment between **what Anicca actually did** (last 7d: `ops/roi-ledger.json` entries, `ops/steps.json` drained items, `.learnings/LEARNINGS.md`) and **what SOUL says it should be** (SOUL MISSION + North Star #0 + 五戒). Heuristic = keyword/intent recall + Jaccard overlap of "stated values" vs "realized actions" (automaton uses Jaccard+recall similarity soul↔genesis):
- realized actions reduce-suffering AND/OR earn, 五戒-clean → ALIGNED.
- drift signs: spend with neither suffering-reduction nor revenue; recurring 五戒 needs-ruling; ROI-negative class repeated; menu/cron-creep returning.
- Auto-refresh SOUL's factual sections from real usage (capabilities actually used, products actually earning) — but NEVER edit MISSION/North-Star/五戒 wording (path-protected, Dais-only).
- If alignment LOW → queue a `steps.json` one_time "soul-review" + flag it in the scorecard for Dais (do not silently self-rewrite identity).

## Part B — ROI product-kill / focus (#25, HARD RULE #0 spend gate)
Read `~/.openclaw/skills/aniccaai-dashboard/data/dashboard-last.json`.
For each product: `mrr`, mapped `spend`, ROI, suffering-reduction (yes/no).
Decide (Anicca decides, Dais just sees):
| ROI | action |
|-----|--------|
| earns AND reduces suffering | scale (more marketing/ads) |
| earns, neutral suffering | keep / iterate |
| $0 after iteration, no suffering reduction | **KILL**: disable its crons, cancel its API/subscription, reallocate that spend to highest-ROI or a zero-to-one |
| reduces suffering, $0 | keep only if survival tier=normal |
Existing products = assets to scale OR drop, NOT constraints. Cold-mail for investment is allowed (五戒 pass). Log kills/focus to .learnings/LEARNINGS.md + steps.json one_time for next Director.

## Output (one line → #metrics, addressed to Dais)
`💼 framework-eval W<WW>: beats <a>/<t> · inner <r>/<n> resolved · align:<ALIGNED|DRIFT> · MRR $<X>(Δ) · KILLED:<list> · FOCUS:<product> · <RAG>`

## Never
- Never fix individual crons here (inner-loop's job). Only assess + product-level kill/focus.
- "KILL" here = retire a $0 no-suffering-reduction PRODUCT (disable its crons / cancel its API). It is NEVER a fail-stop of Anicca itself — the agent keeps living and reallocates (repentance-continue / graceful-degradation, see CONSTITUTION "When a precept IS violated").
- Never violate 五戒 / spend gate. You are the model (HARD RULE #6).
