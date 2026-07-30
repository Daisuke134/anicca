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
  and non-clobbering (`tmp+fsync+link(2)`; link fails `EEXIST` — rename(2)
  would silently overwrite), refused if pre-existing (idempotent: pre-existing file +
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
- Enqueue point: **self-heal sweep only**. A scheduler sweep inside
  life-manager enqueues `wallet.zero-start` for any `lm_users` row missing
  wallet columns. `lm-onboard.js` stays untouched: the runtime job queue
  lives in the local Postgres (`LM_RUNTIME_DATABASE_URL`,
  `lib/runtime-job-store.js:46-58`), not Supabase — a Netlify function has
  no network path to it, and exposing `lm_runtime_jobs` via PostgREST would
  put the queue's write surface on the public internet. The sweep is
  idempotent by construction (`job_id`/`effect_key` = `zero-start:<uid>`)
  and also heals pre-existing tenants and lost enqueues. Cost: a new tenant
  is provisioned on the first sweep after signup instead of synchronously.

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
- Amount encoding (no invented conversions): Base USDC and Solana USDC-SPL
  inflows → `amount_atomic` + decimals 6, currency `USD` (the ledger's
  atomic gate requires USD, `lib/earnings-ledger.js:128`). Native SOL
  inflows → `amount_minor` = lamports, currency `SOL`,
  `meta {unit:"lamports", decimals:9}` — never converted to USD via a price
  feed inside the ledger. Entry keys MUST identify a **single transfer
  event**, not a transaction — one tx can carry several transfers to the
  same wallet: `inflow:base:<txhash>:<logIndex>`,
  `inflow:solana:<sig>:<accountIndex>`, `inflow:solana-sol:<sig>`.
- Finality: only finalized chain data may enter the ledger. Base scans stop
  at the finalized/safe head and drop any log with `removed === true`;
  Solana uses `finalized` commitment, never `confirmed`. An append-only
  money ledger cannot retract a reorged row.
- Cursor persistence: the watch cursor lives in the job's own durable
  receipt (`next_cursor`, read back from the last completed receipt),
  following the existing `runtime-up.js` history-readback pattern. No new
  cursor table.

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

## 9. Adversary round 1 — planner rulings (2026-07-30)

Fresh-context adversary proved three isolation-family defects empirically
(probe suite against the real modules, not inference). Rulings below are
binding; the implementation MUST change to match.

### 9.1 BLOCKER — the Telegram bot token is a colony secret, not a tenant secret

Measured: the shared worker claims jobs for every tenant
(`scripts/runtime-up.js:665`, `claim_lm_runtime_jobs` treats
`p_tenant_id IS NULL` as all tenants), but the zero-start service is built
once around a provider pinned to a single `LM_RUNTIME_TENANT_ID`
(`:240`, `:383`), so every other tenant's job throws
`environment secret tenant scope mismatch`.

Ruling: the scope check is the **wrong gate for this secret**. One Telegram
bot serves the whole colony; a bot token is not tenant-private material.
The zero-start adapter MUST resolve `secret://telegram/bot-token` through a
**colony-scoped** provider that performs no tenant binding, while ALL key
material continues to flow only through the per-tenant keychain (which the
adversary proved isolated: cross-tenant `get` throws
`WALLET_KEY_SCOPE_MISMATCH`, traversal refs refused).

- Do NOT weaken `createScopedEnvironmentSecretProvider` for other adapters.
  Add a separate colony-scoped provider for shared connector secrets.
- REJECTED alternative: one worker per tenant / passing `tenantId` to
  `claimJobs`. It contradicts the shared-worker design and cannot reach the
  1,000-tenant scale gate (Portable Runtime Order 20/26).

### 9.2 BLOCKER — a failed announce must stay recoverable

Measured: wallets are provisioned and the public address is PATCHed into
`lm_users` before the token is fetched, so a failure after provisioning
leaves a real funded-capable address published with the tenant never told,
`needsZeroStart` false, and `job_id zero-start:<uid>` already present so
`ON CONFLICT DO NOTHING` never re-enqueues. Unrecoverable by construction.

Ruling: separate **work identity** from **effect identity**.

- `effect_key` stays `zero-start:<uid>` — the Telegram announcement remains
  exactly-once forever.
- The job row MUST be retryable: either a generation-suffixed `job_id` or a
  sweep that reaps dead/exhausted rows. Executor picks, and states why.
- `needsZeroStart` MUST mean "no completed announcement receipt for this
  tenant", not "wallet columns are NULL". Provisioning is already
  idempotent (`ensureWallets` hard-stops on file/DB disagreement), so
  re-running a provisioned tenant is safe and MUST heal the announcement.

### 9.3 MAJOR — sweep fairness: no tenant may starve

Measured (`planWalletSweep`, 60 watchable tenants): pass 1 and pass 2 plan
the identical `t001..t050`; 10 tenants are never planned. `isWatchable`
never becomes false, there is no cursor, and the read is
`order=uid.asc&limit=500`. Past 50 tenants the tail's inflows are never
recorded — real money silently unbooked. Past 500 they are never read.

Ruling: the inflow sweep MUST order by **least-recently-watched** so every
tenant is eventually served. Derive the ordering from existing receipts if
that query is reasonable; a single nullable `..._watched_at` column is
acceptable if it is not. The false comment at `lib/wallet-sweep.js:26-27`
MUST be corrected — it is true for zero-start (self-draining) and false for
inflow (never drains).

### 9.4 Confirmed-good invariants (do not "simplify" these)

- `lib/tenant-wallet-store.js:165` `parsed.uid` check is load-bearing: this
  machine's filesystem is case-insensitive and the uid grammar is `/i`, so
  `TenantX` and `tenantx` share one directory. That line converts a
  collision into `WALLET_KEY_TENANT_MISMATCH` instead of a leak.
- Cursor reads are tenant-filtered (`scripts/runtime-up.js:426-441`).
- No module-scope mutable wallet/signer/address/cursor/RPC cache exists in
  any of the six new modules. Keep it that way.

## 10. Adversary round 1 (full report) — remaining rulings

Root cause naming: **four of these defects are one failure** — chain data is
copied into an append-only money ledger without re-deriving the facts that
matter (recipient, transfer identity, finality, which token account). The
`entry_key` uniqueness the design leans on is only as good as the key, and
the key was coarser than the events it must distinguish. Fix the class, not
just the four instances: any value that decides an amount or an owner MUST be
re-derived from the payload, never taken from the RPC's own filter.

Note for the record: 1824/1824 tests passed with all six money defects
present. Unit tests written by the builder encode the builder's assumptions;
only hostile-payload probing found these. Every fix below MUST land with a
test that feeds the hostile payload, not the happy one.

| ID | Ruling |
|---|---|
| MAJOR-2 | FIX. `entry_key` per transfer event, not per tx (§4.5 corrected: `inflow:base:<tx>:<logIndex>`, `inflow:solana:<sig>:<accountIndex>`). The spec was wrong; the implementation was faithful to a wrong spec. |
| MAJOR-4 | FIX. Assert `log.topics[2]` equals the tenant's address topic and drop every non-matching log. Never trust the RPC's filter to have been applied. |
| MAJOR-5 | FIX, and change the semantics: `blocked_no_chat` is a **deferred outcome, not a failure**. Write a real blocked receipt, complete the job, and let the sweep re-enqueue on a later pass (which §9.2 already makes it do). A tenant who links their chat on day 30 MUST still get the message. Do not burn `MAX_ATTEMPTS` on waiting. `failJob` MUST stop discarding `error.code`/`error.blocked`. |
| MAJOR-6 | FIX. Finality is required (§4.5 amended): stop at finalized/safe head, drop `removed === true`, Solana `finalized` not `confirmed`. This matches the program SSOT, which counts only *finalized* receipts. The same gap in `skills/earn/x402-sell/verify-inflow.mjs` is out of scope here — it only observes; this writes money. |
| MAJOR-7 | FIX. Pair Solana pre/post balances by `accountIndex` and sum across every token account the owner holds for that mint. T16b (money invented from a reordered list) is the worse half and MUST have a regression test. |
| MINOR-8 | FIX by removal. Delete both `require.main === module` CLI enqueue entrypoints. §4.4 says sweep-only; a second write surface into the job queue is exactly what that ruling excluded. |
| MINOR-9 | FIX the comment only. `assertNoSecret` is a field-name guard, not a shape scanner. Say so where it is used. |
| MINOR-10 | REJECTED. Do not change `lib/agent-wallet.js` sealing — the production payout path reads `privateKey` and that module is outside this slice's scope (§2). Record the asymmetry as a known input to AE-CLOUD-CUSTODY-1. |
| MINOR-11 | KEEP the tenant keychain, FIX its comment. It is referenced only by tests today; it becomes load-bearing in AE-X402-TENANT-ROUTING-1 / AE-CLOUD-CUSTODY-1. This is a deliberate, stated exception to the delete-unused-code rule — the comment MUST NOT claim it guards a running path. |
| MINOR-12 | FIX. One-line guard on the empty-`taken` path in `scanBaseInflows`. |

### 10.1 Verified-good, carried forward

`lm-onboard.js` byte-identical to `origin/main` (md5 match); nothing outside
`apps/life-manager/` + `docs/` touched; gitleaks clean over 14 commits;
secret-safety PASS (fixtures are RFC 8032 §7.1 published vectors);
failure-semantics PASS apart from MAJOR-5; test counts independently
re-measured and identical to the builder's claims (money-slice 238/238, full
1824/1824 exit 0, real-Postgres `refusals=15 key_material_rows=0`).

## 11. §9.2 / MAJOR-5 corrected ruling — gate the re-activation, not the enqueue

The executor proved in real PostgreSQL 18 that both options §9.2 offered are
refused by the shipped schema: a generation-suffixed `job_id` violates
`UNIQUE (tenant_id, effect_key)`; DELETE-reap violates the receipts FK
(`NO ACTION`) and then the receipts immutability trigger; an `attempt` reset
collides with the existing receipt PK `(job_id, attempt)`. Only **status
re-activation to `queued` preserving `attempt`** is permitted, and
`max_attempts` is hard-capped at 20 by CHECK, so a job row has a lifetime
budget of 20 runs and can never be replaced. §9.2 is superseded by this
section.

**REJECTED — gating the enqueue on a linked Telegram chat.** It starves
provisioning: a tenant who has not linked Telegram would get no wallet, no
published address, and therefore no inflow watch (`isWatchable` needs the
wallet columns). That contradicts program SSOT AC5 — wallet generation and
the watch rails MUST start at `$0.00` regardless of any messaging channel.

**REJECTED — a migration widening `max_attempts` or adding `ON DELETE
CASCADE`.** §4.1 scopes the migration to `lm_users`, and cascading would
destroy money-adjacent audit evidence. The executor was right to refuse it.

**RULING — provisioning is unconditional, announcing is conditional, and
waiting is free:**

1. Attempt 1 runs for every tenant with no announcement, chat or not.
   Provisioning + column publication + rail start happen first (they already
   do, `zero-start-job-adapter.js:261-265` precedes the chat check), so the
   wallet exists and `isWatchable` turns true immediately. AC5 satisfied.
2. With no chat, the job **completes** with a real `blocked_no_chat` receipt
   (MAJOR-5). Never a failure.
3. The sweep re-activates a terminal row (probe-4 method: `status='queued'`,
   `attempt` untouched) **only when the blocking condition has cleared** —
   i.e. `telegram_chat_id` is non-empty and no `started` receipt exists.
   A tenant waiting to link consumes **zero** attempts for an unbounded
   time, so a chat linked on day 30 still gets its message.
4. A transient failure with a chat present (RPC down, Telegram 5xx, the
   provisioned-but-never-announced case) re-activates on the next sweep and
   heals, bounded by the remaining budget.
5. `needsZeroStart` means "no completed receipt `kind=tenant_zero_start`
   with `status=started` for this tenant". Wallet columns stop being the
   signal.
6. A row whose 20 attempts are exhausted is surfaced in the sweep result as
   needing operator attention, never silently dropped. A tenant still
   awaiting a chat link is reported as awaiting, not as failed — the two
   states MUST be distinguishable in the sweep output.

Budget arithmetic this yields: 1 attempt to provision, 1 to announce when the
chat arrives, ~18 spare for transients. Tests MUST cover: chatless tenant
consumes exactly one attempt across many sweeps; the same tenant is announced
after a chat is linked much later; a chat unlinked between the sweep read and
the worker run (the MAJOR-5 race) heals; an exhausted row is reported, not
dropped.
