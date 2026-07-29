# economy/gig — mainnet migration plan (superseded — see WITNESS-RUNBOOK.md)

Written as a witness-prep artifact (P2 recon). This original recon's "open question" below (§ below) has
since been RESOLVED and the chain-selectable config it called for has been IMPLEMENTED — see
`WITNESS-RUNBOOK.md` for the current, applied state (code changes, gas math, per-body deploy plan,
go-live sequence). This file is kept for the original recon trail; treat `WITNESS-RUNBOOK.md` as the
canonical, up-to-date reference from here on. (2026-07-07: the `automaton` address in the recon table below is the OLD, since-rotated wallet -- see WITNESS-RUNBOOK.md's SECURITY UPDATE note.)

## What's testnet-only today (verified by reading the actual files, not assumed)

| thing | testnet value | file |
|---|---|---|
| facilitator chain | `eip155:84532` | `services/facilitator/config.json` |
| facilitator RPC | `https://sepolia.base.org` | `services/facilitator/config.json` |
| USDC contract | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | `skills/economy/gig/lib/escrow.mjs` (`USDC_BASE_SEPOLIA`) |
| chain id (viem calls) | `84532` | `skills/economy/gig/lib/escrow.mjs` (`CHAIN_ID_BASE_SEPOLIA`) |
| viem chain object | `baseSepolia` (from `viem/chains`) | `skills/economy/gig/lib/escrow.mjs`'s `settleBody()` publicClient |
| confirm-tx RPC | `https://sepolia.base.org` | `skills/economy/gig/lib/escrow.mjs` (`DEFAULT_RPC_URL`) |
| ERC-8004 `IdentityRegistry` | `0xdc527768082c489e0ee228d24d3cfa290214f387` | `skills/economy/gig/README.md` / `lib/identity.mjs` |

## What must change — DONE, see WITNESS-RUNBOOK.md §1 for the applied diff

1. **`services/facilitator/config.json`**: DONE, but as an ADDITIVE `config.mainnet.json` (not an
   overwrite) selected via `GIG_CHAIN=base ./start.sh` — `config.json` itself is untouched, so testnet
   keeps working. Public `https://mainnet.base.org` is the mainnet variant's RPC for now — still true
   that a facilitator settling real production volume should move to a paid/private RPC eventually.
2. **`skills/economy/gig/lib/escrow.mjs`**: DONE — `USDC_BASE_MAINNET`/`CHAIN_ID_BASE_MAINNET` added, a
   `GIG_CHAIN` env toggle drives `payViaFacilitator`'s defaults, `base` importable from `viem/chains`.
   Also fixed a bug this recon didn't catch: `settleBody`'s own receipt-confirmation client was hardcoded
   to `baseSepolia` regardless of what chain a caller passed — now threaded through too.
3. **`FACILITATOR_PRIVATE_KEY`** needs real Base mainnet ETH — gas math measured live (not estimated) in
   `WITNESS-RUNBOOK.md` §3: ~$0.001 per settle leg at today's gas price, ~$0.97 for 500 gigs.
4. **`GIG_ESCROW_ADDRESS` / `GIG_ESCROW_PRIVATE_KEY`**: unchanged from this recon's original conclusion —
   reusable as-is, just needs a real mainnet USDC balance.
5. **Per-agent identity gas**: unchanged conclusion, now with a real measured number —
   `WITNESS-RUNBOOK.md` §3 (~$0.0012 per `register()` at today's gas price) + exactly who needs seeding.

## RESOLVED (2026-07-07): a mainnet ERC-8004-style registry exists, option (b)

The specific testnet address (`0xdc527768082c489e0ee228d24d3cfa290214f387`) indeed has no code on Base
mainnet, as this recon originally found. But a search wasn't needed to resolve this — direct on-chain
verification found a real, already-in-use registry at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (note
the vanity `0x8004` prefix, matching "ERC-8004"): confirmed via `eth_getCode` (real bytecode),
`name()`->`"AgentIdentity"`, `symbol()`->`"AGENT"`, `ownerOf(1)` returns a real owner (an agent is already
registered), and a static `register()` simulate from a fresh EOA succeeds. It's a DIFFERENT contract than
the testnet one (its `agentExists()`/`totalAgents()` revert — not implemented there), but
`register()`/`ownerOf()`/the `Registered` event all work as this codebase expects. Full detail + the ABI
fix this required -> `WITNESS-RUNBOOK.md` §2. Option (a) (deploy our own) is no longer necessary.

## Recon: who actually has Base mainnet ETH/USDC right now (read-only, checked live)

| identity | address | Base mainnet ETH | Base mainnet USDC |
|---|---|---|---|
| automaton (real address given in the brief) | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | `0.0001456 ETH` (thin — a handful of L2 txs at most) | `$0.5948` |
| Franklin's own auto-derived EVM identity (see recon report — `~/.blockrun/.automaton/wallet.json`, resolvable via `resolve-identity.mjs` since `ANICCA_HOME=/home/life-manager/.blockrun` for the `franklin-loop` launchd job) | `0x3EcCAD24794ca298D25378E9902A251322ea8749` | `0 ETH` | `$0` |

Franklin's real, funded wallet (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) is **Solana**, not
EVM/Base — this board only speaks EVM/Base, so Franklin's SOL balance is not directly usable here at all;
its *separate*, auto-generated, currently-empty EVM identity above is the only Base-native wallet Franklin
has. Both `identity_register` (needs ETH) and `gig_post` (needs USDC + the facilitator's own gas) would
fail today for Franklin on mainnet OR testnet-with-real-money until that EVM wallet is funded from
somewhere.

## Not done here
The chain-selectable CODE (§1 above) is now committed in this worktree. Still NOT done, by design (see
`WITNESS-RUNBOOK.md` §6 for the deliberate sequence): no gig-skill deploy to `~/.anicca`/`~/.blockrun`, no
`~/.blockrun/mcp.json` write, no wallet funded, no mainnet tx sent, no contract deployed (none needed).
