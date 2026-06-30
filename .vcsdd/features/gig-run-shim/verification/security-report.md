---
feature: gig-run-shim
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — gig-run-shim

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied; captured in `security-results/manual-grep.txt` |
| test_gig_run_shim_no_human_touch.py static scan | continuously enforced |

## Summary

### RCE / Injection
| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( | 0 |
| eval( | 0 |
| `\bsudo\b` (word-boundary) | 0 |

### Anti-Human-Touch (REQ-J8 inherited)
- osascript, terminal-notifier, telegram.org, hooks.slack.com, twilio, SecKeychain, find-generic-password → 0 hits

### INV-1 / INV-P1 — LAYER C tmux core protection
- run.sh grep for `tmux kill|--restart|--stop|--kill` → 0 hits
- The shim only invokes `gig-cli.sh` (no args, idempotent start) + `gig-cli.sh --status` (read)

### INV-4 — no double-write of ~/loops/gig/
- run.sh writes ZERO files under ~/loops/gig/ (= proven via sentinel-seeded mtime + content invariance integration test)

### Spec-Gaming Surface
Phase 3 adversary caught the one real test-quality bug (mtime-snapshot was a
no-op when ~/loops/gig empty) on iter-1; cycle-2 sentinel fix verified at
iter-2. AI-slop contained.
