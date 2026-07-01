---
feature: recipe-6-actions
phase: 5
generated_at: 2026-07-01
mode: lean
---

# Security Hardening Report — sprint-4 (d)

## Tooling

- Manual grep for `shell=True`, `eval(`, `exec(`, `os.system(`, `subprocess.getoutput(`.
  Result: 0 hits (see verification/security-results/scan.txt).
- All 6 subprocess.run call sites use argument-list form; user-controlled fields
  (`params.reason`, `params.flow`, `params.target`, `params.keys`) pass as
  individual list elements → shell metacharacters cannot expand.
- No new network I/O.
- All 6 wires wrap subprocess.run in try/except with typed handlers for
  `TimeoutExpired`, `OSError`, `FileNotFoundError` — guaranteeing the tick
  continues on any subprocess failure.

## Summary

Zero SAST-relevant findings. The dominant attack surface (command injection via
user-provided params) is closed by argv-list form. Group-C `anicca_home`
resolves from `os.environ["ANICCA_HOME"]` in the dispatcher — the value is
plumbed through as a cwd/prefix but never shell-interpolated. All fail-soft
paths return `{ok: True, status: "-no-*-deferred"}` when preconditions fail;
`{ok: False, status: "-failed-*"}` on runtime errors — dispatcher tick
continues either way.
