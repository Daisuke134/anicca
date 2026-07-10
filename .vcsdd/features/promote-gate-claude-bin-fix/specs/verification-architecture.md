# Verification Architecture — promote-gate-claude-bin-fix

## Proof Obligations

| ID | Requirement | Tier | Method |
|----|-------------|------|--------|
| PROP-CB1 | REQ-CB1 (PATH hit unchanged) | 1 | unit test: `shutil.which` monkeypatched to return a sentinel path → function returns exactly that path, `os.path.isfile` never consulted |
| PROP-CB2 | REQ-CB2 (fallback list, first existing wins) | 1 | unit test: `shutil.which` monkeypatched to `None`; `os.path.isfile`/`os.access` monkeypatched so only the 2nd candidate in the list "exists+executable" → function returns that 2nd candidate, not the 1st or the final default, and `os.path.isfile` was actually called (not a vacuous pass against the old hardcoded-string implementation) |
| PROP-CB2b | REQ-CB2 (ordering precedence when MULTIPLE candidates exist) | 1 | unit test: `shutil.which` → `None`; BOTH `~/.local/bin/claude` and `/opt/homebrew/bin/claude` report as existing+executable → function returns `~/.local/bin/claude` (the first in list order), proving the real-world 2026-07-10 regression (both paths plausible on a fully-provisioned machine) resolves to the actually-correct install location, not just "a" location |
| PROP-CB2c | REQ-CB2 ("exists" = isfile AND executable, not isfile alone) | 1 | unit test: `shutil.which` → `None`; first candidate (`~/.local/bin/claude`) reports `isfile=True` but `os.access(path, os.X_OK)=False` (exists but not executable — stale/broken install) → function skips it and returns the next candidate that IS executable, never a non-executable path (which would otherwise surface as an uncaught `PermissionError` in `_invoke_adversary`'s `subprocess.run` instead of the handled `FileNotFoundError` case) |
| PROP-CB3 | REQ-CB3 (final fallback preserved) | 1 | unit test: `shutil.which` → `None`; all candidate paths "do not exist" → function returns literal `"/opt/homebrew/bin/claude"` (regression-pins the existing fail-closed string used in `_invoke_adversary`'s error message), and `os.path.isfile` was actually called on the fallback list (not skipped) |
| PROP-CB4 | REQ-CB4 (no collateral change) | 0 | `git diff` scope check in adversary review: only `_resolve_claude_bin` body (+ its new test file) changed |

## Purity Boundary Map

- `_resolve_claude_bin()`: impure (env + filesystem). Tests isolate it by monkeypatching
  `shutil.which`, `os.path.isfile`, and `os.access` — no real filesystem or PATH
  dependency in the test itself, so the suite is deterministic across machines/CI.
- No new impure surface introduced; `subprocess.run` call sites in `_invoke_adversary`
  are unchanged.

## Test Plan (RED phase target)

New file: `skills/earn/self-improve/tests/test_resolve_claude_bin.py` (there is no `lib/tests/`
directory anywhere in this package — all 12 pre-existing tests live directly under
`skills/earn/self-improve/tests/`, per `conftest.py`'s `SELF_IMPROVE_DIR`/`TESTS_DIR` layout; this
file follows that same, already-correct convention).

5 tests total, one per PROP-CB1 / PROP-CB2 / PROP-CB2b / PROP-CB2c / PROP-CB3, using
`unittest.mock.patch`.

## Verification Tier Rationale

Tier 1 (property/unit test with monkeypatched I/O boundary) is sufficient — this is a
pure path-selection function with no concurrency, no external side effects beyond a
filesystem `stat`, and no security-sensitive input (no untrusted data reaches this
function; it only reads fixed, hardcoded candidate strings plus the process `PATH`).
Tier 0 (manual/diff-scope check) covers REQ-CB4. Lean mode: no Tier 2/3 obligations
required for a fix this narrow.
