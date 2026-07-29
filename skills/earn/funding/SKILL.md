# funding — claude-p's surplus PM capital -> Franklin, mechanically (no judgment here)

> Spec of record: `$LIFE_MANAGER_REPO/docs/loop-engineering/11-parent-funding-loop.md` §2
> (send mechanism) + §3 (money-safety rails). This skill implements ONLY the mechanism
> (withdraw -> bridge -> send) plus its safety rails. It does **not** decide WHEN or
> HOW MUCH to fund -- that OBSERVE/DECIDE judgment belongs to the agent running the parent
> funding loop (§1 of the same spec), not to hardcoded logic in this skill (see
> `~/.claude/rules/building-effective-ai-agents.md` -- "no hardcoded judgment, the model
> decides"; `feedback_skills_give_tool_not_decision`). Treat the three scripts below as
> **tools** an agent calls with an amount it has already decided on.

## The route

```
claude-p's Polymarket deposit wallet 0x904B... (Polygon, pUSD/USDC.e)
   │ ① withdraw.py  -- SecureClient.transfer_erc20(recipient=owner EOA 0x810f...)
   ▼
0x810f... (Polygon, USDC.e)
   │ ② bridge.py    -- relay.link quote+execute, Polygon(137) -> Solana(792703809)
   ▼
BF9v... (Solana, USDC) -- claude-p's own founder Solana wallet
   │ ③ send_to_franklin.py -- spl-token transfer
   ▼
Franklin 8Fpqd... (Solana, USDC)
```

Each step is a **standalone script**, independently runnable, independently safe (its own
identity check + caps + kill-switch + ledger row). `run.py` chains all three for convenience
and stops at the first non-`ok` step -- it adds no logic of its own.

## Research finding: is a Polymarket deposit-wallet withdrawal even possible?

**Yes**, confirmed two independent ways (2026-07-08):

1. **Official docs** (`docs.polymarket.com/trading/deposit-wallets`, "Mental Model" section):
   the deposit-wallet owner EOA signs a `WALLET` relayer batch (a normal EIP-712 signature,
   distinct from the `POLY_1271` order-signature path) to execute **any** on-chain call from
   the deposit wallet -- including a plain ERC-20 `transfer` to an arbitrary address. This is
   documented, supported, ordinary functionality, not a workaround.
2. **The installed SDK** (`polymarket` package, in
   `~/.anicca-founder/agents/polymarket-agent/.venv`): `SecureClient.transfer_erc20(token_address,
   recipient_address, amount)` is exactly that `WALLET`-batch ERC-20 transfer. This repo's own
   `skills/earn/polymarket-trade/fund_via_bridge.py` already calls it (with `recipient_address`
   = a bridge address, for registration). Pointing `recipient_address` at the deposit wallet's
   **own owner EOA** (0x810f) instead is a withdrawal -- **no new mechanism, no browser, no
   human credential**. This is what `withdraw.py` does.

The controller key is `POLYGON_WALLET_PRIVATE_KEY` in
`~/.anicca-founder/agents/polymarket-agent/.env` (the owner EOA `0x810F6D61...`, same key that
already signs every pm-trade order) -- never printed by this skill.

### The pUSD wrinkle (verified live 2026-07-08)

The deposit wallet's balance is (right now, live-checked) **100% pUSD, $0 raw USDC.e**. pUSD is
Polymarket's own ERC-20 collateral wrapper (`docs.polymarket.com/concepts/pusd`) and is *not*
bridgeable by relay.link. To get real, bridgeable USDC.e you must first **unwrap**:
`CollateralOfframp.unwrap(asset=USDC.e, to=<deposit wallet>, amount)` (Offramp address
`0x2957922Eb93258b93368531d39fAcCA3B4dC5854`, per `docs.polymarket.com/resources/contracts`).
The SDK does not expose a named `unwrap()` helper (only `transfer_erc20`/`approve_erc20`/
`redeem_positions`/etc.), so `withdraw.py --include-pusd` builds that one call as a raw
`TransactionCall` using the **same** selector+abi-encode primitives the SDK's own
`erc20_transfer_call`/`erc20_approval_call` are built from
(`polymarket._internal.actions.relayer.calls`), and dispatches it via the SDK's own
`SecureClient._dispatch_single_call` (the same dispatcher `transfer_erc20` uses). This is the
one piece of this mechanism that is *not yet* proven with a real on-chain call (everything
else -- `transfer_erc20`, the relay.link bridge, `spl-token transfer` -- has prior live
precedent elsewhere in this repo). Treat `--include-pusd` as the part to watch on the first
real run.

## Scripts

### `withdraw.py` -- PM deposit wallet -> owner EOA (Polygon)
```
python3 withdraw.py --dry [--amount-usd X] [--include-pusd]     # read-only, no chain writes
python3 withdraw.py       [--amount-usd X] [--include-pusd]     # REAL transfer
```
**MUST run with the polymarket-agent's own venv** (`polymarket` SDK only lives there):
`~/.anicca-founder/agents/polymarket-agent/.venv/bin/python3 withdraw.py ...`
Defaults `--amount-usd` to "everything above the configured reserve", then re-clips to the
per-transfer cap. `--include-pusd` unwraps pUSD -> USDC.e first if the existing USDC.e balance
alone isn't enough to cover the requested amount (needed today -- see the pUSD wrinkle above).

### `bridge.py` -- Polygon USDC.e -> Solana USDC (relay.link)
```
python3 bridge.py --dry [--amount-usd X]      # quote only, no signing/broadcast
python3 bridge.py       [--amount-usd X]      # REAL bridge
```
Runs fine under plain `python3` (needs `web3`, `eth_account`, `requests`, `solders` -- all
present in the system interpreter, verified). Refuses (`fail-closed`) if the relay fee would
exceed `bridge_max_fee_pct` in `config.json` (default 15%) -- protects against burning a fixed
relay fee on too small an amount. Live-verified 2026-07-08: relay.link correctly rejects a
sub-economic amount with `AMOUNT_TOO_LOW` (the 0x810f wallet had ~$0.08 real balance at test
time) -- the script surfaces that rejection rather than masking it.

### `send_to_franklin.py` -- Solana USDC -> Franklin (spl-token)
```
python3 send_to_franklin.py --dry [--amount-usd X]
python3 send_to_franklin.py       [--amount-usd X]
```
Runs under plain `python3`. Uses the official `spl-token` CLI (already installed at
`~/.local/share/solana/install/active_release/bin/spl-token`) via a temp, chmod-600,
always-deleted keypair file -- no hand-rolled SPL instruction bytes.

### `run.py` -- chains all three
```
python3 run.py --dry [--amount-usd X] [--include-pusd]
python3 run.py       [--amount-usd X] [--include-pusd]
```
Dispatches each step to the interpreter that actually has its dependencies (`withdraw.py` ->
the agent venv, the other two -> system `python3`; override with env `WITHDRAW_PYTHON` /
`FUNDING_PYTHON`). Stops at the first step whose JSON result is not `ok: true`. Note: in
`--dry` mode each step still reads REAL on-chain/API state independently, so step 2/3 will
only see a meaningful balance once step 1 has REALLY moved money in an earlier, separate,
non-dry run -- `--dry` proves each script's logic is correct against live state, it cannot
simulate money that a prior dry step didn't actually send.

## Money-safety rails (§3 of the parent spec -- all implemented, see `lib/`)

| Rail | Where | How |
|---|---|---|
| Recipient identity verification (the "Efpap5 incident" fix) | `lib/identity.py` | Derives the recipient's PUBLIC key from its OWN key/session file (never trusts a displayed/labeled address) and requires it to equal the known-good address from `config.json`. `send_to_franklin.py` refuses to send if Franklin's `~/.blockrun/.solana-session` does not derive `8Fpqd...` -- exactly the failure mode from `docs/loop-engineering/10-STATUS-verified.md`'s "franklin proxy displayed `Efpap5` instead of `8Fpqd`" note. No flag bypasses this check. |
| Per-transfer / daily / cumulative caps | `lib/caps.py` (`check_caps`), `config.json` | Pure function over the ledger history. Only the `withdraw` step's `"sent"`/`"pending"` rows count toward spend (the withdraw hop is the ONE point money actually leaves claude-p's capital base -- bridge/send_to_franklin move that SAME money onward, not a second/third outflow; see `lib/caps.py::_outflow_rows` docstring, money-safety review Finding C, 2026-07-08). A `failed`/`skipped`/`dry` attempt never eats cap headroom. A `pending` row (broadcast recorded before confirmation resolves, see below) DOES count, since the money may already have moved; if a later `sent`/`failed` row for the same `tx_hash` is appended, only the most-terminal row is counted once (no double-count). |
| Reserve protection (never starve pm-earner) | `lib/caps.py` (`reserve_protected_amount`), `config.json: reserve_usd` | `withdraw.py` never proposes withdrawing below the configured reserve. |
| On-chain confirmation before recording success, crash-safe | `lib/erc20.py` (`eth_tx_confirmed_success`), `lib/solana_rpc.py` (`confirmed_success`) | Independently queries the chain (`eth_getTransactionReceipt` / `getSignatureStatuses`) for a real terminal status -- never trusts an SDK/CLI "success" return alone. Every real broadcast (unwrap, transfer, bridge tx, spl-token transfer) is recorded as a `"pending"` ledger row IMMEDIATELY after broadcast, BEFORE the confirmation wait/poll call -- the confirmation call itself is wrapped in try/except, so a transient RPC failure between broadcast and confirmation can never leave a real transfer completely unlogged (money-safety review Finding A, 2026-07-08). On confirmed success the row is followed by a `"sent"` row (or `"failed"` if the receipt shows a revert); if the confirmation RPC call itself raises, the `pending` row is left as-is for manual reconciliation. |
| Kill-switch | `lib/kill_switch.py` | `touch KILL` in this directory pauses all three scripts (same convention as `polymarket-trade`'s own `KILL`). `rm KILL` resumes. |
| Ledger (audit trail) | `lib/ledger.py` | Every decision (`sent`/`pending`/`failed`/`skipped`/`dry`) appended to `$LIFE_MANAGER_REPO/skills/earn/state/funding-ledger.jsonl`. |
| No touching reserves/other wallets | `config.json: known_addresses` | Every address this skill ever reads from or writes to is a named constant checked against the config, never derived from an untrusted display string. |

## Config (`config.json`)

All caps/reserve/known-addresses are DATA, not code -- change the number here, never the
script logic. Current defaults (raised for the D2 seed, 2026-07-08, after D1's $2 on-chain
success): `reserve_usd: 5.0`, `per_transfer_usd_cap: 12.0`, `daily_usd_cap: 15.0`,
`cumulative_usd_cap: 50.0`, `bridge_max_fee_pct: 15`. Tune these as claude-p's real balance
and Franklin's real needs become clearer -- they are intentionally conservative.

## Tests

Pure logic only (no network, no real keys) -- `lib/caps.py`, `lib/identity.py`,
`lib/ledger.py`:
```
cd $LIFE_MANAGER_REPO/skills/earn/funding
python3 -m pytest tests -v      # 33 tests, all pure/offline
```

## What this skill deliberately does NOT do

- Decide WHEN to fund or HOW MUCH (that's the OBSERVE/DECIDE judgment of the parent funding
  loop, §1 of the parent spec -- an agent, not this skill, makes that call and then invokes
  these scripts with an amount).
- Move any money by itself -- every script defaults to `--dry` semantics being the safe,
  read-only choice; a real transfer requires an explicit run without `--dry`.
- Schedule itself (no launchd/cron wiring here -- that's a separate, later feature per the
  parent spec's §5 VCSDD plan).
