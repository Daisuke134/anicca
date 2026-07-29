# AE-ZERO-START-1 Design — Tenant Zero-Start Wallets

**Date:** 2026-07-30
**Program SSOT:** `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4.6 row 2
**Branch:** `feature/ae-zero-start-1` (worktree `~/Projects/.worktrees/life-manager/ae-zero-start-1`)
**Planner:** Fable 5 (main session). **Executor:** Opus 5 subagent.

## 1. Goal

On Life Manager tenant creation, generate a Base (EVM) wallet and a Solana
wallet owned by that tenant's agent, report the public addresses, the
*measured* `$0.00` balances, and the starting rails to the tenant's Telegram
chat, and start x402 SELL / fee-free WORK / incoming-payment watch with zero
seed. Later inflows are recorded as `capital_in` with revenue 0.

`done="tenant A/B wallet/key/ledger cross-contamination 0; private key in
DB/repo/log/TG 0; real TG message with addresses + explorer links; a real
worker wake at balance 0 emitting a started receipt; started even with no
inflow; a later inflow recorded exactly-once as capital_in / revenue 0"`

## 2. Non-goals (deferred, MUST NOT be built here)

| Deferred | Owner |
|---|---|
| Binding x402 offer `payTo` to tenant wallets | AE-X402-TENANT-ROUTING-1 |
| Cloud KMS / vault signer isolation | AE-CLOUD-CUSTODY-1 |
| BlockRun / provider adapter split | AE-PROVIDER-ADAPTER-1 |
| Spending from tenant wallets | out of scope entirely |

## 3. Chosen approach

Runtime job queue adapter (approach C). Rejected: synchronous generation
inside `apps/landing/netlify/functions/lm-onboard.js` (puts key material in a
Netlify function — wrong custody boundary); per-tenant launchd jobs (does not
scale with tenants, contradicts portable runtime).

## 4. Components

### 4.1 Migration — `apps/life-manager/migrations/2026-07-30-lm-tenant-agent-wallets.sql`

- Add to `lm_users`: `agent_wallet_solana_address text` (base58 CHECK, same
  relaxation style as `2026-07-28-lm-agent-earnings-solana.sql`),
  `agent_wallet_key_ref text`, `agent_wallet_solana_key_ref text`,
  `agent_wallet_created_at timestamptz`.
- Keep the existing EVM CHECK on `agent_wallet_address`
  (`2026-07-27-lm-financial-reports.sql:7-15`) intact for that column.
- Key-ref columns store `secret://` references only (see 4.3). A DB CHECK
  MUST reject values starting with `0x`, containing 64+ hex chars, or
  matching a base58 secret shape — plaintext keys in DB = 0 by schema, not
  by convention.

### 4.2 Wallet generation

| Rail | Module | Notes |
|---|---|---|
| Base | existing `apps/life-manager/lib/agent-wallet.js:54 generateAgentWallet` | reuse; already redact-safe (`redactWallet`) |
| Solana | new `apps/life-manager/lib/agent-wallet-solana.js` | ed25519 via existing dep `@noble/curves`; base58 via `@scure/base` if present, else add `bs58` (small, standard). No `@solana/web3.js`. Fail-closed like `runtime/wallet-address-solana.mjs:11-32`; export `generateSolanaAgentWallet` + `redactSolanaWallet`; secret fields never serialized by default |

### 4.3 Custody (local slice only)

- Per-tenant key files under `${LM_DATA_ROOT:-~/.anicca}/wallets/<uid>/base.json`
  and `.../solana.json`, mode exactly `0600`, written atomically
  (`tmp+rename`), refused if pre-existing (idempotent: pre-existing file +
  matching DB address = already provisioned, skip).
- DB stores public addresses + `secret://lm-agent-wallet/<uid>/base` style
  references only, resolved through the existing secret provider seam
  (`apps/life-manager/lib/secret-provider.js`).
- Mode check on read identical to `scripts/run-agent-payout.js:43`.

### 4.4 Zero-start job adapter — `apps/life-manager/lib/zero-start-job-adapter.js`

Clone of the `report-job-adapter.js` shape:

- capability `wallet.zero-start`, loop id `agent.zero-start`,
  `effect_class: 'message'`, `effect_key: zero-start:<uid>` (exactly-once per
  tenant via existing `UNIQUE (tenant_id, effect_key)`).
- Steps: ensure wallets (4.2/4.3) → write public addresses to `lm_users` →
  measure both balances for real (`lib/base-usdc-balance.js` +
  Solana RPC balance; a `$0.00` that was not measured is a lie) → send one
  Telegram message via `lib/telegram.js` → durable receipt with TG
  `message_id` readback → mark started rails.
- Telegram message contains: Base address + Basescan link, Solana address +
  Solscan link, measured balances, and the started rails
  (`x402 SELL (shared seller until AE-X402-TENANT-ROUTING-1)`,
  `fee-free WORK`, `incoming-payment watch`). No promises of income; if the
  tenant has no linked chat yet, the job records `blocked_no_chat` honestly
  and retries on next wake (never fabricates a send).
- Enqueue point: tenant creation path (`lm-onboard.js` flow) enqueues the
  job; the adapter itself also self-heals — a scheduler sweep enqueues
  `wallet.zero-start` for any `lm_users` row missing wallet columns.

### 4.5 Inflow watch adapter — `apps/life-manager/lib/wallet-inflow-job-adapter.js`

- capability `wallet.inflow.watch`, recurring (5-min cadence like the x402 /
  TaskMarket observers), per-tenant scope.
- Base: `eth_getLogs` USDC `Transfer` to the tenant Base address (same
  method as `skills/earn/x402-sell/verify-inflow.mjs`), bounded block
  window + persisted cursor.
- Solana: `getSignaturesForAddress` polling (same as
  `scripts/observe-ugig-work.js:35,64`), bounded + cursor.
- Every confirmed inflow → `lm_agent_earnings` row with
  `kind: financial_deposit` (the ledger-vocabulary implementation of the
  program-SSOT concept "capital_in"; member of `EXCLUDED_KINDS`,
  `lib/earnings-ledger.js:25-39`, so revenue stays 0). The receipt carries
  `capital_class: "capital_in"` as the semantic label. `capital_in` is NOT
  a ledger kind — `normaliseEntry` and the DB CHECK
  (`migrations/2026-07-25-lm-agent-earnings.sql`) both reject it.
  `entry_key: inflow:<chain>:<tx>` for exactly-once. Self/colony wallets
  (shared `skills/earn/x402-sell/lib/self-wallets.mjs` set) are likewise
  `financial_deposit`, never revenue.
- No inflow = quiet receipt (`checked, none`), not an error.

### 4.6 Worker registration

Register both capabilities in `scripts/runtime-up.js` handler map
(`:264-335` pattern). No new launchd label needed if `runtime-up` workers
already wake on schedule; if a host trigger is required, one label
`ai.anicca.life-manager-zero-start` following
`install-x402-sale-ledger-launchd.sh`, never one per tenant.

## 5. Security invariants (all fail-closed)

1. Private keys never leave `lib/agent-wallet*.js` generation scope except
   into the 0600 file write. Never in: DB rows, ledger rows, receipts, TG
   payloads, logs, thrown errors, test fixtures with real entropy.
2. `assertNoSecret` (`lib/earnings-ledger.js:57`) applied to every receipt
   and TG payload the new code emits.
3. DB CHECK from 4.1 rejects key-shaped strings in key-ref columns.
4. Key file collision (file exists but DB address differs) = hard stop with
   honest error receipt, never overwrite.
5. gitleaks/PII gates must stay green; new test fixtures use fixed dummy
   keys marked as such.

## 6. Test matrix

| # | Test | Kind |
|---|---|---|
| 1 | Solana keygen: address derives from secret, base58 shape, redaction, no-serialize | unit `lib/agent-wallet-solana.test.js` |
| 2 | Migration: columns, CHECKs reject plaintext-key shapes, EVM CHECK intact | migration test (existing style) |
| 3 | Zero-start adapter: fresh tenant → wallets + DB row + TG payload (mock transport) + receipt; second run = no-op (idempotent); no-chat → `blocked_no_chat` | unit + contract |
| 4 | Tenant isolation: tenants A and B provisioned → distinct addresses, distinct key files, distinct key refs, ledger rows disjoint; extend `test/tenant-isolation.test.js` | contract |
| 5 | Redaction: grep receipts/TG/DB writes for secret patterns = 0 | unit |
| 6 | Inflow watch: mocked RPC inflow → exactly-once `financial_deposit` row (`capital_class: capital_in` receipt label), revenue total unchanged; duplicate tx replay → refused; no inflow → quiet receipt | unit |
| 7 | Focused money slice + full `npm test` suite green | regression |

## 7. E2E verification (live, by Fable after merge)

1. Provision two real test tenants (A/B) on the live local runtime.
2. Real Telegram message received for each with address + explorer links +
   measured `$0.00` (message ids recorded).
3. `launchctl`/scheduler receipt shows a real worker wake at balance 0 with
   `started`.
4. Send a tiny real USDC amount to tenant A's Base address → exactly one
   `capital_in` row for A, zero rows for B, revenue totals unchanged.
5. Evidence file `docs/evidence/agent-economy/2026-07-30-ae-zero-start-1.md`
   with tx hash, TG message ids, ledger readback, key-file modes, and a
   secret-scan result.
6. Update §0.4.6 row 2 to done with evidence pointers, same PR train.

## 8. Rollback

Feature is additive: new columns nullable, new adapters behind capability
registration. Rollback = unregister capabilities + leave columns (no
destructive migration down needed). Key files are inert without registered
adapters.
