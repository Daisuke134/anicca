---
feature: recipe-6-actions
phase: 5
generated_at: 2026-07-01
mode: lean
---

# Purity Boundary Audit — sprint-4 (d)

## Declared Boundaries

| Layer | Symbol | Side effects |
|---|---|---|
| I/O SHELL — `lib/step3_recipe.py::execute_recipe` | 6 real wires | subprocess (tmux/npm/git/bot2bot/login-service) |
| PURE — `SEND_KEYS_FLOW_MAP` + `NPM_INSTALL_FLOW_MAP` + `SCAFFOLD_DEFERRED_ACTIONS` | module-level dicts/frozenset | none (module-level constants) |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 3 | passes recipe/issue_kind/anicca_home through | unchanged |

## Observed Boundaries

- Module-level constants (`SEND_KEYS_FLOW_MAP`, `NPM_INSTALL_FLOW_MAP`,
  `SCAFFOLD_DEFERRED_ACTIONS`) are frozen data literals — **pure**.
- `execute_recipe` is the sole I/O shell; all 6 branches invoke subprocess
  inside try/except; no other side-effects (no file writes, no globals
  mutated). Return type is a `{ok, status}` dict — **contained**.
- No wire writes under `loops/<slot>/` (INV-4 preserved, verified by
  `test_I3_no_slot_state_writes` grep).
- Dispatcher's call site is unchanged in structure: it constructs
  `anicca_home` from env and passes it as a kwarg — the recipe execution
  side-effects are triggered ONLY when a health issue is classified.

## Summary

Purity boundary intact. All side effects confined to `execute_recipe` and
happen only when the issue-classification pipeline emits an actionable
recipe. Guardrails (try/except, argv-list form, timeouts) enforce the
"never raises + never hangs" contract.
