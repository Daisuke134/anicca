# CORE-a / 8d method-2 one-shot production 9/9 controlled run

You are a fresh `gpt-5.6-sol` executor in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, branch `feature/lm33d-daily-preflight`, exact expected head `58846034b4505f585bd8b4ea3fbcaa04c38e31bc`, PR #330. Do not spawn another agent.

This order MUST NOT run unless `.claude/sol-orders/logs/core-8d-receipt-fresh-review.log` ends with `VERDICT: PASS`, `BLOCKERS: 0`, and `CONTROLLED-RUN JUDGMENT: AUTHORIZED`. If any condition is absent, stop before all providers with `BLOCKED-BEFORE-SEND`.

Read canonical spec §9.5, §10 row 8d, §10.0, §10.2, §10.3; the VCSDD feature artifacts; the prior production order/log; and the fresh review verdict. This is independent method 2 after the false hypothesis that gog minute timestamps can be compared as exact milliseconds.

## Hard scope and safety

- No merge/deploy/application code change, schema mutation, secret rotation, billing change, calendar event, wallet action, phone call, or third-party contact.
- Authorized write side effects are exactly one Telegram `/panel core8d_<new random nonce>` from Dais's existing MTProto session to the bot identity proven by Bot API `getMe`, and exactly one controlled Resend email to the exact Dais-owned inbox configured as `GOG_ACCOUNT`, using the existing no-action-required proof body.
- Phone sends/dials = 0. Call dependency is read-only configuration/auth/binding proof only.
- Never print/persist raw token, address, phone, nonce, opaque ID, provider payload, one-time URL, webhook secret, or error. Safe booleans, failure classes, counts, and hashes only.
- Invoke `controlled-l3` exactly once. Read-only preflight comes first. If either authorized send happens and the run fails, preserve any generated artifact, record the safe failure class and false hypothesis in §10, then stop. No second invocation, resend, artifact edit, or manual PASS.
- Preserve historical artifact `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json` byte-for-byte, mode 0600, SHA-256 `a44cdc897eee741ac2ea6477b19e11c7e7281cbf7b240fd0723c1d63886243ac`.

## Required execution

1. Prove clean worktree and exact local/upstream/origin/PR head equality at `58846034b`; prove historical artifact hash/mode. Stop before providers on mismatch.
2. Run bounded no-send production-config preflight for all nine dependencies. Confirm health, calendar/Composio, fresh location/discovery, Gemini Live + `gemini-2.5-flash`, Maps, Telegram exact webhook + required updates + zero/provider-error state, Telnyx number/application/profile/call-control webhook + `/ws` auth gate, Resend, pinned gog, and authenticated owned inbox. Do not expose values.
3. Only if a previously specified external binding has drifted and its correct target is unambiguous from deployed config, make the smallest idempotent restoration and record safe before/after hashes/booleans. No credential/commercial changes. Otherwise stop before sends.
4. For this process only, bind `LM_CONTROLLED_EMAIL_ALLOWLIST` to the exact normalized `GOG_ACCOUNT` without echoing or persisting either.
5. Invoke the existing `controlled-l3` CLI once with a new timestamped evidence path. Let the fixed production collectors perform the only two authorized sends. Do not hand-edit output.
6. Verify generated artifact mode 0600, schema/report binding, freshness, `overallStatus`, summary 9/9, each dependency PASS, exact controlled send counts, safe hash refs, and zero raw PII/secret/URL/error leakage. Record SHA-256 and safe counts.
7. On genuine 9/9 only, update worktree canonical spec row 8d and §10.0 with exact safe artifact path/hash, TG request/reply hash refs, email provider/receipt hash refs, read-only call proof, tests, commit, and keep PR unmerged. Mark done only when the generated artifact itself proves all 9. On failure, keep pending and record failure class/false hypothesis.
8. Run focused preflight tests, `npm test`, `npm run eval`, `git diff --check`. Stage only 8d-owned source-of-truth/evidence/spec files, commit, push, and verify remote equality. Never merge PR #330.

Return exactly:

```text
RESULT: 9/9 | NOT-9/9 | BLOCKED-BEFORE-SEND
AUTHORIZED_SENDS: telegram=<0|1> email=<0|1> phone=0
ARTIFACT: <safe path or none>
SHA256: <hash or none>
DEPENDENCIES: <safe pass/fail names>
TESTS: <fresh counts/exits>
SPEC: <pending|done with safe evidence>
COMMIT: <hash or none>
PUSH: <remote equality>
PR: #330 NOT MERGED
```

The result remains provisional until a separate fresh final artifact reviewer passes it.
