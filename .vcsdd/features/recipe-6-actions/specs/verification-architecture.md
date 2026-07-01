---
feature: recipe-6-actions
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — recipe-6-actions

## Purity boundary

| Layer | Symbol | Side effects |
|---|---|---|
| I/O SHELL — `lib/step3_recipe.py::execute_recipe` | REQ-A1..C3 wires | subprocess (tmux/npm/git/bot2bot/login) |
| PURE — status string construction | none |
| ORCHESTRATOR — `proactive-loop-dispatch.py` STEP 3 (unchanged) | passes recipe/issue_kind through |  |

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-A1-kill_server-invokes-tmux | 1 | true | REQ-A1 |
| PROP-A1-kill_server-timeout-caught | 1 | true | REQ-A1 EDGE-E1 |
| PROP-A2-escalate-invokes-bot2bot | 1 | true | REQ-A2 |
| PROP-A2-escalate-missing-script-fail-soft | 1 | true | REQ-A2 EDGE-E5 |
| PROP-B1-send_keys-invokes-tmux-send-keys | 1 | true | REQ-B1 (keys variant) |
| PROP-B1-send_keys-flow-variant-mapped (FIND-001 fix) | 1 | true | REQ-B1 flow="reinject_startup" → "/startup" |
| PROP-B1-send_keys-unknown-flow-fail-soft (FIND-001 fix) | 1 | true | REQ-B1 unknown flow → ok:True status:send_keys-unknown-flow-* |
| PROP-B1-send_keys-enter-flag-appends-Enter | 1 | true | REQ-B1 |
| PROP-B1-send_keys-timeout-caught (FIND-003 fix) | 1 | true | REQ-B1 EDGE-E1 |
| PROP-C1-login-fail-soft-missing-script | 1 | true | REQ-C1 EDGE-E6 |
| PROP-C1-login-timeout-caught (FIND-003 fix) | 1 | true | REQ-C1 EDGE-E1 |
| PROP-C2-npm_install-invokes-npm | 1 | true | REQ-C2 |
| PROP-C2-npm_install-flow-consumed (FIND-2-001 fix) | 1 | true | REQ-C2 NPM_INSTALL_FLOW_MAP: status contains `flow=allowlist_check` when hook_missing recipe fires; missing flow → plain `npm_install-ok`; unknown → `npm_install-ok-flow=<F>` |
| PROP-C2-npm_install-timeout-caught (FIND-003 fix) | 1 | true | REQ-C2 EDGE-E1 |
| PROP-C3-git_checkout-invokes-git | 1 | true | REQ-C3 |
| PROP-C3-git_checkout-timeout-caught (FIND-003 fix) | 1 | true | REQ-C3 EDGE-E1 |
| PROP-A2-escalate-timeout-caught (FIND-003 fix) | 1 | true | REQ-A2 EDGE-E1 |
| PROP-C-no-anicca-home-fail-soft (FIND-002 fix) | 1 | true | Group-C signature change: empty anicca_home → ok:True status:-no-anicca-home-deferred |
| PROP-I1-no-restart-cmd-map-called | 1 | true | REQ-I1 grep |
| PROP-I2-never-raises | 1 | true | REQ-I2 (all subprocess wrapped in try/except) |
| PROP-I3-no-slot-state-writes (FIND-003 fix) | 1 | true | REQ-I3 INV-4: grep dispatcher and step3_recipe for writes under `loops/<slot>/` — 0 occurrences from Group-A/B/C code paths |
| PROP-I4-scaffold-set-empty-or-noop-only | 1 | true | REQ-I4 |

21 required:true. Tests:
- `__tests__/test_recipe_6_actions.py` — unit tests with subprocess mocking
  (monkeypatch subprocess.run) for the 6 action wires.
- `__tests__/test_recipe_6_actions_invariants.py` — grep/static invariants
  (PROP-I1, PROP-I4).

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- vcsdd:vcsdd-adversary PASS (fresh context, 5 dims, 0 new findings)
- Live smoke: manual `execute_recipe` call for each of the 6 actions in a
  local shell — assert exit is deterministic and no crash.
