# How to cash out

Your Anicca earns in **USDC on Base**. This is how money moves between you and your Anicca — in (you seed it) and out (it pays you). Pick your country.

## 🇺🇸 US — direct, all on Base

Trivial both ways. No exchange hop, settles in seconds, do it daily.

- **You → Anicca (seed):** send **USDC (Base)** from your wallet (MetaMask / Coinbase) to your Anicca's Base wallet address.
- **Anicca → you (payout):** your Anicca sends **USDC (Base)** straight to your Base wallet address.

That's it. The whole loop is one network, one token.

## 🇯🇵 Japan — via Binance + PayPay + Solana

Japan has no clean Base on-ramp from a bank, so route through Binance Japan and Solana. (SBI VC Trade was dropped — ~1 day to the bank is too slow.)

### You → Anicca (invest)
1. Move money into **Binance Japan** (PayPay top-up).
2. On Binance, **buy Solana (SOL)**.
3. **Send SOL** to your **MetaMask** (Solana address).
4. **Swap + bridge** SOL → **USDC on Base** via [relay.link](https://relay.link) or Jupiter, sending it to your Anicca's Base wallet.

### Anicca → you (get paid)
1. Your Anicca sends **USDC or SOL** to your **Binance deposit address**.
2. On Binance, **sell** it for JPY.
3. **Cash out to PayPay** — the Binance Japan app supports PayPay withdrawal.

This path is **daily-capable** — no multi-day bank settlement.

## Honest note

Only wallet ↔ wallet on Base is truly instant and no-human-in-loop. Any path that touches a bank, an exchange, or PayPay needs your one-time KYC'd account — that's the human bridge. Once it exists, the flow runs daily.
