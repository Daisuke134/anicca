# Original TDD Log Provenance (Not Yet Accepted)

These external logs are immutable provenance references only. They are outside this worktree feature directory and are not accepted VCSDD Phase 2 RED/GREEN evidence. Phase 2 must adjudicate or replay them after a fresh Phase 1c PASS and explicit strict-mode approval.

| Safe path | SHA-256 | Mode | Observed raw output locations |
|---|---|---:|---|
| `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-receipt-precision-fix.log` | `d9ee50aca6cdac74a99f32b7c8338d7ece7afc61079d2e0a5867189f176e761b` | `0644` | lines 1969–2103 contain a focused command result with exit 1 and `20 tests / 15 pass / 5 fail`; this is broader historical RED output, not accepted evidence |
| `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-receipt-precision-resume.log` | `6829a2ab6518149bea7975fd06e2d80eac8c6b42ec5688fa80df7c4d427d592b` | `0644` | lines 3163–3179 show two intended next-minute failures; lines 6227–6236 show the impossible-date test at `8 pass / 1 fail / EXIT=1`; lines 6737–6747 show focused `51/51` GREEN |

The observed chronology is limited to the raw command/output ordering inside each log. No claim is made here that the logs meet VCSDD freshness, snapshot binding, regression-baseline markers, or Phase 2 gate requirements.

## Preserved production evidence

| Repository path | SHA-256 | Mode |
|---|---|---:|
| `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T055121Z.json` | `6e69dd13086dfeb485ba1dd59e397b490ca187c072b153454603afbd92a455b4` | `0600` |
| `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json` | `a44cdc897eee741ac2ea6477b19e11c7e7281cbf7b240fd0723c1d63886243ac` | `0600` |

Neither JSON file is Phase 1 output. Both must remain byte-for-byte unchanged.
