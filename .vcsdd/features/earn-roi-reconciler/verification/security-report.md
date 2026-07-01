---
feature: earn-roi-reconciler
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — earn-roi-reconciler

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied |
| Static regex regression guards | 6 required:true grep tests continuously enforced |

## RCE / Injection

| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( (split-token check) | 0 |
| eval( | 0 |

## Anti-Human-Touch (REQ-J8)

- 0 hits on osascript / terminal-notifier / telegram / slack / twilio / SecKeychain / find-generic-password

## INV-1 / INV-P1 LAYER C protection

- reconciler.py: grep tmux\\s+kill|kill-session|kill-server|--stop|--kill → 0
- No subprocess call to any <slot>-cli.sh

## INV-4 ~/gig read-only

- reconciler.py: string "earnings.jsonl" appears 0 times in the source
- Live E2E confirms: SHA-256 of all ~/gig/*.jsonl files IDENTICAL before/after reconcile

## Fail-Closed

- roi_jpy_realized NEVER fabricated; ambiguous → .unmatched.jsonl
- Malformed lines preserved via __raw__ (roi) or __malformed__:offset (settle)
- Crash-safe: (i)-(v) ordering with offset LAST; monotone-max makes replay safe

## Summary

Live-money critical path hardened. AI-slop containment via 3-iter spec adversary + 2-iter impl adversary caught real bugs (silent under-counting, dropped malformed lines, missing crash-safety test, malformed-line collapse, missing pick_next proof).
</parameter>
