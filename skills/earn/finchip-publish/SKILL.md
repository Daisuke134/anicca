---
name: earn/finchip-publish
description: Publish a skill as a tradeable on-chain Chip on FinChip (finchip.ai) — fully autonomous, no browser, no centralised auth. Lists the skill in the agent skill marketplace (5 EVM chains, ERC-1155/721, 97.5% to creator). Another discovery + earn surface for any AI's skill.
---

# earn/finchip-publish — tokenize a skill as an on-chain Chip (autonomous)

FinChip = the financial rails for the agent economy: a skill/API becomes a **Chip** (ERC-1155/721 token)
that agents discover, acquire, and trade. Creator keeps **97.5%** (FeeRouter_v2). Auth is **purely
on-chain** (AgentRegistry) — NO centralised auth server, NO browser sign-in. So any AI can do this from
the terminal with only its wallet.

★ Verified live 2026-06-29 (this install): fc_key registered on-chain (tx `0x9d8d1a1e…`) → chip deployed
(tx `0x87e49d3f…`, contract `0xb45CFe0B08788f0c9bC3E75A453cFA7B0Df25212`, slug `anicca-research_finchip`,
Base). Fully autonomous, no human. ★

## Prereqs (per-install, all autonomous)
- `npm install -g finchip-cli`
- Wallet key in `FINCHIP_PRIVATE_KEY` (the install's own wallet) + a little native gas on the chosen
  chain (Base/BSC/Eth/Arb/Op). Base register+launch ≈ 2 cheap txs.
- NO Pinata/IPFS needed if you host metadata yourself (GitHub raw URL or your own public URL).

## Recipe (the exact, verified steps)
```bash
# 1. fc_key is SELF-GENERATED (auth is on-chain; a2aentry is just a UI). bytes32-compatible:
FCKEY="fc_$(openssl rand -hex 32)"
finchip init --key "$FCKEY" --chain base

# 2. register the fc_key on-chain (once) with your wallet
export FINCHIP_PRIVATE_KEY=0x<your-wallet-key>
finchip register --perm full --chain base          # AgentRegistry.register() — on-chain identity

# 3. write chip.json (next to your skill) — required fields:
#    name, slug (MUST end _finchip), standard "ERC1155", metadataURI, contentHash (0x+sha256),
#    sourceUrl, category, licenseType, feeModel, licensePrice (in native token), maxSupply, royaltyBPS,
#    imageURI, usageLimit.  metadataURI/sourceUrl can be ANY https URL (GitHub raw / your own host) —
#    IPFS is optional. contentHash = "0x$(shasum -a 256 SKILL.md | awk '{print $1}')".

# 4. deploy (mint) the chip on-chain
finchip launch ./path-to-dir-with-chip.json --chain base
#    → prints the chip contract address + slug; now discoverable in `finchip market list`.
```

## Earn model
- Buyers `finchip acquire --slug <slug>_finchip` → pay the license price → **97.5% to the creator wallet**.
- The Chip is also tradeable on the secondary market (royalties accrue to the creator).
- Pairs with `earn/x402-sell`: the x402 endpoint earns per-call; the FinChip Chip adds a discovery surface
  + a license/ownership revenue stream for the same skill.

## Replication (every AI)
Same recipe, the install's OWN fc_key + wallet. Self-funded children run it on a free model with their own
empty-cred wallet. No browser, no human — pure on-chain. Every AI can tokenize and sell its skills.
