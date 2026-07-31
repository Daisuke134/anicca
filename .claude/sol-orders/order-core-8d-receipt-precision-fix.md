# CORE-a / 8d method 2 — gog receipt precision TDD fix

Fresh Sol corrective builder in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, branch `feature/lm33d-daily-preflight`, expected starting head/PR #330 head `f6129abb5eff30848ed9296abef1cb3d2fe7e977`.

Read root rules/RTK, canonical spec §9.5/§10 row 8d/§10.0/§10.2/§10.3, the worktree VCSDD feature, and `.claude/sol-orders/logs/core-8d-production-9of9.log`. Do not spawn any agent.

## Scope and safety

This order is build + local verification only. Do not call Railway/provider APIs, Telegram, Resend, gog inbox, Telnyx, Gemini, Maps, Composio, Supabase, or any network. Do not send email/TG, dial, deploy, merge, change provider config, or create a new production artifact. Preserve the historical artifact byte-for-byte. Keep row 8d pending.

Verified failure to fix:

- The single prior controlled run sent TG=1/email=1/phone=0 and both exact receipts were read back.
- `gog` returned the email date as `YYYY-MM-DD HH:MM` (minute precision). The exact same-run nonce receipt's minute bucket contained the send instant, but `findReceipt` and `validateEmailObservation` compared its lower bound to millisecond `sentAtMs`, classified `email_receipt_stale`, and the CLI exited before report generation.
- False hypothesis already recorded: `gog message date is precise enough for a strict millisecond comparison`.

## TDD contract

1. Verify clean exact head/local/upstream/origin/PR equality and historical SHA-256 before edits.
2. Use repository/source search to locate the exact gog date-output contract; if external source is needed, use `gh` against the official gog repository and record a short primary-source citation. Never print inbox data.
3. RED first. Add focused tests proving:
   - an exact nonce receipt whose minute-precision interval contains `afterMs/sentAtMs` is accepted;
   - the immediately previous minute and any interval wholly before the send instant remain stale/rejected;
   - future/malformed dates, nonce mismatch, missing id, provider failure, and >15-minute stale evidence remain fail-closed;
   - second/timezone-precise timestamps retain strict ordering;
   - no caller-controlled precision or proof can be injected into production;
   - one-send budgets and fixed production collectors remain unchanged.
   Capture the RED exit/count in VCSDD evidence.
4. Implement the smallest truthful interval model. Do not fabricate a receipt timestamp by overwriting it with `afterMs`. Represent provider precision explicitly (for example safe lower/upper bounds or a fixed parser-derived precision), accept only when the provider time interval overlaps/contains the same-run send instant, and keep the 15-minute freshness/nonce/provider-ID requirements. Unknown formats fail closed.
5. Ensure report/evidence serialization contains only safe booleans/hash refs and no raw date, nonce, email, provider ID, or PII. Do not loosen `validateEmailObservation` into success based solely on booleans.
6. GREEN: focused receipt/collector/provenance/wiring/CLI tests, full `npm test`, `npm run eval`, changed-module line/function coverage >=90%, `git diff --check`, source scans proving production transport remains closed, historical artifact SHA/mode unchanged, secret/PII scan safe.
7. Update worktree spec row 8d/§10.0 with method-2 RED/GREEN facts but keep `pending`; no new L3 claim. Stage only 8d-owned files, commit, push, and verify local=upstream=origin=PR head. Do not merge.

Final response:

```text
RESULT: LOCAL-GREEN | FAIL
RED: <command/count>
GREEN: <commands/counts/coverage>
PRODUCTION_SIDE_EFFECTS: telegram=0 email=0 phone=0
HISTORICAL_SHA: <unchanged hash>
SPEC: pending
COMMIT: <hash>
PUSH: <equality>
PR: #330 NOT MERGED
```

Main will run a separate fresh artifact-only review before authorizing a second controlled production attempt.
