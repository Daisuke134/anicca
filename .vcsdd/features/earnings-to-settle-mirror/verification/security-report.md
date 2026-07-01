---
feature: earnings-to-settle-mirror
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — earnings-to-settle-mirror

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied |
| Static regex regression guards | 4 grep tests continuously enforced |

## RCE / Injection

| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( | 0 |
| eval( | 0 |

## Anti-Human-Touch (REQ-J8)

- 0 hits on osascript / telegram / slack / twilio / SecKeychain / find-generic-password / terminal-notifier

## INV-1 / INV-P1

- settle_mirror.py contains 0 hits on `tmux kill|kill-session|kill-server|--stop|--kill`
- No subprocess call to any `<slot>-cli.sh`

## INV-4 ~/gig read-only

- Source grep: `open(...earnings...` in write mode = 0 hits
- Live E2E confirms SHA-256 of ~/gig/earnings.jsonl before/after unchanged when the mirror doesn't seed test data itself

## Fail-Closed

- pass_id never fabricated; missing / malformed → `unmatched-requestId-<X>` sentinel
- reconciler routes sentinel to `.unmatched.jsonl` with reason="unknown-pass-id"

## Summary

Live-money critical path hardened. AI-slop containment via 3-iter spec adversary (6→3→0) + 2-iter impl adversary (1→0).
</parameter>
