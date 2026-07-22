# Phase 1 Production Findings

## Probe boundary

- Authorized side effect: one fresh `/panel` message sent through the pinned MTProto sidecar to the LM bot peer derived from Bot API `getMe`.
- Secret handling: the opaque URL existed only in process memory; it was never printed or persisted. The browser ended at query-free `/panel`.
- Stored evidence: Telegram request/reply hash refs, HTTP status, final path, query absence, and fresh/used classification only. Private runtime evidence is mode `0600` at `/tmp/lm-panel-control-center-production-probe.json`.

## Observation

| Fact | Result | Classification |
|---|---|---|
| Fresh token exchange | HTTP 200 final document, `/panel`, no query token | VERIFIED |
| Reuse of the same token | HTTP 403 | VERIFIED |
| Used-token response | literal `forbidden`, no Telegram renewal deep-link | VERIFIED |
| Telegram delivery | reply text contains a URL; current `sendPanelLink` supplies no inline keyboard | VERIFIED from source and probe |
| Current dashboard controls | connection chips and settings are rendered as non-interactive spans/text | VERIFIED from `panel-ui.js` |
| Current session scope | session lookup selects only `uid`, despite rows storing `uid + chat_id` | VERIFIED from `panel-auth.js` |
| Current fresh-403/RPC mismatch | not reproduced; the deployed claim RPC accepted the new token | VERIFIED negative finding |

## Root cause

- VERIFIED: used/expired/invalid token handling intentionally emits raw text in `handlePanelRequest`; there is no recovery UI or deep-link intent.
- VERIFIED: `sendPanelLink` puts the opaque URL in message text and does not pass `reply_markup.inline_keyboard` to Telegram.
- VERIFIED: `panel-api.js` only supports GET readers and `panel-ui.js` has no mutation handlers. Connections are reduced to booleans from `lm_users`, so honest action/error/unavailable states cannot be represented.
- VERIFIED: API auth resolves only `uid`; it does not carry and revalidate the session's `telegram_chat_id` against the scoped `lm_users` row.
- REASONED: the reported fresh 403 was either an already-consumed link or a transient deployment/RPC mismatch. The current production RPC contract is working, so implementation must add a regression test for the exact claim payload and treat a newly-created empty claim as a blocker without weakening single-use behavior.
- ASSUMED: no stable fresh-token defect remains in production until a second authorized reproduction proves otherwise. L3 must re-check after deployment.

## External grounding

- Telegram Bot API, https://core.telegram.org/bots/api — “Exactly one of the fields other than text … must be used to specify type of the button.” The dashboard link therefore uses an inline URL/WebApp button, with clickable URL fallback.
- Telegram Deep Linking, https://core.telegram.org/bots/features#deep-linking — “you can use the start parameter to automatically pass any value to your bot”. The expired-page link uses an allowlisted `start=panel` intent that mints a new single-use link.
- OWASP CSRF Prevention Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html — the guidance includes “Using Standard Headers to Verify Origin” and custom request headers. Panel mutations require same-origin validation plus a session-bound CSRF header.
- WAI-ARIA Switch Pattern, https://www.w3.org/WAI/ARIA/apg/patterns/switch/ — “Space … changes the state of the switch” and on/off state uses `aria-checked`. Native buttons/switch semantics and keyboard operation are mandatory.

