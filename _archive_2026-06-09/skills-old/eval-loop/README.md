# eval-loop

Single-purpose Hermes skill that gates every Anicca output through a 4-dimension
LLM-as-judge (accuracy / helpfulness / harmlessness / coherence) backed by
DeepEval's GEval, with a heuristic fail-closed fallback. Default threshold 0.7.
Used by `scripts/eval.sh`, sourceable lib `scripts/lib.sh::eval_or_fail`, and the
repo-level `.githooks/pre-push`. Cost per eval is logged to
`~/.hermes/state/eval-cost.jsonl`. See `SKILL.md` for the manifest and
`docs/superpowers/plans/2026-06-04-eval-loop.md` for the Wave-1 plan.
