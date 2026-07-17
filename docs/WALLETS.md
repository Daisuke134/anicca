# Anicca WALLETS — canonical (stop forgetting these) — snapshot 2026-07-07 (rotation update)

> The one place every wallet + its role + its live balance lives. Update the snapshot when it changes.
> Balance-check one-liners at the bottom. Key material is NOT here — only public addresses.

## The instances and their wallets

### 🧍 ME / Claude — the LOCAL human-funded automaton (this Mac Mini)
The loop (`~/anicca/runtime/loop`) runs on the founder body `~/.anicca-founder`. It uses TWO EVM wallets:

| Wallet | Address | Key source | Role |
|---|---|---|---|
| **Operational (BlockRun/HL)** | `0xB9dd3B67921B354c656523d6851537988F31DD56` (rotated 2026-07-07T04:47:35Z — old `0xa3CDd4...` leaked in `~/.anicca-founder/agents/polymarket-agent/.env` + `~/.openclaw/.env`, now revoked) | `~/.openclaw/.env::BLOCKRUN_WALLET_KEY` | pays x402 compute + holds the Hyperliquid perp account; the loop's `hl-trade`/`x402_sell` payTo |
| **Founder (treasury)** | `0x810f6d61f7606deee2657d3083e150a222bc29c5` | `~/.anicca-founder/wallet.json` | treasury: yield, pm-trade bankroll (bridged to Polygon), spawn seed source |
| Founder Solana | `BF9vzj7YdA6nowwZdW65fQSM1vhRN4sntkKTPnnsfRCX` | `~/.anicca-founder/solana-wallet.json` | Solana-side treasury / gas source |
| "myClaude" clip (Solana) | `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` | (memory `project_myclaude_clip_rewards_self_earning`) | clip-rewards payout wallet (currently empty) |

### 🤖 SELF-FUNDED AI — Franklin (BlockRunAI/Franklin-Trading), Solana
| Wallet | Address | Key source | Role |
|---|---|---|---|
| **Franklin (self-funded)** | `F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T` (rotated 2026-07-17 — old `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` leaked, all funds moved on-chain, now revoked) | `~/.blockrun/.solana-session` (franklin-trading CLI) | self-funded trader: pays its OWN x402 model calls + trades from THIS wallet |

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

## Telemetry SIGNING identity ≠ funding wallet (2026-07-05, poster-builder)

The dashboard telemetry each instance signs is a SEPARATE concern from where its money actually lives.
For anicca-a3cdd4 (EVM, `0xa3cd…`) and Franklin (Solana, `8Fpqd…`) the funding wallet IS the signing
key — no distinction needed. **claude-p is the exception**: its real funds sit in the Polymarket
deposit wallet `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, which is an ERC-1167 proxy (owned by an
EOA per `skills/earn/polymarket-trade/SKILL.md`) and therefore CANNOT itself produce an EIP-191
personal_sign — a proxy has no private key of its own. So claude-p's telemetry is signed by a
separate, dedicated SIGNING-ONLY identity, freshly generated 2026-07-04 for exactly this purpose:

| Purpose | Address | Key source | Holds funds? |
|---|---|---|---|
| Telemetry signing (claude-p) | `0x02Bb6b2aF70DBf2c367C1B69aCA9858BF3525502` | `~/.anicca-founder/state/telemetry-identity.json` (`purpose` field says so explicitly) | **No** — signing-only |
| Real funds (claude-p / PM) | `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` | Polymarket deposit-wallet proxy (see `skills/earn/polymarket-trade/SKILL.md`) | Yes — pUSD + PM positions |

Verified live 2026-07-05 against `https://aniccaai.com/.netlify/functions/dashboard-sync`: the
`claude-p` leaderboard row's `id` (the signer recovered from the signature) is `0x02bb…`, while
`net_worth_usd` on that same row is populated from the real funding wallet `0x904B50d2…`'s on-chain
balance — the row correctly reports one instance's money under a different key than the one that
signed the message. Franklin also has its own dedicated poster now
(`runtime/dashboard/telemetry-post-franklin.mjs`, ed25519, signs with `8Fpqd…` directly since Solana
keys sign for themselves) and claude-p has `telemetry-post-claude-p.mjs`; both confirmed present on
disk and both instances show `alive` on the live dashboard alongside anicca-a3cdd4 (3/3).

## Balance-check one-liners
```bash
# Base (0x810f / 0xa3cd): USDC = eth_call balanceOf on 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
curl -s -X POST https://mainnet.base.org -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913","data":"0x70a08231000000000000000000000000<ADDR_NO_0x>"},"latest"]}'
# Polygon USDC.e: to=0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174 via https://polygon-bor-rpc.publicnode.com
# Solana USDC (8Fpqd/BF9v/xxKC33): getTokenAccountsByOwner mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
# Hyperliquid acct: ~/.anicca-founder/skills/earn/hl-trade/hl.py account
```
