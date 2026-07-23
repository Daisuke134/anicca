# Verification Architecture — Life Manager PANEL-0

## Purity boundary

- Pure core: typed command validation, deterministic bilingual intent parsing, connection-state derivation, UI view-model shaping, CSRF/origin comparison, result formatting.
- Effectful shell: Supabase REST reads/writes, Composio connected-account calls, Telegram sends, HTTP request/response, cryptographic random generation.
- Rule: panel and Telegram adapters call `executeUserCommand(scope, command, deps)`; neither adapter writes DB/provider state directly.

## Proof obligations

| ID | Requirement | Tier | Required | Evidence |
|---|---|---:|---:|---|
| PROP-001 | REQ-002/003 | 1 | true | atomic fresh/used/expired claim tests and migration RPC assertion |
| PROP-002 | REQ-005/006/017 | 1 | true | two-user read/mutate/OAuth/chat isolation tests |
| PROP-003 | REQ-007–012 | 1 | true | capability matrix and unsupported-provider tests |
| PROP-004 | REQ-013/014 | 1 | true | CSRF/origin/schema/idempotency tests |
| PROP-005 | REQ-015/018 | 1 | true | provider/DB failure and UI rollback tests |
| PROP-006 | REQ-016 | 1 | true | English/Japanese closed grammar convergence tests |
| PROP-007 | REQ-019 | 0 | true | DOM semantic assertions at 390px and 1280px plus browser fixture smoke |
| PROP-008 | REQ-020 | 1 | true | secret/PII/raw-log scan and query-token absence assertion |
| PROP-009 | REQ-021 | 0 | true | forward/rollback SQL structural assertions |
| PROP-010 | REQ-008A/008B | 1 | true | fixture-only Composio disable/enable, tenant filter, duplicate receipt, provider failure, and ACTIVE/inactive readback tests |

## Test layers

- L1 focused: Node test runner for auth, command core, API, Telegram parser, UI semantics, migration.
- L1 regression: full `npm test`, `npm run eval`, `git diff --check`.
- Coverage: `node --test --experimental-test-coverage` on changed modules; line and function coverage each >=90%.
- Browser fixture: authenticated fixture server in existing CloakBrowser/daily-driver, desktop and mobile viewports, native click/keyboard operations, no dead action.
- L3 deferred: one real fresh Telegram link; harmless notification/call-enabled roundtrip panel→chat readback and chat→panel readback; isolated second user; test-user Composio OAuth start/callback. A later separately authorized run may disable/re-enable only an isolated test account. No phone call, email, Dais provider disconnect, payout/wallet, or destructive schema action.

## Security invariants

1. Scope is an immutable pair from the hashed session row and matching `lm_users` row.
2. OAuth state and idempotency receipts include the same uid/chat pair.
3. Mutation accepts only known command discriminants/fields and rejects excess keys.
4. CSRF is a session-derived HMAC value returned only inside authenticated JSON and required in `X-LM-CSRF`; Origin must equal the configured panel origin.
5. GET never executes a user command.
6. Opaque bearer values are hash-only at rest and absent after redirect.
