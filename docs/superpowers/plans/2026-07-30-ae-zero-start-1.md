# AE-ZERO-START-1 Implementation Plan

Spec: `docs/superpowers/specs/2026-07-30-ae-zero-start-1-design.md` (authoritative; on conflict, spec wins).
Worktree: `~/anicca-project/.worktrees/ae-zero-start-1`, branch `feature/ae-zero-start-1`.
Method: TDD (RED → GREEN → REFACTOR) per task. Commit + push after each task.

## Task 1 — Solana wallet module
- RED: `apps/life-manager/lib/agent-wallet-solana.test.js` — keygen shape (base58 address 32-44 chars), deterministic derivation from secret, redaction (`redactSolanaWallet` strips secret fields), JSON.stringify of wallet object never contains secret.
- GREEN: `apps/life-manager/lib/agent-wallet-solana.js` using `@noble/curves` ed25519. Base58: check `apps/life-manager/node_modules` for `@scure/base` (transitive of @noble) first; only add `bs58` if truly absent.
- Model on `lib/agent-wallet.js` (SECRET_FIELDS/redact pattern) + `runtime/wallet-address-solana.mjs` (fail-closed).

## Task 2 — Migration
- `apps/life-manager/migrations/2026-07-30-lm-tenant-agent-wallets.sql` per spec §4.1 (solana address column w/ base58 CHECK, two key-ref columns w/ anti-plaintext-key CHECK, created_at).
- Test in existing migration-test style (see `lib/earnings-migration.test.js` for the pattern).

## Task 3 — Custody helpers
- `apps/life-manager/lib/tenant-wallet-store.js`: ensureTenantWallets(uid) — atomic 0600 writes under `${LM_DATA_ROOT:-~/.anicca}/wallets/<uid>/`, idempotent skip when file+DB agree, hard-stop receipt on mismatch (spec §4.3, §5.4). secret:// refs via `lib/secret-provider.js` seam.
- RED first: unit tests incl. mode check, collision, idempotency, tenant A/B distinct paths.

## Task 4 — Zero-start job adapter
- `apps/life-manager/lib/zero-start-job-adapter.js` per spec §4.4. Clone `lib/report-job-adapter.js` structure (capability/loop id/effect_key/tenant scope/receipt kind).
- Measured balances only: `lib/base-usdc-balance.js` + minimal Solana RPC balance call (add to solana module).
- TG payload through `lib/telegram.js`; `assertNoSecret` on payload + receipt; `blocked_no_chat` honest path.
- HTTP/contract tests in existing style (`test/payout-question-http-contract.test.js` as reference for TG-surface testing).

## Task 5 — Inflow watch adapter
- `apps/life-manager/lib/wallet-inflow-job-adapter.js` per spec §4.5: Base eth_getLogs + Solana getSignaturesForAddress, persisted cursor, `financial_deposit` rows (semantic label `capital_class: capital_in` in receipt) via `lib/earnings-runtime.js` writer with `entry_key: inflow:<chain>:<tx>`.
- Tests: exactly-once, duplicate replay refused, revenue totals unchanged, quiet no-inflow receipt.

## Task 6 — Wiring
- Register both capabilities in `scripts/runtime-up.js` handler map (follow `:264-335` pattern exactly).
- Enqueue = self-heal sweep only (spec §4.4 updated): scheduler sweep enqueues `wallet.zero-start` for `lm_users` rows missing wallet columns. `lm-onboard.js` untouched — runtime queue is in local Postgres, unreachable and un-exposable from Netlify without a new public write surface.
- Extend `test/tenant-isolation.test.js` with wallet isolation assertions.

## Task 7 — Regression + evidence prep
- Run focused money slice (package.json:23 list) then full `npm test`. Fix until green. Record counts.
- `node --test` output pasted into a draft evidence file `docs/evidence/agent-economy/2026-07-30-ae-zero-start-1.md` (E2E sections left for Fable to fill — mark clearly as PENDING-E2E, do not fabricate).

## Rules for executor
- Do NOT touch: `services/x402-endpoint` payTo config, secret-provider cloud paths, BlockRun code (deferred sibling tasks).
- Every symbol you call: verify existence first (Read/grep). No UNVERIFIED code.
- No new heavy deps without checking existing ones first.
- Commit per task, push to `origin/feature/ae-zero-start-1` immediately each time.
- Report back: per-task status, test counts, any spec deviation (deviation requires asking Fable via SendMessage first, not improvising).
