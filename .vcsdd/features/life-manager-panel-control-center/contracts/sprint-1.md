---
feature: life-manager-panel-control-center
sprint: 1
status: amended
negotiationRound: 1
---

# Sprint 1 Test Contract

- CRIT-001: A newly-created valid token produces 303 then authenticated 200 `/panel` with no query; the same/expired/invalid token produces 403 human renewal HTML.
- CRIT-002: `sendPanelLink` sends an inline clickable button and no duplicate opaque token in ordinary message text/log output.
- CRIT-003: two users receive different personalized data; neither can read, mutate, start OAuth, or receive chat results for the other.
- CRIT-004: chat and panel adapters call one typed command service and converge to byte-equivalent setting/result state.
- CRIT-005: calendar/Telegram/location/call/email/wallet states are honest; Gmail/unsupported connectors never report connected or expose fake actions.
- CRIT-006: POST mutation rejects missing/bad Origin, CSRF, content type, action, fields, and idempotency; duplicate same payload is replayed once and changed payload is 409.
- CRIT-007: provider/persistence failure reports failure and leaves/restores prior state.
- CRIT-008: mobile/desktop DOM contains no non-interactive visible action; every visible action has a native handler and accessible keyboard semantics.
- CRIT-009: migration and rollback are additive/user-keyed; GET is side-effect free; scans find no opaque token, secret, raw PII, or hardcoded Dais/default connected state.
- CRIT-010: focused/full tests and eval pass; changed-module line/function coverage are each >=90%; browser fixture smoke passes.
- CRIT-011: deterministic EN/JA chat grammar and native panel controls expose Calendar connect/reconnect/disconnect through the same typed service.
- CRIT-012: Calendar disconnect resolves only the authenticated user's connected-account nanoid, uses official reversible Composio disable, is idempotent, and reports success only after inactive readback.
- CRIT-013: tenant mismatch, ambiguous ownership, provider failure, or failed readback fails closed and preserves the prior ACTIVE/inactive visible state; no external provider disconnect occurs in local tests.
