---
name: eval-loop
description: 4-dimension LLM-as-judge gate (accuracy / helpfulness / harmlessness / coherence) for ANY agent output. Mirrors swarms council_as_judge.py:36-65 and DeepEval GEval. Default threshold 0.7 (configurable per rubric). Use this skill BEFORE shipping any output (X post, gig reply, SEO page, paywall copy, cron output) — pass = ship, fail = rework. Wired as both a CLI (scripts/eval.sh) and a sourceable shell helper (scripts/lib.sh::eval_or_fail). Includes a fail-closed deterministic heuristic fallback so the gate runs even when every BYOK backend is down. Cost per eval is logged to ~/.hermes/state/eval-cost.jsonl.
---

# eval-loop

## What it does
One single-purpose Anicca quality gate. Given an `(input, output, rubric)` triple,
it scores the output on four dimensions in parallel — **accuracy, helpfulness,
harmlessness, coherence** — using DeepEval's GEval (LLM-as-judge with a written
rubric) and aggregates to a weighted total. Threshold defaults to **0.7** (the
"Fix AI Slop" loop bar per spec 16 §C and 24 §1). Below threshold = the output
is slop, do not ship.

## How it's invoked

Three call sites — all back the same engine:

1. **CLI (any skill, any language):**
   ```
   scripts/eval.sh <input.txt> <output.txt> [rubric.json]   # rubric defaults to rubrics/default.rubric.json
   # stdout = one JSON object:
   # {ts, backend, model, mode, task_class, scores, reasons, weights,
   #  threshold, total, pass, reason, elapsed_s}
   #
   # Env: EVAL_MODE="production"|"test" (default production),
   #      EVAL_LOOP_NO_ENV=1 skips sourcing ~/.hermes/.env (test isolation).
   ```

2. **Shell library (skills written in bash):**
   ```bash
   source $HERMES_HOME/skills/eval-loop/scripts/lib.sh
   eval_or_fail rubrics/post-to-x.rubric.json output.txt input.txt   # exit 0 = pass, 1 = fail
   ```

3. **Git pre-push hook** (`anicca-oss/.githooks/pre-push`) blocks any push that
   contains a NEW or MODIFIED file matching `skills/**/eval-output/*.txt` whose
   eval result is `pass: false`. Skills that emit creative output for review
   should write into that `eval-output/` subdirectory so the hook gates them.

## Rubric format

```json
{
  "task_class": "post-to-x",
  "threshold": 0.7,
  "weights":     { "accuracy": 0.25, "helpfulness": 0.25, "harmlessness": 0.25, "coherence": 0.25 },
  "dimensions":  { "accuracy": "...", "helpfulness": "...", "harmlessness": "...", "coherence": "..." }
}
```

`dimensions` strings are the EXACT rubric prompts sent to the judge LLM.
`harmlessness` maps to Constitution Precept 1 (Pāṇātipātā veramaṇī — never
harm; physically, financially, psychologically).

## Backend selection
Wave 1 priority (first key present wins; mini/cheap models per CLAUDE.md
"OpenClaw cron は mini 主軸"): `OPENAI_API_KEY` → `gpt-4o-mini`, else
`DEEPSEEK_API_KEY` → `deepseek-chat`, else `ANTHROPIC_API_KEY` →
`claude-haiku-4-5-20251001`, else `GEMINI_API_KEY`/`GOOGLE_API_KEY` →
`gemini-2.0-flash`, else `MOONSHOT_API_KEY`/`KIMI_API_KEY` → `moonshot-v1-8k`,
else **heuristic** (deterministic offline scorer — fail-closed, never crashes
the gate). Each non-OpenAI provider is constructed via its concrete DeepEval
model class (a bare model-id string only routes to OpenAI). The chosen backend
is recorded per row in `~/.hermes/state/eval-cost.jsonl`.

## Mode (`EVAL_MODE`)
- `production` (DEFAULT — pre-push hook, `eval_or_fail`, every side-effectful caller):
  if the backend collapses to `heuristic` the result is FORCED to
  `pass: false` with `reason: "all backends down"`. Side-effectful gates
  (merge / ship / publish) MUST refuse to accept heuristic scores as a
  green light. Architectural contract per spec 24 § 1.
- `test`: heuristic scores are returned as-is. Used only by the eval-loop
  test suite to verify the heuristic scoring logic still works under
  simulated backend outage.

`EVAL_LOOP_NO_ENV=1` tells `eval.sh` to skip sourcing `~/.hermes/.env`
(otherwise the dot-env would reintroduce real keys and the all-backends-down
path could not be exercised in tests).

## What it writes
`~/.hermes/state/eval-cost.jsonl` (append-only). Each line:
```json
{"ts":"...","backend":"openai","model":"gpt-4o-mini","dim_count":4,"total":0.84,"pass":true,"elapsed_s":3.21,"rubric_task_class":"post-to-x"}
```

## Out of scope (tracked elsewhere)
- Multi-instance live council (multiple Anicca workers as judges) = task #337 SWARM.
- Self-improve loop integration (eval failure → file issue → re-generate) = task #335.
- Runtime guard on every ReAct turn = separate Hermes-level hook.
- Prod-monitor cron + drift detection = separate plan.
- Auto-append failures to a regression suite = separate plan.

## Failure mode
If all judge backends are unreachable the heuristic fallback runs.
In `EVAL_MODE=production` (default) the heuristic ALWAYS returns
`pass: false` with `reason: "all backends down"` — side-effectful gates
fail closed (codex P6 round 2 contract). In `EVAL_MODE=test` the
heuristic's score is returned as-is. If the heuristic ALSO somehow raises
(shouldn't), `eval.sh` exits 3 and prints `{"error":"eval.py crashed …"}`.
The pre-push hook treats exit 3 as a hard block.
