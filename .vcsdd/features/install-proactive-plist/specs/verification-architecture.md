---
feature: install-proactive-plist
phase: 1b
mode: lean
generated_at: 2026-07-01
---

# Verification Architecture — install-proactive-plist

## Purity boundary

| Layer | Symbols | Side effects |
|---|---|---|
| PURE (single source — `lib/plist_render.py`) | `validate_slot(slot)`, `render_plist(slot, anicca_home, log_dir, plist_path)`, `plist_digest(content)`, `parse_loaded_plist_path(launchctl_print_output)` | none — string in / string out |
| THIN SHELL FRONT-END (`install-proactive-plist.sh`) | argument parse → calls `python3 -m lib.plist_render` for validation + render + parse → invokes `launchctl bootstrap/bootout/print` | disk + launchctl |
| LAUNCHD subprocess | `launchctl bootstrap / bootout / print` | OS service registry |

**Single-source decision (FIND-007 fix)**: The shell script does NOT re-implement
validation, render, or parse in bash. It calls into the PURE Python helpers
via `python3 -m lib.plist_render`. The PURE helpers are unit-tested; the shell
script is tested via integration tests only. No duplicate PURE logic exists in
two languages.

## Proof obligations

| PROP | Tier | Required | Maps to |
|---|---|---|---|
| PROP-A1-render-template | 1 | true | REQ-A1, REQ-A2, REQ-A3 (= rendered plist contains literal `/Users/<uid>/...` paths, NOT `$HOME` tokens) |
| PROP-A2-repo-pin | 1 | true | REQ-A2 (= installing from `~/anicca-project` or any non-pinned root → exit non-zero with mismatch error; no plist written) |
| PROP-A4-injection-guard-ordering | 1 | true | REQ-A4, EDGE-E4 (= validation runs BEFORE any side-effect; assert by monkey-patching mkdir/launchctl to fail-loud + slot='gig; rm -rf /' must surface validation error not the side-effect failure) |
| PROP-B1-idempotent | 1 | true | REQ-B1, REQ-B4, EDGE-E7 (= 2nd identical call = byte-identical plist on disk + same launchd PID/load-ts) |
| PROP-B2-template-change | 1 | true | REQ-B2 (= different content → rewrite + bootout/bootstrap + new load-ts) |
| PROP-C1-loaded-check | 1 | true | REQ-C1 (= post-install `launchctl print` succeeds + returns state in {running, waiting}) |
| PROP-D1-no-human-touch-comprehensive | 1 | true | REQ-D1, REQ-D2 (= grep the .sh + the Python helper + ANY imported module for: osascript, terminal-notifier, telegram, slack, twilio, find-generic-password, security add-generic-password, sudo, SecKeychain, outbound URLs except `localhost`. Static scan + runtime monkey-patch denial) |
| PROP-E1-cohealth-load-identity | 1 | true | REQ-E1 (= compare PID and load-timestamp of `ai.anicca.<slot>-core-healthcheck` BEFORE and AFTER our install; both must be identical — a bootout-then-rebootstrap fails this) |
| PROP-E2-conflict-detect-and-bootout | 1 | true | REQ-E2 (= using the documented `parse_loaded_plist_path()` algorithm: stub `launchctl print` to return a `path = /other/...` line → `parse_loaded_plist_path` extracts `/other/...` → script issues bootout, then writes our plist) |
| PROP-NFR1-single-source-pure | 0 | false | NFR-1 + FIND-007 fix (= grep the .sh for re-implementation of `validate_slot`/`render_plist`/`parse_loaded_plist_path` keywords; allow only `python3 -m lib.plist_render` calls) |
| PROP-NFR2-wall-time | 0 | false | NFR-2 (= time-bounded smoke test) |
| PROP-NFR3-stdout-clean | 1 | true | NFR-3 (= stdout = one summary line, all errors on stderr) |
| PROP-E5-half-load-rollback | 1 | true | EDGE-E5 (= simulated bootstrap failure leaves plist either fully booted OR removed-from-disk; never both partially) |
| PROP-E6-darwin-only | 1 | true | EDGE-E6 (= when `uname -s != Darwin`, exit 2 with stderr "Darwin only", no plist written) |

Lean mode required:true count = 12 (added PROP-A2-repo-pin per FIND-001 fix).
All Tier 1 via pytest (PURE helpers) + shell integration test (= the
install-then-print-then-bootout cycle, gated on Darwin).

## Test harness

- `__tests__/test_plist_render.py` — PURE helper unit tests (cross-platform).
- `__tests__/test_install_integration_darwin.py` — full install cycle; skipped
  on non-Darwin via `pytest.skip(... if sys.platform != "darwin" else None)`.
- `__tests__/test_no_human_touch.py` — static grep over the .sh source.

## Out of scope for Phase 5 hardening

- Bandit/semgrep (= shell script + minimal Python; manual grep sweep suffices,
  same pattern as proactive-loop-skeleton sprint-2).
- Formal proofs (= lean mode).

## Done = 4-D convergence

- spec ✓ test ✓ impl ✓ verification ✓
- adversary PASS + my own live `install-proactive-plist.sh gig` against a real
  slot, `launchctl list ai.anicca.gig-proactive` confirms loaded, plist visible
  in `~/Library/LaunchAgents/`, then `bootout` clean-up confirmed.
