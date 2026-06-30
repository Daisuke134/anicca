---
feature: install-proactive-plist
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — install-proactive-plist

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied; captured in `security-results/manual-grep.txt` |
| test_install_no_human_touch.py static scan | continuously enforced (15 test cases) |
| test_install_launchctl_bin_guard.py runtime gate | continuously enforced (3 test cases) |
| bandit | sprint-3 commitment (PEP 668 / pipx flow inherited from sprint-2) |

## Summary

### RCE / Injection Surface

Patterns probed across the shell front-end + the Python PURE module:

| Pattern | Hits | Verdict |
|---------|------|---------|
| `subprocess(..., shell=True)` | 0 | clean |
| `os.system(` | 0 | clean |
| `eval(` | 0 | clean |
| `<<PYEOF` / `<<EOF` with `$` interp | 0 | clean |
| `\bsudo\b` (word-boundary) | 0 | clean |

Slot argument: validated by regex `^[a-z0-9_-]{1,32}$` BEFORE any FS or
launchctl side-effect (REQ-A4 ordering invariant). Injection vectors
`gig; rm -rf /`, `gig\`whoami\``, `$(echo hi)`, `../etc/passwd` all
unit-tested as rejected.

### Anti-Human-Touch (REQ-J8 inherited)

`HUMAN_TOUCH_PATTERNS` static scan = 0 hits:
- osascript, terminal-notifier
- telegram.org, hooks.slack.com, twilio
- find-generic-password, security add-generic-password, SecKeychain
- sudo

Outbound URLs: ONLY allow-listed `localhost | 127.0.0.1 | 0.0.0.0 |
www.apple.com/DTDs/` (= the Apple plist DOCTYPE namespace marker, a
documented macOS convention, not a network fetch).

### Production Foot-Gun Audit — LAUNCHCTL_BIN env hook

The shell exposes a `LAUNCHCTL_BIN` env var so tests can inject a fake
launchctl (= EDGE-E5 rollback test). To prevent accidental production
misuse:

1. Path is canonicalized via `cd "$(dirname …)" && pwd -P` — defeats
   `LAUNCHCTL_BIN=/tmp/../etc/launchctl` traversal escapes.
2. Canonical path must lie under one of: `$TMPDIR | /tmp | /private/tmp |
   /private/var/folders | /var/folders` (= the macOS temp-root prefixes).
3. Path must be executable (`-x` test).
4. Any override triggers a stderr `WARN: LAUNCHCTL_BIN override active
   (test mode)` line so it's visible in cron logs.
5. Rejection exits 9 BEFORE any other side-effect.

Adversary iter-3 explicitly verified the path-traversal escape is
canonicalized away.

### Spec-Gaming / AI-Slop Surface

Phase 3 adversary catches:
- iter-1: 6 findings (1 critical FIND-001 collision-bootout race + 2 high + 3 medium)
- iter-2: 1 new finding (FIND-2-001 production foot-gun on LAUNCHCTL_BIN)
- iter-3: 0 new findings → PASS

The escalating finding cycle catching production-foot-gun on iter-2 is
the AI-slop containment story for this feature — the test-only hook was
genuinely a security risk if exported in cron.
