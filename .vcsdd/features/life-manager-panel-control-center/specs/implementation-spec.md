# Implementation Specification — Life Manager PANEL-0

Iteration: 2. Iteration 1 incorrectly excluded connector disconnect and is superseded by this contract.

## Data model

Migration `2026-07-21-lm-panel-control-center.sql` adds:

- `lm_panel_preferences(uid PK/FK lm_users, call_enabled boolean, notifications_enabled boolean, daily_automation_enabled boolean, delegation_enabled boolean, call_time_zone text, created_at, updated_at)`.
- `lm_panel_command_receipts(uid FK, chat_id, idempotency_key, request_hash, command_type, status, result jsonb, created_at, updated_at, PK(uid,idempotency_key))`.
- `lm_panel_oauth_states(state_hash PK, uid FK, chat_id, provider CHECK calendar, expires_at, used_at, created_at)`.

Existing `lm_users.call_language`, `wake_policy`, `calendar_provider`, `telegram_chat_id`, `phone`, `gmail_account_id`, `payout_destination`, and identity fields remain authoritative. Rollback drops only these three additive tables/indexes.

## Routes

- `GET /panel?t=...`: atomic token exchange only; redirects query-free.
- `GET /panel`: authenticated HTML or 401.
- `GET /api/panel/control-center`: one personalized identity/context/capability/settings model plus CSRF token.
- Existing GET endpoints remain compatible and side-effect free.
- `POST /api/panel/commands`: typed command, CSRF/origin/idempotency enforced.
- `GET /panel/oauth/calendar`: session + one-time user-bound OAuth state validation; renders outcome and does not claim provider success without ACTIVE readback.

## Typed commands

- `connection.start` `{provider: calendar|location|wallet}`.
- `connection.disconnect` `{provider: calendar}`.
- `setting.set` `{setting: call_enabled|notifications_enabled|daily_automation_enabled|delegation_enabled|call_language|wake_policy|call_time_zone, value}`.
- Permanent provider delete, Telegram disconnect, wallet mutation, payout mutation, Gmail connection, unsupported organ mutation, and phone/email side effects are absent from the allowlist.

Calendar provider adapter lists connected accounts with both `user_ids=<uid>` and `toolkit_slugs=googlecalendar`, selects exactly one account, and retains its nanoid only in server memory. Disconnect sends `PATCH /api/v3/connected_accounts/{nanoid}/status` with `{ "enabled": false }`; reconnect of a disabled account sends the same endpoint with `{ "enabled": true }`. Both require a subsequent user-filtered list/readback. Zero or multiple matching accounts fail closed; no provider success is inferred from the PATCH alone. Source: [Composio SDK](https://github.com/ComposioHQ/composio/blob/next/ts/packages/core/src/models/ConnectedAccounts.ts) / core quote: `connectedAccounts.disable('conn_abc123')` delegates to `updateStatus(nanoid, { enabled: false })`; `enable` delegates to `{ enabled: true }`. Source: [Composio migration guide](https://github.com/ComposioHQ/composio/blob/next/docs/content/docs/migration-guide/new-sdk.mdx) / core quote: disable/enable map to `PATCH /api/v3/connected_accounts/{nanoId}/status`.

## Capability truth

- calendar: one ACTIVE and enabled Composio account => connected with disconnect; one disabled/inactive account => action_required with reconnect; no account => action_required with connect; provider read failure, foreign account, or ambiguous matches => error with no destructive action.
- Telegram: exact chat binding => connected, otherwise error.
- location: live unexpired row => connected; otherwise action_required with Telegram instructions.
- call: phone present and call_enabled => connected; phone absent => action_required; preference off => action_required with turn-on action.
- email: unavailable under U1 regardless of stale `gmail_account_id`.
- wallet: payout destination present => connected; absent => action_required with Telegram instructions; never altered from panel.

## Idempotency and rollback

The command service claims `(uid,idempotency_key)` before mutation. Same request hash returns stored result. Different hash returns 409. DB preference updates use exact `uid` and an optimistic pre-state; provider failures never update user state. UI holds the old model and restores it on non-2xx/error.

## L3 runbook

1. After parent mergeability and deployment, derive LM bot peer via `getMe` without token output.
2. Send exactly one `/panel` with pinned MTProto sidecar; record only hash refs.
3. Open reply URL in existing daily-driver; assert final 200 `/panel`, no query token, personalized identity.
4. Reopen same URL; assert 403 human renewal page and clickable `start=panel` deep-link.
5. Toggle harmless notifications setting in panel; assert panel response and chat readback for same user; restore through chat intent and assert panel readback.
6. With isolated second test user/session, assert no response/action/OAuth-state overlap.
7. Start Composio calendar OAuth only for the isolated test user and verify callback/ACTIVE readback. In a future separately authorized L3 run, disable/re-enable only that isolated test connected account and verify inactive/ACTIVE readback. Do not disconnect Dais or alter real provider state in this turn.
8. Capture mobile/desktop semantic assertions and private screenshots; scan for tokens/PII.
