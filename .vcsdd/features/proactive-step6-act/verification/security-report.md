---
feature: proactive-step6-act
phase: 5
mode: lean
generated_at: 2026-07-01
---

# Security Hardening Report — proactive-step6-act

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied; `security-results/manual-grep.txt` |
| test_step3_recipe.py static-grep regression guard | continuously enforced (= test_dispatcher_has_no_tmux_kill_or_stop + test_step3_recipe_has_no_tmux_kill) |

## RCE / Injection
| Pattern | Hits |
|---------|------|
| subprocess(..., shell=True) | 0 |
| os.system( | 0 |
| eval( | 0 |
| `\bsudo\b` (word-boundary) | 0 |

## Anti-Human-Touch (REQ-J8 inherited)
- telegram.org, hooks.slack.com, twilio, osascript, terminal-notifier,
  find-generic-password, SecKeychain → 0 hits

## INV-1 / INV-P1 LAYER C tmux protection
- proactive-loop-dispatch.py: grep `tmux\s+kill|--stop|--kill|kill-session|kill-server` → 0
- lib/step3_recipe.py: same grep → 0
- REQ-R1 production gate: `restart` invoked ONLY when issue_kind=='tmux_dead'
- REQ-R1a: `stale + restart` returns `stale-suppressed-INV-P1` with no subprocess
- Live production: gig kickstart did NOT restart gig-cli.sh (recipe=noop on healthy)

## REQ-R3 7-action sprint-4 scaffold-deferred set
Frozen constant SCAFFOLD_DEFERRED_ACTIONS = {kill_server, send_keys, login,
npm_install, git_checkout, escalate_via_bot2bot, noop}. Cross-referenced
exact match to health_check_v2.py:97-107 RECIPES non-restart actions.

## Summary

All security/anti-touch/INV-1/INV-P1 sweeps return 0 hits. The
production-safety gate on `restart` (issue_kind=='tmux_dead' AND
action=='restart') is unit-tested + regression-grep-tested + live-verified on
production gig. Sprint-4 carry: real action wiring for the other 7 recipes
(kill_server / send_keys / login / npm_install / git_checkout /
escalate_via_bot2bot / noop) — currently all scaffold-deferred with explicit
log lines.

## Spec-Gaming Surface
Phase 3 adversary caught:
- iter-1: 1 critical INV-P1 violation + 4 medium-low
- iter-2: 0 — PASS

The critical INV-P1 violation (= restart fires on healthy 'stale' tmux) was a
real bug only catchable by understanding the cross-module flow (recipe map
emits restart for two distinct Issue.kind values, but the dispatcher only
sees `action`). Cycle-2 added `issue_kind=='tmux_dead'` gate; cycle-3 added
regex regression guards so a future kill-helper addition fails CI.
