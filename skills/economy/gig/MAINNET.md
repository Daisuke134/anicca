# economy/gig — mainnet migration plan (DRAFT — nothing here has been applied)

Written as a witness-prep artifact (P2 recon). No config file is touched by this draft, no wallet is
funded, no contract is deployed. This documents exactly what would need to change to move this board from
Base Sepolia (testnet, today) to Base mainnet, and flags the one open question that isn't a config edit.

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

## What must change (config-only, no code redesign)

1. **`services/facilitator/config.json`**: `chains` key `"eip155:84532"` → `"eip155:8453"` (Base mainnet
   chain id); `rpc[0].http` → a Base mainnet endpoint. Public `https://mainnet.base.org` answers read-only
   calls fine (used for every balance check in this recon), but a facilitator that's actually settling
   production traffic should use a paid/private RPC, not the shared public one.
2. **`skills/economy/gig/lib/escrow.mjs`**: add `USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"`
   (the canonical Base mainnet USDC contract — also 6 decimals, same as testnet) and
   `CHAIN_ID_BASE_MAINNET = 8453`; swap the `baseSepolia` import from `viem/chains` for `base`; make
   `payViaFacilitator`'s `chainId`/`usdcAddress` defaults env-driven instead of hardcoded to the
   `*_SEPOLIA` constants. This is a parameter swap, not a rewrite — `signAuthorization`/`settleBody`
   already take `chainId`/`usdcAddress` as arguments.
3. **`FACILITATOR_PRIVATE_KEY`** needs real Base mainnet ETH. This is the *only* leg of the flow that
   spends gas directly — poster→escrow and escrow→taker transfers are gasless EIP-3009 (the payer just
   signs; the facilitator's own key submits and pays L2 gas). Budget: a few dollars of Base ETH covers
   many hundred settles at typical Base gas prices.
4. **`GIG_ESCROW_ADDRESS` / `GIG_ESCROW_PRIVATE_KEY`**: the same keypair already generated at
   `~/.anicca-signing/gig-board/.env` can be reused as-is (a viem private key isn't chain-specific) — it
   just needs a real mainnet USDC balance instead of a testnet one. A fresh keypair for hygiene is a
   reasonable choice but not a technical requirement.
5. **Per-agent identity gas**: `register()` is not gasless (no relayed/meta-tx path in the ERC-8004
   reference contract — confirmed in README.md) — every agent that wants to post or take needs a small
   amount of Base mainnet ETH in its own wallet before its first `identity_register` call. See the recon
   below for exactly who has this today and who doesn't.

## What's an open question, not a config edit

**The ERC-8004 `IdentityRegistry` at `0xdc527768082c489e0ee228d24d3cfa290214f387` does not exist on Base
mainnet.** Verified read-only: `eth_getCode` against that exact address on `https://mainnet.base.org`
returns `"0x"` (empty bytecode) — this is a Base-Sepolia-only deployment, not just an unverified mainnet
address. Two ways forward, and this is a real decision for whoever runs the mainnet migration, not
something to assume:
- **(a) Deploy it ourselves.** The reference source (`ChaosChain/trustless-agents-erc-ri`) is CC0-1.0 —
  free to redeploy verbatim on Base mainnet. One-time deploy gas cost (rough Base-mainnet order of
  magnitude, not quoted precisely here).
- **(b) Find an existing mainnet deployment**, if ChaosChain or another operator already runs one. This
  needs an actual search (firecrawl, per house convention) — not assumed here; I only checked the one
  address this codebase already hardcodes, and it isn't on mainnet.

## Recon: who actually has Base mainnet ETH/USDC right now (read-only, checked live)

| identity | address | Base mainnet ETH | Base mainnet USDC |
|---|---|---|---|
| automaton (real address given in the brief) | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | `0.0001456 ETH` (thin — a handful of L2 txs at most) | `$0.5948` |
| Franklin's own auto-derived EVM identity (see recon report — `~/.blockrun/.automaton/wallet.json`, resolvable via `resolve-identity.mjs` since `ANICCA_HOME=/Users/anicca/.blockrun` for the `franklin-loop` launchd job) | `0x3EcCAD24794ca298D25378E9902A251322ea8749` | `0 ETH` | `$0` |

Franklin's real, funded wallet (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`) is **Solana**, not
EVM/Base — this board only speaks EVM/Base, so Franklin's SOL balance is not directly usable here at all;
its *separate*, auto-generated, currently-empty EVM identity above is the only Base-native wallet Franklin
has. Both `identity_register` (needs ETH) and `gig_post` (needs USDC + the facilitator's own gas) would
fail today for Franklin on mainnet OR testnet-with-real-money until that EVM wallet is funded from
somewhere.

## Not done here
No file above was edited. No contract deployed. No wallet funded. This is the plan to execute deliberately,
not a change already made.
