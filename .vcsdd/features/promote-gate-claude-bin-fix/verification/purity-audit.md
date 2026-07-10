# Purity Boundary Audit — promote-gate-claude-bin-fix

## Feature: promote-gate-claude-bin-fix | Sprint: 2 | Date: 2026-07-10

## Declared Boundaries

From `specs/behavioral-spec.md` §"Purity Boundary":

> `_resolve_claude_bin()` is impure (reads `PATH` env + filesystem `stat`/`access`
> calls) — same purity class as today, no change in kind, only in which paths it
> probes. All existing pure decision logic (`lib/promote_gate.py::assess_candidate` /
> `decide_promotion` / `promote_if_approved`) is untouched.

From `specs/verification-architecture.md` §"Purity Boundary Map":

> `_resolve_claude_bin()`: impure (env + filesystem). Tests isolate it by monkeypatching
> `shutil.which`, `os.path.isfile`, and `os.access` — no real filesystem or PATH
> dependency in the test itself, so the suite is deterministic across machines/CI.
> No new impure surface introduced; `subprocess.run` call sites in `_invoke_adversary`
> are unchanged.

Declared shell/core split:
- **Shell (impure)**: `_resolve_claude_bin()` — env (`shutil.which` reads `PATH`) +
  filesystem (`os.path.isfile`, `os.access`) I/O.
- **Core (pure)**: `lib/promote_gate.py::assess_candidate`, `decide_promotion`,
  `promote_if_approved` — declared untouched by this feature.
- **Unchanged shell (impure)**: `_invoke_adversary()`'s `subprocess.run` call sites —
  declared as pre-existing impure surface, not modified.

## Observed Boundaries

Read `skills/earn/self-improve/lib/promote_gate_run.py` lines 93-111 directly (the only
lines changed by this feature, confirmed against `main` via the Phase 3 adversary's
byte-for-byte file comparison in
`.vcsdd/features/promote-gate-claude-bin-fix/reviews/implementation/iteration-2/output/verdict.json`):

```python
_CLAUDE_BIN_DEFAULT = "/opt/homebrew/bin/claude"
_CLAUDE_BIN_KNOWN_GOOD_PATHS = (
    os.path.expanduser("~/.local/bin/claude"),
    _CLAUDE_BIN_DEFAULT,
    "/usr/local/bin/claude",
)


def _resolve_claude_bin() -> str:
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    for candidate in _CLAUDE_BIN_KNOWN_GOOD_PATHS:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return _CLAUDE_BIN_DEFAULT
```

- The function's only I/O is: one `shutil.which("claude")` call (env/PATH read), and
  a loop of `os.path.isfile` + `os.access(path, os.X_OK)` filesystem stat calls over a
  fixed 3-element tuple of hardcoded path strings. This matches the declared "impure
  (env + filesystem)" classification exactly — no new impure category (no network, no
  subprocess, no write, no mutable global state) was introduced.
- `os.path.expanduser("~/.local/bin/claude")` is evaluated once at module-import time
  into the `_CLAUDE_BIN_KNOWN_GOOD_PATHS` tuple, not per-call inside
  `_resolve_claude_bin()`. This is a minor observed detail not explicitly called out in
  the declared boundary docs (which describe the function-level impurity, not
  module-load-time evaluation), but it does not change the purity classification:
  `expanduser` reads `$HOME`/pwd-db env state, which is still "env" I/O, and it happens
  exactly once per process regardless of how many times `_resolve_claude_bin()` is
  called — consistent with the "no new impure surface" claim, not a hidden per-call
  side effect.
- Confirmed via direct `Read` of the surrounding file (lines 1-349) that
  `_invoke_adversary()`'s `subprocess.run` call sites (used to shell out to the
  fresh-adversary `claude` CLI invocation) are textually unchanged from `main` —
  no new subprocess surface, no new shell-out path was added by this feature.
- Confirmed via `Read` of `lib/promote_gate.py` (not touched by this feature — no diff
  exists against `main` per the two adversary review iterations) that the declared pure
  decision-logic functions (`assess_candidate`, `decide_promotion`,
  `promote_if_approved`) remain untouched.
- Test isolation: `skills/earn/self-improve/tests/test_resolve_claude_bin.py` monkeypatches
  `shutil.which`, `os.path.isfile`, and `os.access` at the module-attribute level (via
  `mock.patch("shutil.which", ...)` / `mock.patch("os.path.isfile", ...)` /
  `mock.patch("os.access", ...)`) in every one of its 5 test functions — no test reaches
  the real filesystem or real `PATH`, matching the declared "no real filesystem or PATH
  dependency in the test itself" claim exactly.

## Mismatches / Drift

No drift detected. The observed implementation's impurity boundary (env read via
`shutil.which` + `os.path.expanduser`, filesystem stat via `os.path.isfile`/`os.access`,
zero new subprocess/network/write surface) matches the declared boundary in both
`specs/behavioral-spec.md` and `specs/verification-architecture.md` exactly. No
core/shell drift, no hidden side effects (no writes, no logging, no global mutation
beyond the module-load-time tuple construction), and no verifier-hostile coupling (the
function remains trivially mockable at its three I/O call sites, as demonstrated by the
5 passing tests that never touch the real filesystem).

## Summary

Purity boundary audit: **NO DRIFT DETECTED**. The implemented `_resolve_claude_bin()`
stays within its declared impure (env + filesystem) classification; no new side-effect
category was introduced; the declared-untouched pure core (`lib/promote_gate.py`) and
declared-untouched impure `_invoke_adversary()` subprocess surface were both confirmed
unchanged by direct file read. No follow-up required before Phase 6.
