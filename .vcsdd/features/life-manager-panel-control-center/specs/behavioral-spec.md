# Behavioral Specification — Life Manager PANEL-0

Status: iteration 2 approved for local implementation; production remains `pending — local GREEN`.

## Iteration 2 alignment correction

Iteration 1 was incomplete because it omitted Calendar disconnect from the EARS requirements, closed chat grammar, typed command allowlist, UI actions, and sprint criteria, and the implementation spec explicitly excluded all disconnects. That contradicted canonical root §9.9 (`Connect / Reconnect / Disconnect / Turn on / Turn off`) and the HARD correction in the original order. Iteration 2 makes the real Composio Calendar lifecycle mandatory while retaining Telegram as the non-destructive authentication anchor.

Provider contract decision: PANEL-0 Calendar Disconnect is the reversible Composio connected-account **disable** operation, never permanent delete. Source: [Composio ConnectedAccounts SDK](https://github.com/ComposioHQ/composio/blob/next/ts/packages/core/src/models/ConnectedAccounts.ts) / core quote: “Disable a connected account” and `updateStatus(nanoid, { enabled: false }, requestOptions)`. Source: [Composio migration guide](https://github.com/ComposioHQ/composio/blob/next/docs/content/docs/migration-guide/new-sdk.mdx) / core quote: `POST /api/v1/connectedAccounts/{connectedAccountId}/disable` maps to `PATCH /api/v3/connected_accounts/{nanoId}/status`. Permanent delete is rejected for PANEL-0 because the same SDK says it “cannot be undone and will revoke any access tokens”.

## Scope and actors

An authenticated Telegram-linked user operates the same allowlisted command layer from chat or `/panel`. Static labels are shared; all identity, context, capability, connection, setting, gate, action, and result data is scoped by the authenticated pair `{uid, telegram_chat_id}`.

## EARS requirements

- REQ-001: WHEN `/panel` is requested in Telegram, the system SHALL send one inline clickable dashboard button where supported and a clickable URL fallback, without logging or duplicating the opaque token outside the button/fallback payload.
- REQ-002: WHEN a valid fresh five-minute token is claimed once, the system SHALL atomically bind it to its stored `uid + chat_id`, create a separate HttpOnly Secure SameSite=Lax session, and redirect to query-free `/panel`.
- REQ-003: WHEN a token is used, expired, malformed, or invalid, the system SHALL return HTTP 403 with a human HTML page containing exactly one clickable Telegram deep-link for `start=panel`; it SHALL NOT reactivate or reuse the token.
- REQ-004: WHEN the bot receives `/start panel`, `/panel`, “open dashboard”, or Japanese equivalents, the system SHALL create a new single-use link for the chat's linked user; an unlinked chat SHALL receive a concise failure without a token.
- REQ-005: WHILE a panel session is valid, every request SHALL resolve and revalidate the exact stored `uid + chat_id`; user-controlled query/body identifiers SHALL NOT change scope.
- REQ-006: WHEN two fixture users read panel state, the system SHALL return different identity/context/connections/settings derived only from each user's rows/provider state.
- REQ-007: The system SHALL represent calendar, Telegram, location, call, email, and payout/wallet with one of `connected`, `action_required`, `unavailable`, or `error`, plus an honest reason and zero or more allowlisted actions.
- REQ-008: Calendar SHALL reuse the existing Composio Google Calendar connected-account contract. It SHALL report connected only for an ACTIVE account/provider truth and SHALL bind OAuth state to `uid + chat_id`.
- REQ-008A: WHEN the authenticated user disconnects an ACTIVE Calendar account, the shared command service SHALL resolve only that user's Google Calendar connected-account nanoid, call the official Composio disable/status operation, and report success only after user-scoped readback is inactive. Repeated disconnect with a new idempotency key against already-inactive state SHALL be a provider-free success.
- REQ-008B: WHEN Calendar reconnect is requested for a disabled account, the service SHALL use the official enable/status operation and report connected only after ACTIVE readback; otherwise it SHALL use the existing OAuth start gate. Provider failure or mismatched/ambiguous account ownership SHALL fail closed and preserve the prior visible state.
- REQ-009: Gmail reading SHALL report `unavailable` while U1 remains true and SHALL never expose a connect action or claim success.
- REQ-010: Location and payout/wallet MAY expose only Telegram setup-instruction actions; they SHALL NOT mutate location, wallet, or payout provider state from the panel.
- REQ-011: Telegram SHALL be `connected` only when the session chat equals the current user's `telegram_chat_id`; it SHALL have no destructive disconnect action in PANEL-0.
- REQ-012: Call enabled/policy, call language/timezone, notification automation, DAILY automation, and delegation SHALL be real per-user settings. Unsupported organ controls SHALL render `unavailable`, not decorative toggles.
- REQ-013: WHEN a panel mutation is submitted, the system SHALL require POST, same-site session, allowed Origin, session-bound CSRF token, JSON content type, an allowlisted typed command, and an idempotency key.
- REQ-014: WHEN the same user repeats an idempotency key with the same command payload, the system SHALL return the original result without a second mutation/provider call; a different payload SHALL be rejected.
- REQ-015: WHEN a provider or persistence mutation fails, the system SHALL return failure, keep/restore the prior visible state, and SHALL NOT report success.
- REQ-016: WHEN a deterministic chat phrase matches an allowlisted connection/toggle intent in English or Japanese, the parser SHALL dispatch the same typed command service used by panel POST. Ambiguous/unsupported input SHALL list available actions without a generic question.
- REQ-017: WHEN a chat command completes, only that user's chat SHALL receive a concise success/failure or required-gate report; no other user SHALL be notified.
- REQ-018: The panel SHALL update the affected card/setting immediately from the command result and provide per-control loading, success, and failure states with rollback on failure.
- REQ-019: Every visible action SHALL be a native interactive element with an installed handler, disabled state when unsupported/in-flight, focus visibility, accessible name/state, and keyboard operation at mobile and desktop widths.
- REQ-020: GET routes SHALL be side-effect free. Logs, snapshots, URLs after exchange, and error bodies SHALL contain no opaque token, provider secret, raw PII, or foreign-user state.
- REQ-021: An additive migration SHALL create user-keyed preferences, OAuth-state hashes, and command receipts; rollback SHALL drop only those new objects and SHALL NOT delete `lm_users` or provider data.
- REQ-022: The feature SHALL remain `pending — local GREEN` until its stacked parent is mergeable and L3 proves the real Telegram, browser, tenant, and supported OAuth flow after deployment.

## Closed chat grammar

| Intent | English forms | Japanese forms | Typed command |
|---|---|---|---|
| panel | `/panel`, `open dashboard`, `get dashboard link` | `ダッシュボードを開いて`, `パネルを開いて` | `panel.open` |
| calendar connect | `connect calendar`, `reconnect calendar` | `カレンダーを接続`, `カレンダーをつないで` | `connection.start(calendar)` |
| calendar disconnect | `disconnect calendar`, `disconnect my google calendar` | `カレンダーを切断`, `カレンダーを解除して` | `connection.disconnect(calendar)` |
| call off/on | `turn calls off/on`, `disable/enable calls` | `電話を止めて/再開して`, `コールをオフ/オン` | `setting.set(call_enabled)` |
| notifications off/on | `turn notifications off/on` | `通知をオフ/オン` | `setting.set(notifications_enabled)` |
| DAILY automation off/on | `turn daily automation off/on` | `デイリー自動化をオフ/オン` | `setting.set(daily_automation_enabled)` |
| delegation off/on | `turn delegation off/on` | `委任をオフ/オン` | `setting.set(delegation_enabled)` |
| language | `calls in English/Japanese` | `電話を英語/日本語にして` | `setting.set(call_language)` |

## UI states

Every section supports `loading`, `ready`, `empty`, and `error`. Every supported action supports `idle`, `loading`, `success`, and `failure`; failure restores the pre-action model. Unsupported actions render explanation text without a button. Mobile uses a single column with 44px minimum targets; desktop uses the existing editorial grid without changing action semantics.
