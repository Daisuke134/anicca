---
feature: proactive-step6-act
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — proactive-step6-act

## Purity boundary

| Layer | Symbols | Side effects |
|---|---|---|
| PURE (in `lib/step6_act.py`) | `sanitize_name(name)`, `task_filename(ts, name)`, `task_descriptor(pass_id, ts, picked, budget, slot)`, `select_restart_cmd(slot, cmd_map)` | none |
| I/O-BOUND (in `lib/step6_act.py`) | `enqueue_task_descriptor(slot_dir, descriptor)` | disk write to `<slot_dir>/tasks/` |
| I/O-BOUND (in `lib/step3_recipe.py`) | `execute_recipe(recipe, slot, cmd_map, timeout=30)` → `{ok:bool, status:str}` | subprocess invocation |
| ORCHESTRATOR (in `proactive-loop-dispatch.py`) | STEP 3 + STEP 6 wired to the above | composes |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-T1-enqueue-creates-file | 1 | true | REQ-T1, REQ-T2 |
| PROP-T2-descriptor-shape | 1 | true | REQ-T2 (= 6 keys present) |
| PROP-T3-filename-sanitized | 1 | true | REQ-T3 |
| PROP-T4-idempotent-pass-id | 1 | true | REQ-T4 |
| PROP-T5-build-log-outcome | 1 | true | REQ-T5 (= "enqueued:<filename>") |
| PROP-R1-restart-invokes-cmd | 1 | true | REQ-R1 (= subprocess called with the resolved cmd) — assert ONLY when Issue.kind == `tmux_dead` |
| PROP-R1a-stale-suppressed | 1 | true | REQ-R1a (= Issue.kind == `stale` + action == `restart` → log + NO subprocess; parent INV-P1) |
| PROP-R2-restart-failures-logged | 1 | true | REQ-R2 (= rc!=0 + timeout both log + continue) |
| PROP-R3-other-actions-scaffold-only | 1 | true | REQ-R3, EDGE-E6 — parametrized over the full 7-action set {kill_server, send_keys, login, npm_install, git_checkout, escalate_via_bot2bot, noop} + unknown-action catch-all |
| PROP-R4-cmd-table-lookup | 1 | true | REQ-R4, EDGE-E7 |
| PROP-I1-no-tmux-kill | 1 | true | REQ-I1 static grep |
| PROP-I2-step6-writes-scoped | 1 | true | REQ-I2 mtime snapshot scoped to <slot_dir>/tasks/* + build_log.md ONLY (NOT state/, which the dispatcher legitimately writes every step) |
| PROP-I3-no-human-touch | 1 | true | REQ-I3 grep |
| PROP-E1-tasks-dir-autocreate | 1 | true | EDGE-E1 |
| PROP-E3-dup-pass-id-skipped | 1 | true | EDGE-E3 |
| PROP-E8-write-fail-no-crash | 1 | true | EDGE-E8 |

15 required:true (Tier 0/1). Lean mode. Tests:
- `__tests__/test_step6_act.py` — PURE + enqueue unit tests.
- `__tests__/test_step3_recipe.py` — execute_recipe unit tests with shim.
- `__tests__/test_dispatch_integration.py` — full proactive-loop-dispatch.py
  run on a synthetic ~/loops/<probe>/ slot dir; assert tasks/ file appears,
  build_log gains "enqueued:" outcome, ~/gig/ untouched.

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + live `bash skills/_shared/proactive-loop.sh gig` against
  production after #27, verifying tasks/ file gets enqueued AND gig-cli.sh
  not restarted spuriously (= recipe.action == noop in healthy state).
