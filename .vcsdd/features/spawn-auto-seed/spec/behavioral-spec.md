# spawn-auto-seed — behavioral spec (VCSDD lean, 2026-07-04)

Parent SSOT: anicca-project `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md`
§10 G1 (SPAWN = ONE COMMAND) + V-matrix V4. Problem: `skills/self/spawn/run.sh` provisions
wallet/inbox/host/telemetry but then PRINTS "Seed the child wallet with $X" — a human instruction =
human in the loop. The child never receives funds unless a human acts. This feature closes it: the
parent seeds the child ON-CHAIN automatically, in the same one command.

## Requirements (EARS)

- **REQ-1 (gate env overrides)** WHEN `run.sh` evaluates the spawn gate, the system SHALL pass
  `minBalanceUsdc`, `rateLimitDays`, `maxChildren` to `decideSpawn` from env
  `ANICCA_SPAWN_MIN_BALANCE` / `ANICCA_SPAWN_RATE_DAYS` / `ANICCA_SPAWN_MAX_CHILDREN`, defaulting to
  the current constants (20 / 14 / 1) when unset. Non-numeric env values SHALL fall back to defaults.
- **REQ-2 (real balance, fail-closed)** WHEN `run.sh` reads the parent balance, it SHALL query the
  REAL on-chain Base USDC balance of the parent wallet address (via `scripts/usdc-balance.py`,
  public RPC, env-overridable `BASE_RPC_URL`). IF the query fails, the balance SHALL be 0 (dormant —
  fail-closed, never a fake balance). The stale `wallet.json .balance_usdc` field is no longer read.
- **REQ-3 (pure seed plan)** `lib/seed.js` SHALL export `buildSeedPlan({seedUsdc, parentWallet,
  childWallet, parentBalanceUsdc})` returning `{ amountUnits }` (integer, 6 decimals) and SHALL throw
  when: seedUsdc is not a finite number > 0; childWallet equals parentWallet (case-insensitive);
  parentBalanceUsdc < seedUsdc. No I/O.
- **REQ-4 (real transfer)** AFTER telemetry registration succeeds, `run.sh` SHALL execute
  `scripts/seed-child.py` transferring exactly `amountUnits` of Base USDC from the parent wallet to
  the child wallet (real broadcast, wait for receipt). ON success it SHALL print `SEED_TX=<0xhash>`.
  ON failure it SHALL append a ledger row with `seed_status:"failed"` and exit 1 (HARD 0.24 — no
  success report without the on-chain side-effect).
- **REQ-5 (ledger finalization)** `lib/seed.js` SHALL export `finalizeSeedRow(row, {txHash})`
  returning a NEW row (no mutation) with `seed_tx:<hash>`, `seed_status:"sent"`. The final colony
  row SHALL include these fields.
- **REQ-6 (no human instruction)** The final stdout message SHALL NOT instruct a human to seed; it
  SHALL state the seed tx hash instead.

## Out of scope (explicit)

- Akash MAINNET boot: blocked by physics — treasury needs ≥25 AKT (~$17) to mint ACT ≥ min_mint;
  current liquid funds $1.79. Sandbox-2 lease-active already evidenced (2026-06-27). Mainnet migrates
  when an agent's earnings cover it (TREASURY_SWAP_CMD wiring = separate feature).
- Any spawn/earning DECISION logic (the gate params' VALUES are ops config; the gate LOGIC is
  untouched, §0.25).

## Verification architecture

| layer | check |
|---|---|
| unit (node:test) | `lib/__tests__/seed.test.js` — REQ-3/REQ-5 all branches |
| static | `bash -n run.sh`; `python3 -m py_compile` both scripts |
| adversary | fresh vcsdd-adversary, disk-only, binary PASS/FAIL |
| NO-MOCK E2E | ONE command spawns a real child (host=do boots; akash=sandbox lease) with REAL `SEED_TX` visible on basescan; child appears on live dashboard; ledger row has provider_id + seed_tx |
