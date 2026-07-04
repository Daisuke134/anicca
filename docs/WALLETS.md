# Anicca WALLETS — canonical (stop forgetting these) — snapshot 2026-07-04 ~07:40 JST

> The one place every wallet + its role + its live balance lives. Update the snapshot when it changes.
> Balance-check one-liners at the bottom. Key material is NOT here — only public addresses.

## The instances and their wallets

### 🧍 ME / Claude — the LOCAL human-funded automaton (this Mac Mini)
The loop (`~/anicca/runtime/loop`) runs on the founder body `~/.anicca-founder`. It uses TWO EVM wallets:

| Wallet | Address | Key source | Role |
|---|---|---|---|
| **Operational (BlockRun/HL)** | `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` | `~/.openclaw/.env::BLOCKRUN_WALLET_KEY` | pays x402 compute + holds the Hyperliquid perp account; the loop's `hl-trade`/`x402_sell` payTo |
| **Founder (treasury)** | `0x810f6d61f7606deee2657d3083e150a222bc29c5` | `~/.anicca-founder/wallet.json` | treasury: yield, pm-trade bankroll (bridged to Polygon), spawn seed source |
| Founder Solana | `BF9vzj7YdA6nowwZdW65fQSM1vhRN4sntkKTPnnsfRCX` | `~/.anicca-founder/solana-wallet.json` | Solana-side treasury / gas source |
| "myClaude" clip (Solana) | `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` | (memory `project_myclaude_clip_rewards_self_earning`) | clip-rewards payout wallet (currently empty) |

### 🤖 SELF-FUNDED AI — Franklin (BlockRunAI/Franklin-Trading), Solana
| Wallet | Address | Key source | Role |
|---|---|---|---|
| **Franklin (self-funded)** | `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` | `~/.blockrun/` (franklin-trading CLI) | self-funded trader: pays its OWN x402 model calls + trades from THIS wallet |

## Live balances (snapshot 2026-07-04 ~07:40 JST)

| Wallet | Chain | Holdings | ≈ USD |
|---|---|---|---|
| 0xa3cd operational | Base | 8.819 USDC + 0.00018 ETH | $8.82 |
| 0xa3cd operational | Hyperliquid | perp acct value | $8.75 |
| 0x810f founder | Base | 0.300 USDC + 0.315 aUSDC(yield) | $0.62 |
| 0x810f founder | Polygon | 5.976 USDC.e + 7.53 POL | $5.98 + ~$1.5 |
| BF9v founder | Solana | 0.002 SOL | ~$0 |
| xxKC33 clip | Solana | empty | $0 |
| **8Fpqd Franklin (self-funded)** | Solana | 0.420 USDC + 0.003 SOL | **$0.42** |
| | | **TOTAL on-chain** | **≈ $26** |

## Where did the money go? (honest accounting, Dais gave ~$10 each)
- **Almost NONE was wasted.** The bulk is intact, just RELOCATED across chains by my bridges (setup):
  Base→Polygon $6.00 (pm-trade bankroll, now 5.976 USDC.e) + $0.60→POL gas; Base→Solana $1.50 (Franklin seed).
- **Only real loss = $0.91**: Franklin (self-funded) burned it on opus-4.8 *thinking* over a few sessions
  with $0 earned. FIXED 2026-07-04 (FIX-C) → now on cheap `openai/gpt-5-mini`; balance held at $0.42 through
  the last (failed free-model) run = bleed stopped.
- **Earnings so far ≈ $0**: yield trickled +$0.12 (0.19→0.315 aUSDC); gig +$0.315 once (historical);
  hl-trade churn = pennies-negative; x402_sell live but no buyers. Realized net since the loop turned on ≈ $0.
- ★ OPEN QUESTION for Dais: the self-funded AI's wallet (Franklin 8Fpqd) was seeded by ME with only $1.50
  from the founder treasury — I never saw a separate ~$10 "self-funded" deposit. If you funded a specific
  self-funded address with $10, tell me which one so I can reconcile; otherwise the self-funded pot = what I
  bridge to it from the founder treasury. ★

## Balance-check one-liners
```bash
# Base (0x810f / 0xa3cd): USDC = eth_call balanceOf on 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
curl -s -X POST https://mainnet.base.org -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","data":"0x70a08231000000000000000000000000<ADDR_NO_0x>"},"latest"]}'
# Polygon USDC.e: to=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 via https://polygon-bor-rpc.publicnode.com
# Solana USDC (8Fpqd/BF9v/xxKC33): getTokenAccountsByOwner mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
# Hyperliquid acct: ~/.anicca-founder/skills/earn/hl-trade/hl.py account
```
