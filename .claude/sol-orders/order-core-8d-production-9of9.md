# CORE-a / 8d production 9/9 controlled run

You are the fresh Sol builder/executor for §10 row 8d. Work only in:

`/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`

Expected branch: `feature/lm33d-daily-preflight`; expected starting head: `904e158c8f8592b7a6d8c3fcd2f215c037f842b1`; PR: #330.

Read before acting:

1. root `AGENTS.md` and `/Users/anicca/.codex/RTK.md`;
2. canonical spec §9.5, §10 row 8d, §10.0, §10.2, §10.3;
3. handover `/Users/anicca/anicca-project/.claude/handovers/2026-07-21_0320_lm-ship-run.md`;
4. `.claude/sol-orders/order-core-8d-closed-final-review.md` and its log.

The local code gate is already independently PASS with blocker 0. Do not reopen or redesign it without concrete production evidence. The only goal of this order is a single bounded production-config preflight followed by one controlled run that truthfully produces a fresh report through the existing report builder.

## Hard safety / scope

- Do not spawn any agent. Do not merge, deploy application code, rotate secrets, change billing/payment routes, edit destructive schema, dial any phone, create a calendar event, or contact any third party.
- Never print, paste, commit, or persist raw tokens, email addresses, phone numbers, opaque IDs, one-time URLs, webhook secrets, or provider payloads. Use hashes/safe booleans only.
- The only authorized write side effects are exactly:
  1. one safe Telegram command `/panel core8d_<random nonce>` from Dais's existing MTProto user session to the bot identity returned by Bot API `getMe`;
  2. one controlled Resend email to the exact inbox identity already owned by Dais and configured as `GOG_ACCOUNT`, with the collector's no-action-required body.
- No phone call is authorized. The `call` dependency must be proved only by read-only Telnyx configuration/binding/auth-gate checks already implemented.
- Do not invoke `controlled-l3` more than once. First eliminate configuration failures with read-only inspection. If the one controlled run exits nonzero after either authorized send, preserve the generated artifact, record the exact safe failure class in §10, and stop; do not send again in this order.
- Preserve the historical artifact `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json` byte-for-byte.

## Required execution

1. Verify clean start, exact head/local/upstream/remote equality, PR #330 head, and historical artifact SHA-256. If the head differs, stop before providers and report it.
2. Run a no-side-effect configuration preflight against the real production environment. Inspect Railway/provider bindings without exposing values. Confirm all variables required by health/calendar/location/discovery/Gemini/Maps/Telegram/call/email exist and are internally consistent. Confirm Telegram exact webhook URL + required updates, Telnyx number/application/profile/webhook + `/ws` auth gate, scheduler cohort/location freshness, Composio calendar, Gemini Live + `gemini-2.5-flash`, Maps drive-or-transit, Resend key, pinned `gog`, and authenticated `GOG_ACCOUNT` inbox access.
3. For this one local process only, set `LM_CONTROLLED_EMAIL_ALLOWLIST` equal to the exact normalized `GOG_ACCOUNT` value without echoing either. Do not persist this allowlist to Railway unless current production operation already requires it; a one-shot collector guard should remain one-shot.
4. If a read-only preflight finds a mismatched existing webhook/provider binding, make only the smallest idempotent restoration to the already specified production URL/profile, capture before/after as safe hashes/booleans, and rerun read-only inspection. Do not change credentials or commercial configuration. If the correct target cannot be derived unambiguously from existing deployed config, stop without mutation and record the blocker.
5. Run the existing CLI exactly once in `controlled-l3` mode with a new timestamped output under `.vcsdd/features/life-manager-daily-preflight/evidence/`. Use the real production environment plus the one-shot allowlist. The existing fixed collector must perform the only two authorized sends. Do not hand-edit the artifact.
6. Check artifact mode 0600, schema/report binding, summary 9/9, dependency statuses, `overallStatus`, exit code, freshness, and absence of raw PII/secrets. Record SHA-256. Run a secret/PII scan that reports only safe counts.
7. If and only if the artifact is genuine 9/9 and exit 0, update the worktree copy of the canonical spec row 8d and §10.0 with the exact safe artifact path/hash, dependency result, TG request/reply hash refs, email provider/message hash refs, and call read-only proof. Mark `done` only with all 9 dependencies PASS. Otherwise keep `pending` and record the safe failure class and the false hypothesis tested.
8. Run fresh local regression verification (`npm test`, `npm run eval`, focused preflight tests, `git diff --check`). Stage only row-8d-owned files, commit, and push the branch. Do not merge PR #330. If no tracked file legitimately changes, do not create an empty commit.

## Final response contract

Return:

```text
RESULT: 9/9 | NOT-9/9 | BLOCKED-BEFORE-SEND
AUTHORIZED_SENDS: telegram=<0|1> email=<0|1> phone=0
ARTIFACT: <safe path or none>
SHA256: <hash or none>
DEPENDENCIES: <safe pass/fail names>
TESTS: <commands and counts/exits>
SPEC: <pending|done and exact evidence summary>
COMMIT: <hash or none>
PUSH: <remote equality result>
PR: #330 NOT MERGED
```

Do not call 8d done based on self-report, flags, or API 200 alone. A separate fresh reviewer will adjudicate the resulting artifact.
