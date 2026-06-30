---
feature: earn-shared-skeleton
phase: 5
mode: lean
sprint: 1
generated_at: 2026-07-01T05:10:00+09:00
---

# Security Report — earn-shared-skeleton sprint-1

## Tooling

Tools attempted / applied:

| Tool | Tier | Status | Notes |
|------|------|--------|-------|
| Manual grep sweep | 0 | applied | 5 RCE/injection patterns probed across all source |
| anti-J8 grep sweep | 1 | applied | 7 human-touch hostname patterns probed |
| `python3 -m bandit` | 1 | unavailable | PEP 668 blocks system install of bandit on macOS Homebrew; `pipx install bandit` would be required. Manual sweep substituted. |
| Semgrep | 2 | not run | optional for lean mode |
| nacl.signing real-key verify | 1 | scope-deferred to sprint-2 | current sprint ships fixture-protocol sha256-mix per PROP-E5 verification matrix |

Captured outputs under `verification/security-results/`:
- `bandit-2026-07-01.txt` — install attempt log (PEP 668 block recorded)
- `manual-grep-2026-07-01.txt` — manual sweep results

## Summary

### RCE / Injection Surface Audit

Patterns probed (= would indicate AI-slop or attack-by-source):

| Pattern | Hits in production source | Verdict |
|---------|---------------------------|---------|
| `subprocess.*shell=True` | 0 | clean |
| `os.system(` | 0 | clean |
| `eval(` | 0 | clean |
| `exec(` | 0 | clean |
| `<<PYEOF` (Python heredoc in shell) | 0 | clean (refactored from iter-2 fix) |
| `<<EOF` with `$` interpolation | 0 | clean |

iter-2 critical RCE finding (FIND-2-001: shell→Python heredoc injection) is closed: all
4 shell scripts that invoke Python (`loop-healthcheck.sh`, `self-recover.sh`, `loop-roi.sh`,
`cross-learn-share.sh`) now use ENV VAR pattern — they `export ANICCA_*=<value>` then
`exec python3 <name>-dispatch.py`. The Python dispatchers read `os.environ.get(...)`;
untrusted bytes never pass through `bash → """..."""` string interpolation.

Verified via grep over `skills/_shared/*.sh`:
```
grep -nE "<<PYEOF|python3 -c|python3 - <<" skills/_shared/*.sh
# → no hits
```

### Anti-Human-Touch (REQ-J8) Audit

Patterns probed (= production code MUST NOT contain any of these as a CALL site):

| Pattern | Hits in production source | Verdict |
|---------|---------------------------|---------|
| `api.telegram.org` | 0 call sites | clean |
| `hooks.slack.com` | 0 call sites | clean |
| `twilio` | 0 call sites | clean (only mention is in `group_j._HUMAN_TOUCH_PATTERNS` = the BLOCKLIST itself) |
| `osascript` | 0 call sites | clean (only in blocklist) |
| `terminal-notifier` | 0 call sites | clean (only in blocklist) |
| `find-generic-password` | 0 call sites | clean (only in blocklist) |
| `security add-generic-password` | 0 call sites | clean |
| `gh issue create --label escalation` | 0 call sites | clean (only in blocklist regex) |

All hits for these patterns under `skills/_shared/lib/group_j.py` are confined to the
blocklist source (lines 46-67) which DEFINES the patterns to REJECT — these are anti-patterns
the static analyzer flags, not production calls.

Production-source verification:
```
grep -rE "telegram|slack|twilio|osascript|find-generic-password" \
   skills/_shared/lib/*.py skills/_shared/*.sh \
   | grep -vE "BLOCKLIST|blocklist|_HUMAN_TOUCH_PATTERNS|# |REQ-J8|invariant"
# → no hits
```

REQ-J8 anti-human-touch invariant: VERIFIED ENFORCED.

### Trust-Anchor Audit

- `anicca-bot.pub` — fixture base64 ed25519 pubkey (44 chars → 32 bytes). REAL nacl.signing
  signature verification is sprint-2 commitment per scope-cut table. Sprint-1 ships
  fixture-protocol (sha256(pinned + pubkey) truncated to 64 bytes) which is testable but
  NOT cryptographically secure against a determined attacker — this limitation is honestly
  declared in the verification-architecture.md PROP-E5 row.
- `payout-endpoint-allowlist.json` — 5 MVP platforms with per-entry `unit` + `comparison`
  declarations. Schema validated by JSON load + `verify_earn_event` allowlist lookup.
- `hook-modules-allowlist.txt` — 4 entries (dotenv, zx, execa, @anthropic-ai/claude-code-hooks).
  Sprint-2 commitment: `trusted-authors.json` powers auto-allowlist expansion via REQ-J3.
- `trusted-authors.json` — 7 trusted npm authors + 4 org namespaces + threshold config.

### Spec-Gaming / AI-Slop Surface Audit

Phase 3 adversary explicitly probed for these signals over 3 iterations (sprint-1 total
findings: 18 + 5 + 0 = 23 findings raised, 10 fixed in-sprint, 13 documented as sprint-2
commitments with concrete file-path + acceptance criteria, 0 silently incomplete after
iter-3 PASS).

The Sprint-1/Sprint-2 Scope Cut table in `specs/behavioral-spec.md` enumerates every
deferred commitment. Hand-waving language ("production wires this", "real impl") was
explicitly hunted by the iter-2 adversary (FIND-2-004) and replaced with concrete
acceptance criteria in iter-2 fix.

## Tooling — Notes on Sprint-2

Sprint-2 verification additions:
- Install `bandit` via `pipx install bandit` and run as part of CI.
- Install `semgrep` and ship a `semgrep.yml` rule pack tuned to REQ-J8 violations
  (blocks Telegram/Slack/Twilio/osascript/Touch-ID call sites at PR time).
- Replace fixture-protocol PROP-E5 signature with real ed25519 via `python -m nacl` +
  CI-managed `anicca-bot` keypair.
