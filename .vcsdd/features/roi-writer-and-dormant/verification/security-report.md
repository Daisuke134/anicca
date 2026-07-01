---
feature: roi-writer-and-dormant
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — roi-writer-and-dormant

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied; `security-results/manual-grep.txt` |
| AST walk regression guard | continuously enforced (test_dispatcher_ast_no_kill_argv) |
| \b regex import + call-site guard | continuously enforced (test_dispatcher_does_not_call_legacy_dormant_symbols) |

## RCE / Injection

| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( | 0 |
| eval( | 0 |
| \\bsudo\\b (word-boundary) | 0 |

## Anti-Human-Touch (REQ-J8 inherited)

- 0 hits on osascript / terminal-notifier / telegram.org / hooks.slack.com / twilio / SecKeychain / find-generic-password

## INV-1 / INV-P1 LAYER C protection

- lib/roi_track.py: no subprocess calls
- lib/quota_tracker.py (appended helpers): no subprocess, no fs writes
- proactive-loop-dispatch.py new code: AST walk over ast.Constant literals contains NONE of {kill-session, kill-server, --kill, --stop}
- \b regex over dispatcher: 0 call sites of is_dormant() or write_dormant_sentinel() (per REQ-I3 scope-cut Group D)

## Summary

All grep + AST guards return 0 hits. The critical Phase 3 iter-1 catch (REQ-W1 exit-path drops) was a spec-compliance bug, not a security vulnerability, but the roi.jsonl signal loss would have been silent and undetectable in production. Cycle-2 hoisted the emit into a helper called from all exit paths + added integration tests for each. AI-slop contained.

## Sprint-4 carry

Group D dispatcher wire is DELIBERATELY deferred. Sprint-4 must:
1. Re-enable is_dormant_with_horizon call site.
2. Add PROP-D* obligations with real settle data.
3. Extend security scan to cover the sentinel write path.
