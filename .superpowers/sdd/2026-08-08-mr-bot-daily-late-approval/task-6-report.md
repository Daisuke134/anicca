# Task 6 report — DAILY Gate0 production receipt recovery

STATUS: DONE_WITH_CONCERNS

## Scope and safety boundary

This recovery owns only Task 6 of `2026-08-08-mr-bot-daily-late-approval`:
deployment identity, controlled-event evidence, and the DAILY row #5 receipt. The
worktree currently contains two pre-existing untracked geocode test files; they are
preserved and are outside this task.

Before any external side effect, this run audits Railway deployment identity,
Supabase late-approval drafts/claims/receipts, Resend provider sends, and Telegram
delivery state for the controlled-test window. No environment variables are changed
and no third-party send is performed by this recovery unless an already-existing
production receipt proves that assertion without replay.

## Initial checkpoint

- Worktree branch: `feat/lm-daily-late-approval`.
- `HEAD`, `canonical/main`, and `canonical/feat/lm-daily-late-approval` all point to
  `dcd9ad9ad` (latest canonical/main supplied for this gate).
- The real-event HTML fixes `62d239b36` and `6004c7028` are ancestors of HEAD.
- No production state has been mutated in this recovery before the read-only audit.
- Existing untracked files preserved: `apps/mr-bot/lib/geocode-cache.test.js`
  and `apps/mr-bot/test/mobile-geocode-cost-guard.test.js`.

Next: complete the redacted read-only audit, then run only missing local/production
assertions that do not violate the no-new-third-party-send constraint.

## Read-only production audit (before any new side effect)

Controlled window used for the initial deployment readback: deployment start
`2026-08-08T11:42:28Z` through the audit time. The existing controlled event ledger
was also checked all-time because its approved event began before that deployment.

- Railway production service `life-call`: deployment `e284947e-fbc0-451a-943c-6d28c186395f`,
  status `SUCCESS`, `main`, repo `Daisuke134/life-manager`, exact commit
  `dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b`; `/health` returned HTTP 200 with
  `ok=true`, `service=life-call`, `build=lm2a-webhook-retry-v1`.
- Supabase direct PostgREST reads for the four late tables returned HTTP 403 by
  design (direct table access is revoked). Read-only Management SQL aggregation
  returned: drafts 6 total (`awaiting_decision=1`, `do_not_send=1`, `sent=1`,
  `recipient_missing=2`, `recipient_ambiguous=1`); decisions 2 (`send=1`,
  `do_not_send=1`); delivery claims 1; provider receipts 1. The sent draft has
  `telegram_receipt_status=sent`, one Telegram receipt message id, and two bounded
  Telegram receipt attempts. No duplicate `(uid,event_key)` groups exist.
- Timeline (all timestamps UTC, no IDs/recipient values stored here): resolved
  draft at `11:37:36`; `send` decision at `11:39:45`; delivery claim at
  `11:39:45`; provider receipt at `11:39:46`; sent/Telegram receipt durable
  update at `11:43:41`. Railway has one later idempotent callback replay at
  `11:43:47` (`decision=send`, `ok=true`, `sent=true`), consistent with the
  already-sent row; no second claim or provider receipt exists.
- The terminal `do_not_send` draft was created at `11:26:39`, updated at
  `11:29:46`, and has no provider or Telegram receipt. Later production ticks
  produced no duplicate event group. Missing-recipient drafts (2) and the
  ambiguous-recipient draft (1) have no approval-card message id, decision,
  claim, provider receipt, or Telegram receipt; therefore no send control was
  created for those states.
- Resend read-only `GET /emails?limit=100` and `GET /emails/<redacted-provider-id>`
  both returned HTTP 401 because the production key is restricted to sending.
  This is a provider-permission limitation; the durable Supabase provider receipt
  count is 1, and no Resend send endpoint was called by this recovery.
- Telegram read-only `getMe` and `getWebhookInfo` returned HTTP 200; webhook is
  configured, `pending_update_count=0`, `last_error_date=null`, and the allowed
  updates include callback queries. The receipt chat `getChat` returned HTTP 200.

No new external send, environment change, or production mutation was performed by
this recovery during the audit.

## Verification

After restoring `node_modules` with `npm ci --ignore-scripts --no-audit --no-fund`
(no package-file changes), the requested focused commands are green:

```text
cd apps/mr-bot && node --test lib/late-recipient-resolver.test.js lib/late-approval.test.js lib/late-notice.test.js test/late-approval-http-contract.test.js
  66 tests, 66 pass, 0 fail

cd apps/mr-bot && node --test test/telegram-callback-http-contract.test.js lib/telegram-onboard.test.js
  33 tests, 33 pass, 0 fail

cd apps/mr-bot && git diff --check
  PASS
```

`npm test` exits 1 only at the pre-existing legacy-path scan. Its failing sub-suite
is `scripts/scan-legacy-paths.test.js`: 17 pass, 1 fail because the two unrelated
Connector boot/deploy scripts still contain `${HOME}/.openclaw/.env` references.
The late approval, daily journey, Telegram callback, and all earlier full-suite
stages are green. No connector, mobile, or geocode file was changed.

## Final gate disposition

`DONE_WITH_CONCERNS`: all missing Task6 assertions are already proven by the existing
controlled production event and read-only provider/Telegram/database evidence; no
external send was repeated. The deployment identity is exact and live, the durable
no-send and missing/ambiguous controls are terminal, and the approved path has one
provider receipt plus one Telegram receipt despite callback replay. Remaining gaps
are the restricted Resend read permission and the unrelated legacy-path baseline
failure described above. No Task6 implementation defect is observed.

Commit/push completed: `ac713cd8b` (`docs(mr-bot): record daily late approval
receipt`) pushed to `canonical/feat/lm-daily-late-approval`.

The two pre-existing untracked geocode test files remain untouched.
