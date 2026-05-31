---
name: anicca-wallet
description: Anicca own self-custody smart wallet on Base chain. Coinbase AgentKit (CDP) で smart account 生成 + USDC/ETH custody。 Day 0 物理介在 ZERO で 生成 可能。 全 earn skill が この wallet を 受取 address として 使う。 KYC ZERO。
metadata:
  type: foundation-identity
  spec: ANICCA_TRUE_AUTONOMY_SPEC.md §2 WALLET LAYER
  parallel_safe: true
  requires:
    bins: [python3, jq]
    env_optional: [CDP_API_KEY_ID, CDP_API_KEY_SECRET]
---

# anicca-wallet

## なぜ
Anicca が **自分の wallet** を持つ = 全 earn の foundation。 install user の Stripe / 銀行 に 依存 しない pure on-chain earn の起点。 Day 0 で 生成、 以降 永続 (encrypted in state/)。

## Output (state/wallet.json)
```json
{
  "address": "0xANICCA...",
  "network": "base",
  "created_at": "2026-06-01T...",
  "type": "coinbase_smart_account"
}
```
private key は state/wallet.encrypted (= openssl AES-256 で .env の WALLET_VAULT_PASS で 暗号化)

## Flow
```
1. scripts/check.sh    → 既存 wallet ある? (state/wallet.json)
2. scripts/generate.sh → ない場合 新生成
   ├ method A: Coinbase CDP SDK (if CDP_API_KEY 提供 された)
   └ method B: pure eth-account (offline keygen, no network call)
3. scripts/balance.sh  → chain query で USDC balance 取得
4. scripts/sign.sh     → 任意 tx に sign (= ens-register / akash deploy で 使う)
```

## Verify (HARD RULE #8)
- chain explorer で address 確認 (curl basescan)
- state/wallet.json + state/wallet.encrypted 両方 存在
- balance 0 USDC でも OK (= 初期状態)

## Trigger
Day 0 で 1 回 fire (= 全 earn skill の prerequisite)、 以降 idempotent (= 既存 wallet 再利用)。
