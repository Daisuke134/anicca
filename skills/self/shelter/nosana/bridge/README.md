# Base -> Solana USDC bridge (S10: agent financial independence)

Moves the colony's idle Base USDC into the Solana wallet that actually pays for shelter
(Franklin, `../funding/acquire-nos.mjs`), so runway stops being measured in hours. Every number
below was measured live 2026-07-25 against real Base RPC state, real Circle docs, and a real
LI.FI quote — see the citations inline.

## The decision: bridge. The numbers say yes, by a wide margin.

**Gas verdict (the thing that could have killed this outright):** the founder wallet holds
`0.000008860775871093 ETH` (~$0.0165 at the ETH/USD price fetched live). A real
`eth_estimateGas` call against Base mainnet for an ERC-20 `approve(spender, 10 USDC)` from this
wallet returned `0xdbb0` = **56,240 gas**. Base's real gas price at measurement time was
`baseFeePerGas` 0.005 gwei / `eth_gasPrice` 0.006 gwei (6,000,000 wei/gas) — Base is one of the
cheapest chains that exists. `depositForBurn`'s own gas could not be cleanly isolated (every real
recent Base `depositForBurn`-emitting transaction found by scanning 383 real on-chain events was
routed through a third-party router/aggregator/ERC-4337 EntryPoint, which inflates gas beyond a
raw call), so it is bounded instead by a real comparable: a `receiveMessage`-shaped call on Base
(the destination-side leg, which does strictly *more* work — it also verifies a Circle attestation
signature and mints) used **171,252 gas** in a real transaction
(`0xd68b069a7c98481e07c190c0edabe4e624195e0d873cae3d879c577f34938fa2`). `220,000` gas is used as a
deliberately conservative round-up (`DEFAULT_BURN_GAS_UNITS` in `bridge.mjs`, overridable).

Total estimated Base-side gas for approve + burn at the measured price: **~$0.003** — about 1/5th
of the wallet's available ETH, leaving comfortable headroom even if gas price rises several-fold
before a live run executes. A real `bin/citizen-bridge --dry` run against the actual founder
wallet confirmed this exactly: `total cost $0.0032 (0.032% of $10)`.

## Route comparison (canonical CCTP vs. one aggregator), real quotes

| Route | Mechanism | Real measured/quoted cost on $10 | Time to arrive | Verdict |
|---|---|---|---|---|
| **CCTP V2 Standard Transfer** (built here) | Circle's own burn-and-mint, direct Base->Solana | **0 bps protocol fee** (verified live, `developers.circle.com/cctp/concepts/fees`: "Standard Transfers are free") + ~$0.003 Base gas + negligible Solana gas | Base gas ~seconds; CCTP finality + a destination finalize call, minutes+ | **Recommended** |
| LI.FI aggregator, NEAR Intents solver (`tool: "near"`) | Solver network delivers USDC directly, one Base-side signature only | Real quote 2026-07-25: `fromAmount 10000000 -> toAmount 9961797` = **~0.38% cost** (min after slippage ~0.48%) | ~32 sec (quoted `executionDuration`) | Viable fallback — fully automatic, no destination-side action needed |
| LI.FI aggregator, Mayan MCTP (`tool: "mayanMCTP"`) | CCTP wrapped by Mayan's gas-abstracted relayer | Real quote 2026-07-25: `fromAmount 10000000 -> toAmount 8481850` = **~15% cost** | ~1200 sec (quoted) | **Rejected** — a fixed relayer fee that is punishing at this transfer size |

Circle's own fee table (`developers.circle.com/cctp/concepts/fees`, fetched live): Fast Transfer on
Base costs 1.3 bps (~$0.0013 on $10) but Standard Transfer is 0 bps everywhere, including Solana.
Since this bridge is not latency-sensitive (it exists to extend a runway measured in hours to one
measured in days), Standard Transfer's free rail was chosen over Fast Transfer's ~13 basis points
of paid speed.

**Why build the direct CCTP route instead of just calling LI.FI:** the LI.FI/NEAR-Intents route is
cheap enough (~0.4%) that it would also have been a reasonable choice, and remains documented here
as the fallback if a future session wants a fully-automatic single-transaction UX without building
the CCTP finalize leg (see "Known gap" below). CCTP direct was chosen because (a) it is
structurally the cheapest possible route — literally 0 protocol fee, only real gas — and (b) this
colony already controls both ends of the transfer, so a third-party solver network is an
unnecessary intermediary for an internal transfer between the colony's own wallets.

## Known gap: this build does not submit the Solana-side finalize call

CCTP requires an explicit destination-side action: fetch Circle's attestation for the burn
(`GET https://iris-api.circle.com/v2/messages/6?transactionHash=<burnTxHash>`, domain 6 = Base),
then submit it to Solana's CCTP program to mint. This call is public/permissionless (anyone
holding the attestation may submit it) but nothing submits it automatically. Implementing it
correctly requires hand-deriving several Anchor PDAs against Circle's Solana CCTP program
(`circlefin/solana-cctp-contracts`), which could not be verified live in this session (this
executor was never run `--live`, per the task's own constraint that the Dais/coordinator runs
every live financial action). Shipping unverified PDA-derivation code for the single most
consequential, least-recoverable step would be worse than not shipping it — this repo's own
precedent (`../deploy.mjs`'s README "Known gap" section) is to ship the value-additive,
fully-testable part and flag the highest-risk gap honestly rather than ship guesswork.

What this build DOES do, safely and completely:
1. Burns real USDC on Base via `TokenMessengerV2#depositForBurn` — the irreversible spend this
   colony's own founder wallet controls — with full at-most-once discipline.
2. Polls the real Solana USDC balance at the destination for the credit (`reconcile.mjs`'s
   `pollForDestinationCredit`) — the spec's own reconciliation mechanism ("poll for the
   destination-side credit... never re-send").

A `--live` run will very likely end in `awaiting-credit`: the burn succeeded on Base; the mint has
not happened yet because nothing has submitted the finalize call. This is reported honestly as
`creditResult.outcome === "awaiting-credit"`, never silently treated as failure or success. The
follow-up (a future S11) is to automate the finalize call using the burn tx hash this build already
records, or to complete it once manually via the attestation.

## Module map

| File | Role |
|---|---|
| `constants.mjs` | Verified-live CCTP/Base/Solana addresses, domains, USDC mints. |
| `identity.mjs` | Resolves the Base (source, signs) and Solana (destination, address-only) identities via `resolve-identity.mjs` + `../keypair.mjs`'s `deriveAddressFromSecret` — never a new wallet, never logs secret material. |
| `cctp.mjs` | Pure ABI encode/decode (`approve`, `allowance`, `depositForBurn`) via `viem` (this feature's one new dependency). Selectors cross-checked against the public 4byte.directory database. |
| `quote.mjs` | Pure `{worthIt, netReceivedUsdc, costUsd, costFraction, reason}` evaluator. Fails closed on any missing/unfetched gas price, price, or fee. |
| `spend-gate.mjs` | Pure money-safety gate: reuses `../spend-gate.mjs`'s `checkSpendCaps` for the cap discipline, adds a small explicit per-bridge cap and a "leave ETH for a future tx" floor. |
| `base-rpc.mjs` | Raw Base JSON-RPC reads/writes (gas price, balances, nonce, chainId, `eth_call`, send, receipt) — same hand-rolled-fetch convention as `../../../earn/lib/usdc.mjs`. |
| `eth-price.mjs` | Real ETH/USD price (CoinGecko's keyless public endpoint). |
| `solana-balance.mjs` | Real Solana USDC balance read — mirrors `../deploy.mjs`'s `readNosBalance` shape. |
| `sign.mjs` | The one place this feature signs a Base transaction (via `viem/accounts`), deterministic so the tx hash is known before broadcast. |
| `reconcile.mjs` | At-most-once reconciliation for the burn send, plus `pollForDestinationCredit` — the core "never blind-retry, poll for the destination credit" logic. |
| `bridge.mjs` | Orchestrates all of the above — `bridgeToSolana({live})`. |
| `bin/citizen-bridge` (repo root) | Thin CLI entrypoint, `--dry` default, matching `citizen-up`/`citizen-fund`/`citizen-rent`/`citizen-state`/`citizen-solvency`. |

## Money-safety notes

- **Fail closed everywhere.** A gas-price fetch failure, an unresolvable identity, or a missing
  fee quote all refuse (`worthIt:false` / throw) rather than silently proceeding with a
  zero/free/unknown assumption.
- **At-most-once.** A live run writes an intent record (`nosana-bridge-intents.jsonl` under
  `resolveStateDir()`) *before* signing — the tx hash is already known at that point because
  `viem`'s ECDSA signing is deterministic (RFC6979), the same property
  `../funding/acquire-nos.mjs` relies on for Solana's ed25519 signatures. If the send call itself
  throws or times out, the outcome is reconciled by reading the real receipt via
  `eth_getTransactionReceipt` — never a blind resend.
- **Cap discipline reused, not reinvented a third time.** `spend-gate.mjs` imports
  `checkSpendCaps` from `../spend-gate.mjs` directly instead of re-expressing per-transfer/
  daily/cumulative cap math again.
