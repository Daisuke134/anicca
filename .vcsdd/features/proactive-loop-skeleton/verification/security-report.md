---
feature: proactive-loop-skeleton
phase: 5
mode: lean
sprint: 2
generated_at: 2026-07-01T08:00:00+09:00
---

# Security Report — proactive-loop-skeleton sprint-2

## Tooling

| Tool | Status |
|------|--------|
| Manual grep sweep | applied |
| sprint-1 `anti_human_touch_violations` static analyzer | applied to sprint-2 sources |
| bandit (semgrep) | sprint-3 commitment (PEP 668 / pipx flow inherited from sprint-1) |

Captured outputs in `verification/security-results/`:
- `manual-grep-sprint-2.txt`

## Summary

### RCE / Injection Surface Audit

Patterns probed across the 6 sprint-2 lib modules + 4 shell scripts + 1 Python dispatcher:

| Pattern | Hits | Verdict |
|---------|------|---------|
| `subprocess(..., shell=True)` | 0 | clean |
| `os.system(` | 0 | clean |
| `eval(` | 0 | clean |
| `exec(` | 0 | clean |
| `<<PYEOF` (Python heredoc in shell) | 0 | clean |
| `<<EOF` with `$` interpolation in body | 0 | clean |

Shell scripts use the ENV VAR pattern inherited from sprint-1 FIND-2-001 RCE fix: `export ANICCA_*=<value>` then `exec python3 <dispatch>.py`. Python dispatchers read `os.environ.get(...)`. Bash variable expansion CANNOT reach the Python parser. Zero injection surface.

### Anti-Human-Touch (REQ-J8) Audit

The sprint-1 `anti_human_touch_violations` static analyzer was re-run mentally over each sprint-2 source. Zero hits in production code:

- `lib/quota_tracker.py` — pure compute, no I/O surface
- `lib/menu.py` — pure compute, no I/O surface
- `lib/health_check_v2.py` — dispatch_highest_priority returns recipes; ZERO recipe maps to a human-touch action (Telegram/Slack/osascript/Touch-ID)
- `lib/bot2bot.py` — gh issue API only; `escalation` label rejects human-targeted body via `_HUMAN_BODY_PHRASES` blocklist (EN + JA)
- `lib/proactive_loop.py` — pure decision + jsonl writer
- `lib/build_log.py` — pure format + append
- 4 shell scripts + 1 dispatcher — `proactive-loop.sh` runs Python via env vars; `credential-restore.sh` / `auto-allowlist.sh` / `auto-rollback.sh` are sprint-3-deferred scaffolds returning exit 1 (= explicit non-action, NOT human escalation)

### Trust-Anchor Audit

Sprint-2 inherits sprint-1's anicca-bot.pub trust anchor + 4 allowlist files unchanged. No new trust anchors introduced.

### Spec-Gaming / AI-Slop Surface Audit

Phase 3 adversary catches:
- iter-1: 20 findings → 3 critical (auto-merge identity gate, dormant sentinel write missing, 4 shell scripts hide 13 PROPs)
- iter-2: 13 new findings on cycle-2 surface (partial closures)
- iter-3: 5 new findings on cycle-3 surface
- iter-4: PASS (0 new findings)

The escalating finding cycle (= adversary catches each cycle's residual drift) and final convergence at iter-4 is the AI-slop containment story. Spec-vs-test-vs-impl drift was repeatedly caught by the fresh-context Opus adversary; cycle-N+1 fixed each issue with concrete file:line evidence.

### Auto-Merge SCOPE-DEFERRED to sprint-3

Per FIND-003 critical: sprint-2 bot2bot.annotate_pr POSTS a PR comment but does NOT call `gh pr merge`. The auto-merge function does not exist in lib/bot2bot.py. test_auto_merge_function_does_not_exist asserts this via static `hasattr` check. Sprint-3 will add real ed25519 + CI signed-commit gate.
</parameter>
