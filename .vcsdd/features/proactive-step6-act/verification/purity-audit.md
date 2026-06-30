---
feature: proactive-step6-act
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — proactive-step6-act

## Declared Boundaries

| Layer | Symbols | Side effects |
|---|---|---|
| PURE — `lib/step6_act.py` | `sanitize_name`, `task_filename`, `task_descriptor` | none (str / dict in → str / dict out) |
| I/O SINK — `lib/step6_act.py` | `enqueue_task_descriptor(slot_dir, descriptor)` | disk write (atomic temp+rename) |
| PURE-ISH — `lib/step3_recipe.py` | `SCAFFOLD_DEFERRED_ACTIONS` frozenset; `default_restart_cmd_map` (str→list) | none |
| I/O — `lib/step3_recipe.py` | `execute_recipe(recipe, issue_kind, slot, cmd_map, timeout)` | subprocess.run (only when issue_kind=='tmux_dead' AND action=='restart') |
| ORCHESTRATOR | `proactive-loop-dispatch.py` STEP 3 + STEP 6 | composes PURE helpers + I/O |

## Observed Boundaries

- `sanitize_name` — verified pure: 9 parametrized exact-match tests (incl. Japanese / mixed / symbol-only / empty)
- `task_filename` / `task_descriptor` — pure str / dict construction; deterministic
- `execute_recipe` — subprocess invocation gated by TWO predicates (issue_kind + action); stale + restart explicitly returns `stale-suppressed-INV-P1` WITHOUT calling subprocess (proven by test_stale_restart_is_suppressed asserting cmd_log file NOT created)
- `enqueue_task_descriptor` — writes confined to `<slot_dir>/tasks/`; atomic via `.tmp` + rename; failure modes return `{ok:False, status}` dict (never raises)

## Sprint-2 Carry Fix

`lib/menu.py:112` `if novel_items and novelty_ratio > 0 and len(history) >= int(1.0 / novelty_ratio):` — added `novelty_ratio > 0` guard. The `> 0` is the only new clause; everything else is identical. 3 new tests prove the guard works (incl. saturated-history case that would have crashed on the old code).

## Summary

PURE layer (3 helpers in step6_act + 1 constant + 1 lookup in step3_recipe) verified side-effect-free. I/O sinks (enqueue_task_descriptor + execute_recipe subprocess) confined to declared paths. ORCHESTRATOR composes correctly per the live E2E observation.
