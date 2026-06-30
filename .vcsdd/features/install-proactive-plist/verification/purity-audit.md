---
feature: install-proactive-plist
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Purity Boundary Audit — install-proactive-plist

## Declared Boundaries

Per `specs/verification-architecture.md` Phase 1b, single-source PURE in
`lib/plist_render.py`. The thin shell front-end calls into the Python
module via `python3 -m lib.plist_render <subcmd>` and re-implements NONE
of the PURE logic in bash (FIND-007 single-source decision).

### PURE layer — `skills/_shared/lib/plist_render.py`

| Symbol | Side effects |
|--------|--------------|
| `validate_slot(slot)` | none — raises SlotValidationError on bad input |
| `render_plist(slot, anicca_home, log_dir, plist_path)` | none — pure str transformation; re-validates for defense in depth |
| `plist_digest(content)` | none — SHA-256 over UTF-8 |
| `parse_loaded_plist_path(launchctl_print_output)` | none — regex match + strip |
| `_cli(argv)` | reads stdin + prints stdout (= I/O boundary) for the shell to invoke |
| `CANONICAL_ANICCA_HOME` constant | none — frozen string `/Users/anicca/anicca` |

### I/O-BOUND layer — `skills/_shared/install-proactive-plist.sh`

| Step | I/O surface |
|------|-------------|
| arg parse + LAUNCHCTL_BIN gate | env-var read, file stat, pwd -P canonicalize |
| validation subprocess | `python3 -m lib.plist_render validate <slot>` (read-only) |
| Darwin check | `uname -s` |
| repo root pin | `cd .. && pwd` |
| dir create | `mkdir -p $HOME/Library/LaunchAgents $HOME/.openclaw/logs` |
| render subprocess | `python3 -m lib.plist_render render` (PURE produced via stdout) |
| collision detect | `launchctl print` + `python3 -m lib.plist_render parse-path` |
| digest compare | `python3 -m lib.plist_render digest` × 2 |
| disk write | `printf '%s' "$NEW_CONTENT" > "$PLIST"` |
| launchctl bootstrap/bootout | macOS service registry |
| post-install verify | `launchctl print >/dev/null` |
| tmp cleanup | `trap 'rm -f ...' EXIT` |

## Observed Boundaries

`validate_slot('gig; rm -rf /')` — raises SlotValidationError without
mkdir / file write / launchctl call (verified by
`test_injection_guard_no_side_effect` snapshot-diff).

`render_plist(slot='gig', ...)` — returns deterministic XML string with
literal `/Users/anicca/...` paths; zero `$HOME` tokens (verified by
`test_render_NEVER_emits_HOME_token`).

`parse_loaded_plist_path(...)` — pure regex extraction; tested with 4
inputs (well-formed, missing, with-spaces, trailing-whitespace).

## Boundary Deviations

1. `_cli(argv)` reads stdin and prints stdout — semantically I/O at the
   module's CLI seam. The PURE helpers it delegates to remain
   side-effect-free.
2. `render_plist` accepts a `plist_path` parameter it includes verbatim
   in keys; the caller must pre-resolve to absolute (verified via
   leading-slash assert).
3. The shell front-end is the only place the FS and launchctl are
   touched; the PURE module never imports `os.system` / `subprocess`.

## Summary

PURE layer = 4 helpers + 1 constant + 1 module CLI entry. Adversary
iter-3 confirmed no duplicate PURE logic exists in the shell (`grep`
ban for `validate_slot|render_plist|parse_loaded_plist_path|plist_digest`
as bash function definitions = 0 hits, per
`test_shell_does_not_reimplement_pure_logic`).

Residual purity risks: none material; the LAUNCHCTL_BIN env hook is
gated by canonicalized-temp-root check + log + executable test (per
FIND-2-001 hardening).
